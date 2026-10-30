"""Strict schema-v1 demo configuration."""

import json
import tomllib
from pathlib import Path

from spectral_audit.types import Band, DemoConfig, RecordConfig, ToneSignalConfig


def _keys(data: object, required: set[str], optional: set[str] = frozenset()) -> dict:
    if not isinstance(data, dict):
        raise ValueError("configuration section must be a table")
    missing = required - data.keys()
    unknown = data.keys() - required - optional
    if missing or unknown:
        raise ValueError(f"configuration missing {sorted(missing)}; unknown keys {sorted(unknown)}")
    return data


def _array(value: object, label: str) -> tuple:
    if not isinstance(value, list):
        raise ValueError(f"{label} must be an array")
    return tuple(value)


def load_demo_config(path: Path) -> DemoConfig:
    with path.open("rb") as stream:
        data = tomllib.load(stream)
    _keys(data, {"schema_version", "experiment_id", "record", "signal", "bands", "reference"})
    if type(data["schema_version"]) is not int or data["schema_version"] != 1:
        raise ValueError("unsupported schema_version; expected 1")
    r = _keys(data["record"], {"n_samples", "sampling_rate_hz", "sample_unit"}, {"mean_policy"})
    s = _keys(data["signal"], {"kind", "frequencies_hz", "amplitudes", "phases_rad"})
    ref = _keys(data["reference"], {"kind", "fft_norm"})
    if s["kind"] != "tones" or ref != {"kind": "finite_record_dft", "fft_norm": "ortho"}:
        raise ValueError("unsupported signal kind or reference settings")
    if not isinstance(data["bands"], list):
        raise ValueError("bands must be an array of tables")
    bands = []
    for item in data["bands"]:
        b = _keys(item, {"name", "lower_hz", "upper_hz"}, {"include_upper"})
        bands.append(Band(b["name"], b["lower_hz"], b["upper_hz"], b.get("include_upper", False)))
    return DemoConfig(
        data["experiment_id"],
        RecordConfig(
            r["n_samples"], r["sampling_rate_hz"], r["sample_unit"], r.get("mean_policy", "none")
        ),
        ToneSignalConfig(
            _array(s["frequencies_hz"], "frequencies_hz"),
            _array(s["amplitudes"], "amplitudes"),
            _array(s["phases_rad"], "phases_rad"),
        ),
        tuple(bands),
    )


def resolved_config(config: DemoConfig) -> dict:
    return {
        "schema_version": 1,
        "experiment_id": config.experiment_id,
        "record": {
            "n_samples": config.record.n_samples,
            "sampling_rate_hz": config.record.sampling_rate_hz,
            "sample_unit": config.record.sample_unit,
            "mean_policy": config.record.mean_policy,
        },
        "signal": {
            "kind": "tones",
            "frequencies_hz": config.signal.frequencies_hz,
            "amplitudes": config.signal.amplitudes,
            "phases_rad": config.signal.phases_rad,
            "generation": "sum(amplitude*sin(2*pi*frequency_hz*j/fs+phase_rad)); j=0..n-1",
        },
        "bands": [
            {
                "name": b.name,
                "lower_hz": b.lower_hz,
                "upper_hz": b.upper_hz,
                "include_upper": b.include_upper,
            }
            for b in config.bands
        ],
        "reference": {
            "kind": "finite_record_dft",
            "fft_norm": "ortho",
            "bin_selection": "absolute_physical_frequency",
            "denominator": "actual_record_mean_square",
        },
    }


def canonical_json_bytes(value: object) -> bytes:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False
    ).encode("utf-8")
