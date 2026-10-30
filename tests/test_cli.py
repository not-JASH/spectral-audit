import csv
import hashlib
import json
import subprocess
import sys
from datetime import UTC
from pathlib import Path

import numpy as np
import pytest

from spectral_audit import __version__

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "configs" / "m0_tones.toml"


def run_cli(*args):
    return subprocess.run(
        [sys.executable, "-m", "spectral_audit", *map(str, args)],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )


def test_help_and_version():
    assert "demo" in run_cli("--help").stdout
    result = run_cli("--version")
    assert result.returncode == 0
    assert __version__ in result.stdout


def test_demo_outputs_and_provenance(tmp_path):
    outputs = [tmp_path / "a", tmp_path / "b"]
    for out in outputs:
        result = run_cli("demo", "--config", CONFIG, "--out", out)
        assert result.returncode == 0, result.stderr
        manifest = json.loads((out / "manifest.json").read_text(encoding="utf-8"))
        summary = json.loads((out / "summary.json").read_text(encoding="utf-8"))
        with (out / "band_powers.csv").open(newline="", encoding="utf-8") as stream:
            rows = list(csv.DictReader(stream))
        assert set(p.name for p in out.iterdir()) == {
            "band_powers.csv",
            "summary.json",
            "manifest.json",
        }
        assert [row["band"] for row in rows] == ["low", "mid", "high"]
        assert [float(row["band_power"]) for row in rows] == pytest.approx(
            [0.5, 0.125, 0], rel=1e-12, abs=1e-12
        )
        assert [float(row["record_power_fraction"]) for row in rows] == pytest.approx(
            [0.8, 0.2, 0], rel=1e-12, abs=1e-12
        )
        assert summary["record_power"] == pytest.approx(0.625, rel=1e-12)
        assert summary["sum_band_power"] == pytest.approx(0.625, rel=1e-12)
        assert summary["status"] == "ok"
        assert summary["power_unit"] == "(a.u.)^2"
        assert manifest["run_status"] == "complete"
        assert manifest["resolved_configuration"]["record"]["mean_policy"] == "none"
        assert manifest["source_files"] and manifest["source_digest"]
        assert manifest["source_state"] in {"unversioned", "dirty", "clean"}
        assert manifest["source_config_sha256"] == hashlib.sha256(CONFIG.read_bytes()).hexdigest()
        canonical = json.dumps(
            manifest["resolved_configuration"],
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        ).encode("utf-8")
        assert manifest["resolved_configuration_sha256"] == hashlib.sha256(canonical).hexdigest()
        indices = np.arange(256)
        signal = np.sin(2 * np.pi * 8 * indices / 128)
        signal += 0.5 * np.sin(2 * np.pi * 24 * indices / 128)
        assert (
            manifest["signal"]["sha256"]
            == hashlib.sha256(np.asarray(signal, dtype="<f8").tobytes()).hexdigest()
        )
        inventory = manifest["source_files"]
        assert inventory == sorted(inventory, key=lambda item: item["path"])
        for item in inventory:
            assert item["sha256"] == hashlib.sha256((ROOT / item["path"]).read_bytes()).hexdigest()
        inventory_bytes = json.dumps(
            inventory, sort_keys=True, separators=(",", ":"), ensure_ascii=False
        ).encode("utf-8")
        assert manifest["source_digest"] == hashlib.sha256(inventory_bytes).hexdigest()
        for name in ("band_powers.csv", "summary.json"):
            assert (
                manifest["outputs"][name] == hashlib.sha256((out / name).read_bytes()).hexdigest()
            )
    for name in ("band_powers.csv", "summary.json"):
        assert (outputs[0] / name).read_bytes() == (outputs[1] / name).read_bytes()


def test_refuse_nonempty_output(tmp_path):
    out = tmp_path / "occupied"
    out.mkdir()
    marker = out / "keep.txt"
    marker.write_text("keep", encoding="utf-8")
    result = run_cli("demo", "--config", CONFIG, "--out", out)
    assert result.returncode == 2
    assert "nonempty" in result.stderr
    assert marker.read_text(encoding="utf-8") == "keep"
    assert not (out / "manifest.json").exists()


def test_failed_write_has_no_completion_manifest(tmp_path, monkeypatch):
    from datetime import datetime

    import spectral_audit.io as output
    from spectral_audit.config import load_demo_config
    from spectral_audit.reference import fourier_reference
    from spectral_audit.signals import make_tones

    config = load_demo_config(CONFIG)
    record = make_tones(config.signal, config.record)
    measure = fourier_reference(record, config.bands)
    original = output._atomic_write

    def fail_summary(path, data):
        if path.name == "summary.json":
            raise OSError("injected failure")
        return original(path, data)

    monkeypatch.setattr(output, "_atomic_write", fail_summary)
    out = tmp_path / "failed"
    with pytest.raises(OSError, match="injected failure"):
        output.write_demo_run(out, config, record, measure, CONFIG, ROOT, datetime.now(UTC), 0, [])
    assert not (out / "manifest.json").exists()


def test_zero_power_output_uses_null_fractions(tmp_path):
    content = CONFIG.read_text(encoding="utf-8").replace(
        "amplitudes = [1.0, 0.5]", "amplitudes = [0.0, 0.0]"
    )
    config = tmp_path / "zero.toml"
    config.write_text(content, encoding="utf-8")
    out = tmp_path / "zero"
    result = run_cli("demo", "--config", config, "--out", out)
    assert result.returncode == 0, result.stderr
    summary = json.loads((out / "summary.json").read_text(encoding="utf-8"))
    assert summary["status"] == "undefined"
    assert all(band["record_power_fraction"] is None for band in summary["bands"])
    assert all(band["reason"] == "zero_reference_power" for band in summary["bands"])
    with (out / "band_powers.csv").open(newline="", encoding="utf-8") as stream:
        assert all(row["record_power_fraction"] == "" for row in csv.DictReader(stream))
