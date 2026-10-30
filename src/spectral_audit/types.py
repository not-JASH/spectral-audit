"""Validated immutable configuration and measurement values."""

from dataclasses import dataclass, field
from math import isfinite

import numpy as np


def finite_number(value: object, label: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{label} must be a finite number")
    result = float(value)
    if not isfinite(result):
        raise ValueError(f"{label} must be finite")
    return result


@dataclass(frozen=True)
class Band:
    name: str
    lower_hz: float
    upper_hz: float
    include_upper: bool = False

    def __post_init__(self) -> None:
        if not isinstance(self.name, str) or not self.name.strip():
            raise ValueError("band name must be nonempty")
        lo = finite_number(self.lower_hz, "lower_hz")
        hi = finite_number(self.upper_hz, "upper_hz")
        if lo < 0 or hi <= lo:
            raise ValueError("band bounds must be nonnegative and increasing")
        if type(self.include_upper) is not bool:
            raise ValueError("include_upper must be boolean")
        object.__setattr__(self, "lower_hz", lo)
        object.__setattr__(self, "upper_hz", hi)


def validate_bands(bands: tuple[Band, ...], fs: float) -> tuple[Band, ...]:
    if not bands:
        raise ValueError("bands must be nonempty")
    nyquist = fs / 2
    if len({b.name for b in bands}) != len(bands):
        raise ValueError("band names must be unique")
    if bands[0].lower_hz != 0:
        raise ValueError("bands must start at 0 Hz")
    resolved = []
    edge = 0.0
    for i, band in enumerate(bands):
        tolerance = 1e-12 * max(1.0, fs, abs(edge))
        if abs(band.lower_hz - edge) > tolerance:
            raise ValueError("bands must be ordered, nonoverlapping, and contiguous")
        if band.include_upper != (i == len(bands) - 1):
            raise ValueError("only the final band must include its upper edge")
        if band.upper_hz > nyquist + tolerance:
            raise ValueError("band upper edge exceeds Nyquist")
        resolved.append(Band(band.name, edge, band.upper_hz, band.include_upper))
        edge = band.upper_hz
    if abs(edge - nyquist) > 1e-12 * max(1.0, fs):
        raise ValueError("bands must end at Nyquist")
    resolved[-1] = Band(resolved[-1].name, resolved[-1].lower_hz, nyquist, True)
    return tuple(resolved)


@dataclass(frozen=True)
class RecordConfig:
    n_samples: int
    sampling_rate_hz: float
    sample_unit: str
    mean_policy: str = "none"

    def __post_init__(self) -> None:
        if type(self.n_samples) is not int or self.n_samples < 2:
            raise ValueError("n_samples must be an integer >= 2")
        fs = finite_number(self.sampling_rate_hz, "sampling_rate_hz")
        if fs <= 0:
            raise ValueError("sampling_rate_hz must be positive")
        if not isinstance(self.sample_unit, str) or not self.sample_unit.strip():
            raise ValueError("sample_unit must be nonempty")
        if self.mean_policy != "none":
            raise ValueError("mean_policy must be 'none' in M0")
        object.__setattr__(self, "sampling_rate_hz", fs)


@dataclass(frozen=True)
class ToneSignalConfig:
    frequencies_hz: tuple[float, ...]
    amplitudes: tuple[float, ...]
    phases_rad: tuple[float, ...]

    def __post_init__(self) -> None:
        if (
            not self.frequencies_hz
            or len(self.frequencies_hz) != len(self.amplitudes)
            or len(self.frequencies_hz) != len(self.phases_rad)
        ):
            raise ValueError("tone arrays must have equal nonzero lengths")
        for label in ("frequencies_hz", "amplitudes", "phases_rad"):
            values = tuple(finite_number(v, label) for v in getattr(self, label))
            object.__setattr__(self, label, values)


@dataclass(frozen=True)
class DemoConfig:
    experiment_id: str
    record: RecordConfig
    signal: ToneSignalConfig
    bands: tuple[Band, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.experiment_id, str) or not self.experiment_id.strip():
            raise ValueError("experiment_id must be nonempty")
        object.__setattr__(self, "bands", validate_bands(self.bands, self.record.sampling_rate_hz))
        for frequency in self.signal.frequencies_hz:
            if not 0 < frequency < self.record.sampling_rate_hz / 2:
                raise ValueError("tone frequencies_hz must lie strictly between DC and Nyquist")


@dataclass(frozen=True)
class SignalRecord:
    samples: np.ndarray = field(repr=False)
    sampling_rate_hz: float
    sample_unit: str

    def __post_init__(self) -> None:
        raw = np.asarray(self.samples)
        if raw.ndim != 1 or raw.size < 2 or raw.dtype.kind not in "iuf":
            raise ValueError("samples must be a real numeric vector of length >= 2")
        samples = np.array(raw, dtype=np.float64, order="C", copy=True)
        if not np.all(np.isfinite(samples)):
            raise ValueError("samples must be finite float64 values")
        samples.setflags(write=False)
        fs = finite_number(self.sampling_rate_hz, "sampling_rate_hz")
        if fs <= 0:
            raise ValueError("sampling_rate_hz must be positive")
        if not isinstance(self.sample_unit, str) or not self.sample_unit.strip():
            raise ValueError("sample_unit must be nonempty")
        object.__setattr__(self, "samples", samples)
        object.__setattr__(self, "sampling_rate_hz", fs)


@dataclass(frozen=True)
class Measurement:
    method_id: str
    reference_id: str
    target_id: str
    bands: tuple[Band, ...]
    powers: tuple[float, ...]
    record_power: float
    fractions: tuple[float | None, ...]
    status: str
    reasons: tuple[str | None, ...]
    measurement_kind: str = "finite_record_fourier"
    population_target_kind: str | None = None
    method_total_power: float | None = None
    method_total_fractions: tuple[float | None, ...] = ()
    method_total_reasons: tuple[str | None, ...] = ()
    power_statuses: tuple[str, ...] = ()
    power_reasons: tuple[str | None, ...] = ()
    settings: dict | None = None
    settings_hash: str | None = None
    support: dict | None = None
    record_id: str | None = None
    accounting_error: float | None = None
    n_samples: int | None = None
    sampling_rate_hz: float | None = None
    sample_unit: str | None = None
    power_unit: str | None = None
    density_unit: str | None = None
    preprocessing: str = "none"

    @property
    def method_total(self) -> float:
        return self.method_total_power if self.method_total_power is not None else sum(self.powers)
