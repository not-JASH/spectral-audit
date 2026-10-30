"""Independent finite Haar and schema-v3 checks."""

import csv
import hashlib
import importlib.metadata
import json
import subprocess
import sys
from dataclasses import replace
from datetime import UTC, datetime
from pathlib import Path

import numpy as np
import pytest
import pywt

from spectral_audit.config import load_demo_config, load_measure_config, resolved_measure_config
from spectral_audit.estimators.dwt import DWTSettings, measure_dwt
from spectral_audit.estimators.welch import measure_welch
from spectral_audit.io import write_measure_run
from spectral_audit.reference import fourier_reference
from spectral_audit.signals import make_tones
from spectral_audit.types import Band, SignalRecord

ROOT = Path(__file__).resolve().parents[1]
BANDS = (Band("low", 0, 16), Band("mid", 16, 32), Band("high", 32, 64, True))


def independent_haar(x):
    """Pairwise numerical oracle with no production transform helpers."""
    root_two = np.sqrt(2)
    a1 = np.array([(x[2*j] + x[2*j+1]) / root_two for j in range(len(x)//2)])
    d1 = np.array([(x[2*j] - x[2*j+1]) / root_two for j in range(len(x)//2)])
    a2 = np.array([(a1[2*j] + a1[2*j+1]) / root_two for j in range(len(a1)//2)])
    d2 = np.array([(a1[2*j] - a1[2*j+1]) / root_two for j in range(len(a1)//2)])
    return a2, d2, d1


def check_groups(x, fs=128):
    result = measure_dwt(SignalRecord(np.asarray(x, dtype=float), fs, "V"), DWTSettings())
    oracle = independent_haar(x)
    for actual, expected in zip(result.coefficients, oracle, strict=True):
        np.testing.assert_allclose(actual, expected, rtol=1e-12,
                                   atol=1e-12 * max(1, np.max(np.abs(x))))
    for group, coeff in zip(result.groups, oracle, strict=True):
        assert group.coefficient_count == len(coeff)
        assert group.sum_squared_coefficients == pytest.approx(
            np.dot(coeff, coeff), rel=1e-12, abs=1e-12 * max(1, np.dot(x, x))
        )
        assert group.record_power_contribution == pytest.approx(np.dot(coeff, coeff) / len(x))
        assert group.coefficient_mean_square == pytest.approx(np.dot(coeff, coeff) / len(coeff))
    assert result.method_total_power == pytest.approx(np.dot(x, x) / len(x), rel=1e-12)
    return result


def test_hand_fixture_and_mean_square_distinction():
    x = np.arange(1, 9, dtype=float)
    a2, d2, d1 = independent_haar(x)
    np.testing.assert_allclose(a2, [5, 13], rtol=1e-12, atol=1e-12)
    np.testing.assert_allclose(d2, [-2, -2], rtol=1e-12, atol=1e-12)
    np.testing.assert_allclose(d1, [-1/np.sqrt(2)] * 4, rtol=1e-12, atol=1e-12)
    result = check_groups(x)
    assert [g.coefficient_count for g in result.groups] == [2, 2, 4]
    assert [g.sum_squared_coefficients for g in result.groups] == pytest.approx([194, 8, 2])
    assert [g.record_power_contribution for g in result.groups] == pytest.approx([24.25, 1, .25])
    assert [g.coefficient_mean_square for g in result.groups] == pytest.approx([97, 4, .5])
    assert result.record_power == pytest.approx(25.5)
    assert np.var(d2) == pytest.approx(0)
    assert sum(g.coefficient_mean_square for g in result.groups) != pytest.approx(25.5)


@pytest.mark.parametrize("n", [4, 8, 12, 20])
def test_orthogonality_reconstruction_and_scaling(n):
    matrix = np.column_stack([
        np.concatenate(independent_haar(np.eye(n)[j])) for j in range(n)
    ])
    assert matrix.shape == (n, n)
    np.testing.assert_allclose(matrix.T @ matrix, np.eye(n), rtol=1e-12, atol=1e-12)
    x = np.linspace(-2, 3, n)
    np.testing.assert_allclose(matrix.T @ matrix @ x, x, rtol=1e-12, atol=1e-12)
    result = check_groups(x)
    np.testing.assert_allclose(
        matrix.T @ np.concatenate(result.coefficients), x, rtol=1e-12, atol=1e-12
    )
    scaled = check_groups(3.25 * x)
    for left, right in zip(result.groups, scaled.groups, strict=True):
        assert right.record_power_contribution == pytest.approx(
            3.25**2 * left.record_power_contribution, rel=1e-12,
            abs=1e-12 * max(1, left.record_power_contribution)
        )
        assert right.coefficient_mean_square == pytest.approx(
            3.25**2 * left.coefficient_mean_square, rel=1e-12,
            abs=1e-12 * max(1, left.coefficient_mean_square)
        )


def test_pure_groups_zero_and_impulses():
    cases = [(np.ones(12), 0), (np.tile([2, -2], 6), 2),
             (np.tile([2, 2, -2, -2], 3), 1)]
    for x, active in cases:
        result = check_groups(x)
        for i, group in enumerate(result.groups):
            assert group.record_power_contribution == pytest.approx(
                result.record_power if i == active else 0, abs=1e-12
            )
    zero = check_groups(np.zeros(12))
    assert all(g.record_power_contribution == 0 for g in zero.groups)
    assert zero.record_power_fractions == (None,) * 3
    assert zero.method_total_fractions == (None,) * 3
    assert zero.record_fraction_reasons == ("zero_record_power",) * 3
    assert zero.method_fraction_reasons == ("zero_method_total_power",) * 3
    for index in (0, 5, 11):
        x = np.zeros(12)
        x[index] = 3
        check_groups(x)


def test_phase_sensitive_16hz():
    j = np.arange(256)
    expected_zero = [(3 + 2*np.sqrt(2))/16, 1/16, (2-np.sqrt(2))/8]
    expected_quarter = [expected_zero[1], expected_zero[0], expected_zero[2]]
    for phase, expected in ((0, expected_zero), (np.pi/2, expected_quarter)):
        x = np.sin(2*np.pi*16*j/128 + phase)
        result = check_groups(x)
        assert [g.record_power_contribution for g in result.groups] == pytest.approx(
            expected, rel=1e-12, abs=1e-12
        )
        assert result.method_total_power == pytest.approx(.5, rel=1e-12, abs=1e-12)
        dft = fourier_reference(SignalRecord(x, 128, "V"), BANDS)
        assert dft.powers == pytest.approx([0, .5, 0], abs=1e-12)


@pytest.mark.parametrize("settings", [
    {"wavelet": "db2"}, {"mode": "periodic"}, {"mode": "symmetric"},
    {"level": 1}, {"level": 3}, {"level": True}, {"level": 2.0},
    {"wavelet": True}, {"mode": True},
])
def test_reject_settings(settings):
    with pytest.raises(ValueError):
        DWTSettings(**settings)


@pytest.mark.parametrize("samples", [np.ones(3), np.ones(5), np.ones(6), np.ones(7)])
def test_reject_incompatible_length(samples):
    with pytest.raises(ValueError, match="divisible by four"):
        measure_dwt(SignalRecord(samples, 128, "V"), DWTSettings())


def test_reject_bad_input_and_range():
    for samples in (np.array([True] * 4), np.array([[1, 2], [3, 4]]),
                    np.array([1, np.nan, 2, 3])):
        with pytest.raises(ValueError):
            SignalRecord(samples, 128, "V")
    with pytest.raises(ValueError, match="numerical range"):
        measure_dwt(SignalRecord(np.full(8, 1e300), 128, "V"), DWTSettings())


def _run(config, out):
    return subprocess.run([sys.executable, "-m", "spectral_audit", "measure",
                           "--config", str(config), "--out", str(out)],
                          cwd=ROOT, capture_output=True, text=True)


def test_schema_v3_artifacts_and_strictness(tmp_path):
    config = ROOT / "configs" / "m1_dwt_16hz_phase0.toml"
    parsed = load_measure_config(config)
    assert resolved_measure_config(parsed)["schema_version"] == 3
    outputs = [tmp_path / "a", tmp_path / "b"]
    for out in outputs:
        run = _run(config, out)
        assert run.returncode == 0, run.stderr
        manifest = json.loads((out / "manifest.json").read_text())
        summary = json.loads((out / "summary.json").read_text())
        assert manifest["pywavelets_version"] == pywt.__version__
        assert manifest["pywavelets_distribution_version"] == importlib.metadata.version(
            "PyWavelets"
        )
        assert set(manifest["outputs"]) == {"comparisons.csv", "native_scales.csv", "summary.json"}
        for name, sha in manifest["outputs"].items():
            assert hashlib.sha256((out / name).read_bytes()).hexdigest() == sha
        assert any(item["path"].endswith("estimators/dwt.py") for item in manifest["source_files"])
        with (out / "native_scales.csv").open(newline="") as stream:
            rows = list(csv.DictReader(stream))
        assert [row["group"] for row in rows] == ["A2", "D2", "D1"]
        assert [int(row["coefficient_count"]) for row in rows] == [64, 64, 128]
        assert all(row["support_kind"] == "native_scale_group" for row in rows)
        assert all(row["difference_from_dft"] == "" for row in rows)
        assert all(
            row["difference_reason"] == "native_scale_not_exact_fourier_band" for row in rows
        )
        assert summary["density_unit"] is None
        assert summary["methods"][2]["groups"][0]["coefficient_mean_square_quantity_id"] == (
            "native_scale_coefficient_mean_square"
        )
        with (out / "comparisons.csv").open(newline="") as stream:
            comparisons = list(csv.DictReader(stream))
        assert len(comparisons) == 6
        assert comparisons[3]["difference_from_dft"]
    for name in ("comparisons.csv", "native_scales.csv", "summary.json"):
        assert (outputs[0] / name).read_bytes() == (outputs[1] / name).read_bytes()
    refused = _run(config, outputs[0])
    assert refused.returncode == 2 and "nonempty" in refused.stderr
    base = config.read_text()
    for bad in (base.replace("schema_version = 3", "schema_version = 2"),
                base.replace("level = 2", "level = true"),
                base.replace("wavelet = \"haar\"", "wavelet = \"db2\""),
                base + "\nunknown = 1\n"):
        path = tmp_path / f"bad{len(list(tmp_path.glob('bad*.toml')))}.toml"
        path.write_text(bad)
        assert _run(path, tmp_path / path.stem).returncode == 2
    old = ROOT / "configs" / "m1_welch_tones.toml"
    assert load_measure_config(old).dwt is None
    demo = ROOT / "configs" / "m0_tones.toml"
    v1_with_dwt = tmp_path / "v1_with_dwt.toml"
    v1_with_dwt.write_text(demo.read_text() + "\n[dwt]\nwavelet = 'haar'\n")
    with pytest.raises(ValueError, match="unknown keys"):
        load_demo_config(v1_with_dwt)


def test_failed_native_write_has_no_manifest(tmp_path, monkeypatch):
    import spectral_audit.io as output

    path = ROOT / "configs" / "m1_dwt_tones.toml"
    config = load_measure_config(path)
    record = make_tones(config.tones.signal, config.tones.record)
    reference = fourier_reference(record, config.tones.bands)
    welch = measure_welch(record, config.tones.bands, config.welch)
    native = measure_dwt(record, config.dwt)
    original = output._atomic_write

    def fail_native(target, data):
        if target.name == "native_scales.csv":
            raise OSError("injected failure")
        return original(target, data)

    monkeypatch.setattr(output, "_atomic_write", fail_native)
    out = tmp_path / "failed"
    with pytest.raises(OSError, match="injected failure"):
        write_measure_run(out, config, record, reference, welch, path, ROOT,
                          datetime.now(UTC), 0, [], native)
    assert not (out / "manifest.json").exists()


def test_zero_serialization_and_shared_identity(tmp_path):
    source = ROOT / "configs" / "m1_dwt_tones.toml"
    config_path = tmp_path / "zero.toml"
    config_path.write_text(source.read_text().replace(
        "amplitudes = [1.0, 0.5]", "amplitudes = [0.0, 0.0]"
    ))
    out = tmp_path / "zero"
    assert _run(config_path, out).returncode == 0
    with (out / "native_scales.csv").open(newline="") as stream:
        rows = list(csv.DictReader(stream))
    assert all(row["record_power_contribution"] == "0" for row in rows)
    assert all(row["coefficient_mean_square"] == "0" for row in rows)
    assert all(row["absolute_status"] == "ok" for row in rows)
    assert all(row["record_power_fraction"] == "" for row in rows)
    assert all(row["record_fraction_reason"] == "zero_record_power" for row in rows)
    assert all(row["method_fraction_reason"] == "zero_method_total_power" for row in rows)
    summary = json.loads((out / "summary.json").read_text())
    assert summary["methods"][2]["groups"][0]["record_power_fraction"] is None

    config = load_measure_config(source)
    record = make_tones(config.tones.signal, config.tones.record)
    reference = fourier_reference(record, config.tones.bands)
    welch = measure_welch(record, config.tones.bands, config.welch)
    native = measure_dwt(record, config.dwt)
    with pytest.raises(ValueError, match="shared record"):
        write_measure_run(tmp_path / "mismatch", config, record, reference, welch,
                          source, ROOT, datetime.now(UTC), 0, [],
                          replace(native, sample_unit="other"))
