"""Independent numerical and contract checks for the bounded Welch family."""

import csv
import hashlib
import json
import subprocess
import sys
from pathlib import Path

import numpy as np
import pytest

from spectral_audit.config import canonical_json_bytes, load_measure_config
from spectral_audit.estimators.welch import WelchSettings, measure_welch
from spectral_audit.reference import fourier_reference
from spectral_audit.signals import make_tones
from spectral_audit.types import Band, SignalRecord

ROOT = Path(__file__).resolve().parents[1]
BANDS_4 = (Band("low", 0, 1), Band("high", 1, 2, True))


def oracle(samples, fs, length, overlap, bands):
    """Direct exponential DFT matrix, independent of the production spectral path."""
    starts = list(range(0, len(samples) - length + 1, length - overlap))
    t = np.arange(length)
    window = 0.5 - 0.5 * np.cos(2 * np.pi * t / length)
    transform = np.exp(-2j * np.pi * np.outer(t, t) / length)
    coefficients = np.array([transform @ (window * samples[s : s + length]) for s in starts])
    indices = np.arange(length // 2 + 1)
    multiplicity = np.array(
        [1 if k == 0 or (length % 2 == 0 and k == length // 2) else 2 for k in indices]
    )
    density = np.mean(abs(coefficients[:, indices]) ** 2, axis=0)
    density *= multiplicity / (fs * np.sum(window**2))
    frequencies = indices * fs / length
    powers = [
        np.sum(
            density[
                (frequencies >= b.lower_hz)
                & (frequencies <= b.upper_hz if b.include_upper else frequencies < b.upper_hz)
            ]
        )
        * fs
        / length
        for b in bands
    ]
    return density, powers


@pytest.mark.parametrize(
    "length, samples",
    [
        (4, [1, 2, 3, 4, 5, 6]),
        (5, [2, -1, 0, 3, -2, 1, 4, 0]),
        (4, [1, 1, 1, 1, 1, 1]),
        (4, [1, -1, 1, -1, 1, -1]),
    ],
)
def test_small_explicit_dft_oracle(length, samples):
    fs = 10.0
    bands = (Band("dc_side", 0, 2.5), Band("upper", 2.5, 5, True))
    record = SignalRecord(np.array(samples), fs, "V")
    settings = WelchSettings(length, 2 if length == 4 else 1)
    result = measure_welch(record, bands, settings)
    density, expected = oracle(record.samples, fs, length, settings.noverlap, bands)
    assert result.powers == pytest.approx(expected, rel=1e-12, abs=1e-12)
    assert result.method_total == pytest.approx(np.sum(density) * fs / length, rel=1e-12)
    scaled = measure_welch(SignalRecord(3 * record.samples, fs, "V"), bands, settings)
    assert scaled.powers == pytest.approx(9 * np.array(expected), rel=1e-12, abs=9e-12)


def test_impulse_coverage_and_denominators():
    samples = np.array([0, 0, 1, 0, 0, 0])
    record = SignalRecord(samples, 4, "V")
    result = measure_welch(record, BANDS_4, WelchSettings(4, 2))
    dft = fourier_reference(record, BANDS_4)
    assert dft.powers == pytest.approx([1 / 12, 1 / 12], rel=1e-12, abs=1e-12)
    assert result.powers == pytest.approx([1 / 12, 1 / 4], rel=1e-12, abs=1e-12)
    assert result.record_power == pytest.approx(1 / 6)
    assert result.method_total == pytest.approx(1 / 3)
    assert result.fractions == pytest.approx([1 / 2, 3 / 2])
    assert result.method_total_fractions == pytest.approx([1 / 4, 3 / 4])
    assert result.support["frame_starts"] == (0, 2)
    assert result.support["omitted_sample_indices"] == []
    assert result.support["zero_taper_weight_sample_indices"] == [0]

    edge = np.zeros(6)
    edge[0] = 1
    zero_method = measure_welch(SignalRecord(edge, 4, "V"), BANDS_4, WelchSettings(4, 2))
    assert zero_method.record_power > 0
    assert zero_method.method_total == 0
    assert zero_method.fractions == (0, 0)
    assert zero_method.method_total_fractions == (None, None)
    assert zero_method.method_total_reasons == ("zero_method_total_power",) * 2
    assert zero_method.power_statuses == ("ok", "ok")

    tail = np.zeros(7)
    tail[6] = 1
    omitted = measure_welch(SignalRecord(tail, 4, "V"), BANDS_4, WelchSettings(4, 2))
    assert omitted.support["omitted_sample_indices"] == [6]
    assert omitted.support["zero_taper_weight_sample_indices"] == [0]
    assert omitted.method_total == 0
    assert omitted.record_power == pytest.approx(1 / 7)

    zero = measure_welch(SignalRecord(np.zeros(6), 4, "V"), BANDS_4, WelchSettings(4, 2))
    assert zero.fractions == (None, None)
    assert zero.reasons == ("zero_record_power",) * 2
    assert zero.method_total_reasons == ("zero_method_total_power",) * 2


@pytest.mark.parametrize(
    "config_file, expected_dft, expected_welch",
    [
        ("m1_welch_tones.toml", [0.5, 0.125, 0], [0.5, 0.125, 0]),
        ("m1_welch_edge_tone.toml", [0, 0.5, 0], [1 / 12, 5 / 12, 0]),
    ],
)
def test_configured_tones(config_file, expected_dft, expected_welch):
    config = load_measure_config(ROOT / "configs" / config_file)
    record = make_tones(config.tones.signal, config.tones.record)
    dft = fourier_reference(record, config.tones.bands)
    welch = measure_welch(record, config.tones.bands, config.welch)
    assert dft.powers == pytest.approx(expected_dft, rel=1e-12, abs=1e-12)
    assert welch.powers == pytest.approx(expected_welch, rel=1e-12, abs=1e-12)
    assert welch.method_total == pytest.approx(sum(expected_welch), rel=1e-12)
    assert welch.support["frame_starts"] == (0, 32, 64, 96, 128, 160, 192)


def test_white_noise_windowed_identity_and_ensemble():
    n, length, overlap, variance, replicates = 256, 64, 32, 1.7, 512
    fs = 128
    starts = range(0, n - length + 1, length - overlap)
    window = 0.5 - 0.5 * np.cos(2 * np.pi * np.arange(length) / length)
    u = sum(window**2)
    q = np.zeros(n)
    for start in starts:
        q[start : start + length] += window**2 / (len(starts) * u)
    standard_error = np.sqrt(2 * variance**2 * sum(q**2) / replicates)
    bands = (Band("low", 0, 16), Band("mid", 16, 32), Band("high", 32, 64, True))
    rng = np.random.default_rng(20261030)
    totals = []
    for _ in range(replicates):
        samples = rng.normal(scale=np.sqrt(variance), size=n)
        result = measure_welch(
            SignalRecord(samples, fs, "V"), bands, WelchSettings(length, overlap)
        )
        independent = sum(
            np.dot(window * samples[s : s + length], window * samples[s : s + length])
            for s in starts
        ) / (len(starts) * u)
        assert result.method_total == pytest.approx(independent, rel=1e-12, abs=1e-12)
        assert abs(result.accounting_error) <= 1e-12 * result.method_total
        totals.append(result.method_total)
    assert abs(np.mean(totals) - variance) <= 6 * standard_error


@pytest.mark.parametrize(
    "settings",
    [
        {"segment_length": True},
        {"segment_length": 1},
        {"noverlap": True},
        {"noverlap": -1},
        {"noverlap": 64},
        {"nfft": 128},
        {"nfft": True},
        {"taper": "hann_symmetric"},
        {"detrend": True},
        {"scaling": "spectrum"},
        {"average": "median"},
        {"padding": "zero"},
        {"boundary": "extend"},
        {"sidedness": "twosided"},
    ],
)
def test_invalid_settings(settings):
    with pytest.raises(ValueError):
        WelchSettings(**settings)


def test_too_short_and_empty_bin_band():
    record = SignalRecord(np.ones(6), 4, "V")
    with pytest.raises(ValueError, match="exceeds record"):
        measure_welch(record, BANDS_4, WelchSettings(7, 2))
    narrow = (Band("dc", 0, 0.1), Band("empty", 0.1, 0.2), Band("rest", 0.2, 2, True))
    with pytest.raises(ValueError, match="no Welch estimator bins"):
        measure_welch(record, narrow, WelchSettings(4, 2))


def test_measure_cli_artifacts_and_rejections(tmp_path):
    config = ROOT / "configs" / "m1_welch_edge_tone.toml"
    outputs = [tmp_path / "a", tmp_path / "b"]
    for out in outputs:
        command = [
            sys.executable,
            "-m",
            "spectral_audit",
            "measure",
            "--config",
            str(config),
            "--out",
            str(out),
        ]
        result = subprocess.run(command, cwd=ROOT, capture_output=True, text=True)
        assert result.returncode == 0, result.stderr
        manifest = json.loads((out / "manifest.json").read_text(encoding="utf-8"))
        summary = json.loads((out / "summary.json").read_text(encoding="utf-8"))
        assert manifest["run_status"] == "complete"
        assert manifest["scipy_version"]
        assert (
            manifest["resolved_configuration_sha256"]
            == hashlib.sha256(canonical_json_bytes(manifest["resolved_configuration"])).hexdigest()
        )
        assert [row["path"] for row in manifest["source_files"]] == sorted(
            row["path"] for row in manifest["source_files"]
        )
        for item in manifest["source_files"]:
            assert item["sha256"] == hashlib.sha256((ROOT / item["path"]).read_bytes()).hexdigest()
        for name, sha in manifest["outputs"].items():
            assert sha == hashlib.sha256((out / name).read_bytes()).hexdigest()
        assert summary["comparison_status"] == "descriptive"
        assert (
            summary["methods"][1]["settings_hash"]
            == hashlib.sha256(canonical_json_bytes(summary["methods"][1]["settings"])).hexdigest()
        )
        with (out / "comparisons.csv").open(newline="", encoding="utf-8") as stream:
            rows = list(csv.DictReader(stream))
        assert len(rows) == 6
        assert rows[3]["difference_from_dft"]
    for name in ("comparisons.csv", "summary.json"):
        assert (outputs[0] / name).read_bytes() == (outputs[1] / name).read_bytes()
    collision = subprocess.run(command, cwd=ROOT, capture_output=True, text=True)
    assert collision.returncode == 2
    assert "nonempty" in collision.stderr
    malformed = tmp_path / "bad.toml"
    malformed.write_text(config.read_text(encoding="utf-8") + "\nunknown = 1\n", encoding="utf-8")
    rejected = subprocess.run(
        [
            sys.executable,
            "-m",
            "spectral_audit",
            "measure",
            "--config",
            str(malformed),
            "--out",
            str(tmp_path / "bad"),
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    assert rejected.returncode == 2


def test_measure_failed_write_has_no_completion_manifest(tmp_path, monkeypatch):
    from datetime import UTC, datetime

    import spectral_audit.io as output

    config_path = ROOT / "configs" / "m1_welch_tones.toml"
    config = load_measure_config(config_path)
    record = make_tones(config.tones.signal, config.tones.record)
    reference = fourier_reference(record, config.tones.bands)
    estimate = measure_welch(record, config.tones.bands, config.welch)
    original = output._atomic_write

    def fail_summary(path, data):
        if path.name == "summary.json":
            raise OSError("injected failure")
        return original(path, data)

    monkeypatch.setattr(output, "_atomic_write", fail_summary)
    out = tmp_path / "failed"
    with pytest.raises(OSError, match="injected failure"):
        output.write_measure_run(out, config, record, reference, estimate, config_path,
                                 ROOT, datetime.now(UTC), 0, [])
    assert not (out / "manifest.json").exists()
