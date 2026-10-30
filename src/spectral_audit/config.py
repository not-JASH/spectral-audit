"""Strict schema-v1 demo configuration."""

import json
import tomllib
from dataclasses import dataclass
from pathlib import Path

from spectral_audit.estimators.welch import WelchSettings
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
    return _parse_tones(data, 1)


def _parse_tones(data: dict, version: int) -> DemoConfig:
    expected = {"schema_version", "experiment_id", "record", "signal", "bands", "reference"}
    if version == 2:
        expected.add("welch")
    _keys(data, expected)
    if type(data["schema_version"]) is not int or data["schema_version"] != version:
        raise ValueError(f"unsupported schema_version; expected {version}")
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


@dataclass(frozen=True)
class MeasureConfig:
    tones: DemoConfig
    welch: WelchSettings


def load_measure_config(path: Path) -> MeasureConfig:
    with path.open("rb") as stream:
        data = tomllib.load(stream)
    tones = _parse_tones(data, 2)
    w = _keys(
        data["welch"],
        {"method_id", "segment_length", "noverlap"},
        {"nfft", "taper", "detrend", "sidedness", "scaling", "average", "boundary", "padding"},
    )
    if w["method_id"] != "welch_mean_density_v1":
        raise ValueError("unsupported Welch method_id")
    return MeasureConfig(
        tones,
        WelchSettings(
            segment_length=w["segment_length"],
            noverlap=w["noverlap"],
            nfft=w.get("nfft"),
            taper=w.get("taper", "hann_periodic"),
            detrend=w.get("detrend", False),
            sidedness=w.get("sidedness", "onesided"),
            scaling=w.get("scaling", "density"),
            average=w.get("average", "mean"),
            boundary=w.get("boundary", "none"),
            padding=w.get("padding", "none"),
        ),
    )


def resolved_measure_config(config: MeasureConfig) -> dict:
    result = resolved_config(config.tones)
    result["schema_version"] = 2
    result["welch"] = config.welch.resolved()
    return result


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
