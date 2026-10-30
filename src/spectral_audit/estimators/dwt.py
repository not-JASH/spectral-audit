"""One finite, orthonormal two-level Haar native-scale measurement."""

import json
from dataclasses import dataclass
from hashlib import sha256

import numpy as np
import pywt

from spectral_audit.types import SignalRecord

METHOD_ID = "dwt_haar_periodization_level2_v1"


@dataclass(frozen=True)
class DWTSettings:
    wavelet: str = "haar"
    level: int = 2
    mode: str = "periodization"

    def __post_init__(self) -> None:
        if type(self.wavelet) is not str or self.wavelet != "haar":
            raise ValueError("unsupported wavelet; expected 'haar'")
        if type(self.level) is not int or self.level != 2:
            raise ValueError("unsupported level; expected integer 2")
        if type(self.mode) is not str or self.mode != "periodization":
            raise ValueError("unsupported mode; expected 'periodization'")

    def resolved(self) -> dict:
        return {
            "method_id": METHOD_ID,
            "wavelet": self.wavelet,
            "level": self.level,
            "mode": self.mode,
            "preprocessing": "none",
            "retained_coefficient_policy": "all_coefficients",
            "normalization": "sum_squared_coefficients_divided_by_record_length",
            "coefficient_order": ["A2", "D2", "D1"],
        }


@dataclass(frozen=True)
class NativeGroup:
    name: str
    coefficient_count: int
    sum_squared_coefficients: float
    record_power_contribution: float
    coefficient_mean_square: float
    nominal_lower_hz: float
    nominal_upper_hz: float
    support_kind: str = "native_scale_group"

    def __post_init__(self) -> None:
        if self.name not in {"A2", "D2", "D1"} or type(self.coefficient_count) is not int:
            raise ValueError("invalid native group")
        if self.coefficient_count < 1 or self.support_kind != "native_scale_group":
            raise ValueError("invalid native group support")
        values = (
            self.sum_squared_coefficients,
            self.record_power_contribution,
            self.coefficient_mean_square,
            self.nominal_lower_hz,
            self.nominal_upper_hz,
        )
        if not all(np.isfinite(v) for v in values) or any(v < 0 for v in values):
            raise ValueError("numerical range exceeded in DWT measurement")


@dataclass(frozen=True)
class NativeScaleResult:
    method_id: str
    settings: dict
    settings_hash: str
    record_id: str
    n_samples: int
    sampling_rate_hz: float
    sample_unit: str
    power_unit: str
    preprocessing: str
    groups: tuple[NativeGroup, ...]
    coefficients: tuple[tuple[float, ...], ...]
    record_power: float
    method_total_power: float
    record_power_fractions: tuple[float | None, ...]
    method_total_fractions: tuple[float | None, ...]
    record_fraction_reasons: tuple[str | None, ...]
    method_fraction_reasons: tuple[str | None, ...]

    def __post_init__(self) -> None:
        if tuple(g.name for g in self.groups) != ("A2", "D2", "D1"):
            raise ValueError("native group order must be A2, D2, D1")
        if self.method_id != METHOD_ID or self.preprocessing != "none":
            raise ValueError("invalid native method identity or preprocessing")
        if self.n_samples < 4 or self.n_samples % 4:
            raise ValueError("invalid native record length")
        if sum(g.coefficient_count for g in self.groups) != self.n_samples:
            raise ValueError("DWT coefficient counts do not cover record")
        if tuple(g.coefficient_count for g in self.groups) != (
            self.n_samples // 4, self.n_samples // 4, self.n_samples // 2
        ):
            raise ValueError("DWT group counts violate supported contract")
        if len(self.coefficients) != 3 or any(
            len(c) != g.coefficient_count
            for c, g in zip(self.coefficients, self.groups, strict=True)
        ):
            raise ValueError("DWT coefficient arrays do not match group counts")
        if any(len(v) != 3 for v in (
            self.record_power_fractions, self.method_total_fractions,
            self.record_fraction_reasons, self.method_fraction_reasons,
        )):
            raise ValueError("invalid native fraction lengths")
        if not np.isfinite(self.record_power) or not np.isfinite(self.method_total_power):
            raise ValueError("numerical range exceeded in DWT measurement")


def measure_dwt(record: SignalRecord, settings: DWTSettings) -> NativeScaleResult:
    if not isinstance(settings, DWTSettings):
        raise ValueError("settings must be DWTSettings")
    n = record.samples.size
    if n < 4 or n % 4:
        raise ValueError("DWT record length must be >= 4 and divisible by four")
    try:
        with np.errstate(over="raise", invalid="raise"):
            coefficients = pywt.wavedec(
                record.samples.copy(), wavelet=settings.wavelet, mode=settings.mode,
                level=settings.level,
            )
            energies = [float(np.dot(c, c)) for c in coefficients]
            record_power = float(np.dot(record.samples, record.samples) / n)
            powers = [energy / n for energy in energies]
            means = [energy / len(c) for energy, c in zip(energies, coefficients, strict=True)]
            total = float(sum(powers))
    except (FloatingPointError, OverflowError) as exc:
        raise ValueError("numerical range exceeded in DWT measurement") from exc
    if not all(np.isfinite(v) for v in (*energies, record_power, *powers, *means, total)):
        raise ValueError("numerical range exceeded in DWT measurement")
    counts = [len(c) for c in coefficients]
    if counts != [n // 4, n // 4, n // 2]:
        raise ValueError("DWT coefficient counts violate supported contract")
    if not np.isclose(total, record_power, rtol=1e-12, atol=1e-12 * record_power):
        raise ValueError("DWT powers disagree with record mean square")
    fs = record.sampling_rate_hz
    bounds = [(0.0, fs / 8), (fs / 8, fs / 4), (fs / 4, fs / 2)]
    groups = tuple(
        NativeGroup(name, count, energy, power, mean, lo, hi)
        for name, count, energy, power, mean, (lo, hi) in zip(
            ("A2", "D2", "D1"), counts, energies, powers, means, bounds, strict=True
        )
    )
    settings_dict = settings.resolved()
    settings_hash = sha256(
        json.dumps(settings_dict, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    record_id = sha256(np.asarray(record.samples, dtype="<f8", order="C").tobytes()).hexdigest()
    return NativeScaleResult(
        METHOD_ID, settings_dict, settings_hash, record_id, n, fs, record.sample_unit,
        f"({record.sample_unit})^2", "none", groups,
        tuple(tuple(float(v) for v in c) for c in coefficients), record_power, total,
        tuple(None if record_power == 0 else p / record_power for p in powers),
        tuple(None if total == 0 else p / total for p in powers),
        tuple("zero_record_power" if record_power == 0 else None for _ in groups),
        tuple("zero_method_total_power" if total == 0 else None for _ in groups),
    )
