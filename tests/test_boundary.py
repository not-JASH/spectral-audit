"""Independent signed db4, extension, accounting, response, and artifact checks."""

import csv
import hashlib
import json
from pathlib import Path

import numpy as np
import pytest
import pywt

from spectral_audit.boundary import BoundarySettings, evaluate
from spectral_audit.boundary_audit import _response_reference, load_config, run
from spectral_audit.boundary_reference import DB4_HIGH, DB4_LOW, decompose
from spectral_audit.types import SignalRecord

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "configs/m1_db4_boundaries.toml"


def result(x, mode):
    return evaluate(
        SignalRecord(np.asarray(x, dtype=float), 128, "V"), BoundarySettings("db4", 2, mode)
    )


@pytest.mark.parametrize("n", [30, 31, 32, 64])
@pytest.mark.parametrize("mode", ["periodization", "periodic"])
def test_signed_coefficients_counts_and_ledger(n, mode):
    x = (-1.0) ** np.arange(n) * (np.arange(n) + 1) / n
    expected, a1, ledger, flags = decompose(x, mode)
    actual = pywt.wavedec(x.copy(), "db4", mode=mode, level=2)
    for left, right in zip(actual, expected, strict=True):
        np.testing.assert_allclose(left, right, rtol=1e-12, atol=1e-12)
    measured = result(x, mode)
    counts = {
        ("periodization", 30): [8, 8, 15],
        ("periodization", 31): [8, 8, 16],
        ("periodization", 32): [8, 8, 16],
        ("periodization", 64): [16, 16, 32],
        ("periodic", 30): [12, 12, 18],
        ("periodic", 31): [13, 13, 19],
        ("periodic", 32): [13, 13, 19],
        ("periodic", 64): [21, 21, 35],
    }
    assert [g["coefficient_count"] for g in measured["groups"]] == counts[mode, n]
    assert measured["extension_ledger"] == ledger
    assert [g["structural_extension_dependency_count"] for g in measured["groups"]] == [
        sum(f) for f in flags
    ]
    assert ledger[1]["stage_input_length"] == len(a1)
    if n == 30 and mode == "periodization":
        assert ledger[1]["duplicated"]
        assert ledger[1]["duplicate_source_index"] == 14
        assert ledger[1]["duplicate_source_stage"] == "level_1_approximation"
    assert measured["reconstruction_length"] >= n
    assert measured["reconstruction_max_abs_error"] < 1e-12


def test_filter_bank_constants_and_invalid_settings():
    wavelet = pywt.Wavelet("db4")
    np.testing.assert_allclose(DB4_LOW, wavelet.dec_lo, rtol=0, atol=1e-14)
    np.testing.assert_allclose(DB4_HIGH, wavelet.dec_hi, rtol=0, atol=1e-14)
    for args in [("haar", 2, "periodic"), ("db4", True, "periodic"), ("db4", 2, "symmetric")]:
        with pytest.raises(ValueError):
            BoundarySettings(*args)
    with pytest.raises(ValueError):
        result(np.ones(27), "periodic")
    with pytest.raises(ValueError):
        SignalRecord(np.array([1.0] * 29 + [np.nan]), 128, "V")
    with pytest.raises(ValueError):
        result(np.ones(32) * 1e200, "periodic")


@pytest.mark.parametrize("n", [30, 31, 32])
def test_constant_known_answers(n):
    p = result(np.ones(n), "periodization")
    q = result(np.ones(n), "periodic")
    assert p["method_total_power"] == pytest.approx((n + (4 - n % 4) % 4) / n, rel=1e-12, abs=1e-12)
    assert p["accounting_residual"] == pytest.approx(0, abs=1e-12)
    assert q["accounting_residual"] == pytest.approx(0, abs=1e-12)
    if n == 32:
        assert q["method_total_power"] == pytest.approx(13 / 8, abs=1e-12)
        assert q["method_total_power"] / (45 / 32) == pytest.approx(52 / 45)
        assert p["groups"][0]["sum_squared_coefficients"] == pytest.approx(32)
        assert q["groups"][0]["sum_squared_coefficients"] == pytest.approx(52)
        for mode, count in (("periodization", 8), ("periodic", 13)):
            coefficients = decompose(np.ones(32), mode)[0]
            np.testing.assert_allclose(coefficients[0], [2] * count, rtol=1e-12, atol=1e-12)
            for detail in coefficients[1:]:
                np.testing.assert_allclose(detail, 0, rtol=1e-12, atol=1e-12)


def test_periodization_endpoint_identity_and_orthonormal_matrix():
    for index, expected in [(30, 2 / 31), (12, 1 / 31)]:
        x = np.eye(1, 31, index)[0]
        measured = result(x, "periodization")
        assert measured["method_total_power"] == pytest.approx(expected, abs=1e-12)
        assert measured["accounting_residual"] == pytest.approx(0, abs=1e-12)
    x = (-1.0) ** np.arange(30) * (np.arange(30) + 1) / 30
    _, a1, _, _ = decompose(x, "periodization")
    measured = result(x, "periodization")
    assert measured["method_total_power"] == pytest.approx(
        (np.dot(x, x) + a1[-1] ** 2) / 30, rel=1e-12, abs=1e-12
    )
    matrix = np.column_stack(
        [np.concatenate(decompose(np.eye(32)[i], "periodization")[0]) for i in range(32)]
    )
    np.testing.assert_allclose(matrix.T @ matrix, np.eye(32), rtol=1e-12, atol=1e-12)


def test_amplitude_zero_and_record_ratios():
    x = np.arange(30) / 29
    left = result(x, "periodic")
    right = result(3.5 * x, "periodic")
    assert right["method_total_power"] == pytest.approx(3.5**2 * left["method_total_power"])
    zero = result(np.zeros(30), "periodization")
    for group in zero["groups"]:
        assert group["record_power_ratio"] is None
        assert group["record_power_ratio_reason"] == "zero_record_power"
        assert group["method_total_share"] is None
        assert group["method_total_share_reason"] == "zero_method_total_power"


def test_coherent_responses():
    n = 64
    j = np.arange(n)
    for k in range(33):
        omega = 2 * np.pi * k / n
        c, s = np.cos(omega * j), np.sin(omega * j)
        for mode in ("periodization", "periodic"):
            expected, kind = _response_reference(omega, mode, c, s, n)
            assert kind == (
                "circular_filter_response"
                if mode == "periodization"
                else "explicit_finite_filter_bank"
            )
            measured_c, measured_s = result(c, mode), result(s, mode)
            for i, value in enumerate(expected):
                combined = (
                    measured_c["groups"][i]["record_normalized_coefficient_energy"]
                    + measured_s["groups"][i]["record_normalized_coefficient_energy"]
                )
                assert combined == pytest.approx(value, rel=1e-12, abs=1e-12)
            if mode == "periodization":
                assert sum(expected) == pytest.approx(1, abs=1e-12)


def test_artifacts_determinism_hashes_collision_and_failed_write(tmp_path, monkeypatch):
    a, b = tmp_path / "a", tmp_path / "b"
    first = run(CONFIG, a, ROOT)
    second = run(CONFIG, b, ROOT)
    assert first["source_digest"] == second["source_digest"]
    assert len(first["input_records"]) == 84
    for name, expected_hash in first["outputs"].items():
        data = (a / name).read_bytes()
        assert data == (b / name).read_bytes()
        assert hashlib.sha256(data).hexdigest() == expected_hash
        assert second["outputs"][name] == expected_hash
    with pytest.raises(ValueError, match="nonempty"):
        run(CONFIG, a, ROOT)
    summary = json.loads((a / "summary.json").read_text())
    rows = list(csv.DictReader((a / "mode_comparisons.csv").open()))
    assert len(summary["case_list"]) == 18
    assert all(r["difference_label"].startswith("periodic_minus_periodization") for r in rows)
    assert all(r["comparison_status"] == "descriptive" for r in rows)
    for entry in first["input_records"]:
        if entry["case_id"] == "n30_ones":
            assert entry["sha256"] == hashlib.sha256(
                np.asarray(np.ones(30), dtype="<f8").tobytes()
            ).hexdigest()
    import spectral_audit.boundary_audit as module

    original = module._atomic_write

    def fail_on_manifest(path, data):
        if path.name == "manifest.json":
            raise OSError("interrupted")
        original(path, data)

    monkeypatch.setattr(module, "_atomic_write", fail_on_manifest)
    with pytest.raises(OSError, match="interrupted"):
        run(CONFIG, tmp_path / "interrupted", ROOT)
    assert not (tmp_path / "interrupted" / "manifest.json").exists()


def test_strict_audit_config(tmp_path):
    data = CONFIG.read_text()
    for changed in (data.replace("schema_version = 1", "schema_version = 2"),
                    data.replace("[audit]", "extra = 1\n[audit]"),
                    data.replace("[30, 31, 32]", "[30, 32]")):
        path = tmp_path / "bad.toml"
        path.write_text(changed)
        with pytest.raises(ValueError):
            load_config(path)
