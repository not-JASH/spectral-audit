"""Fixed-family, mean-density Welch band measurement."""

import json
from dataclasses import dataclass
from hashlib import sha256

import numpy as np
from scipy.signal import welch
from scipy.signal.windows import hann

from spectral_audit.estimators.base import EstimatorContract
from spectral_audit.types import Band, Measurement, SignalRecord, validate_bands

METHOD_ID = "welch_mean_density_v1"
CONTRACT = EstimatorContract(
    METHOD_ID,
    "finite_record_windowed_band_power",
    "global_mean_none; per_frame_detrend_false",
    "complete_frames_from_zero_no_padding",
    "mean_one_sided_density_bin_sum; window_squared_energy",
)


@dataclass(frozen=True)
class WelchSettings:
    segment_length: int = 64
    noverlap: int = 32
    nfft: int | None = None
    taper: str = "hann_periodic"
    detrend: bool = False
    sidedness: str = "onesided"
    scaling: str = "density"
    average: str = "mean"
    boundary: str = "none"
    padding: str = "none"

    def __post_init__(self) -> None:
        length, overlap = self.segment_length, self.noverlap
        if type(length) is not int or length < 2:
            raise ValueError("segment_length must be an integer >= 2")
        if type(overlap) is not int or not 0 <= overlap < length:
            raise ValueError("noverlap must be an integer from 0 to segment_length - 1")
        if self.nfft is not None and (type(self.nfft) is not int or self.nfft != length):
            raise ValueError("nfft must equal segment_length")
        object.__setattr__(self, "nfft", length)
        expected = {
            "taper": "hann_periodic",
            "detrend": False,
            "sidedness": "onesided",
            "scaling": "density",
            "average": "mean",
            "boundary": "none",
            "padding": "none",
        }
        for name, value in expected.items():
            if getattr(self, name) != value or type(getattr(self, name)) is not type(value):
                raise ValueError(f"unsupported {name}; expected {value!r}")

    def resolved(self) -> dict:
        return {
            "method_id": METHOD_ID,
            "segment_length": self.segment_length,
            "noverlap": self.noverlap,
            "hop": self.segment_length - self.noverlap,
            "nfft": self.nfft,
            "taper": self.taper,
            "taper_construction": "scipy.signal.windows.hann(L, sym=False)",
            "window_normalization": "U=sum(window**2)",
            "detrend": self.detrend,
            "global_mean_policy": "none",
            "sidedness": self.sidedness,
            "scaling": self.scaling,
            "average": self.average,
            "boundary": self.boundary,
            "padding": self.padding,
            "frame_policy": "all_complete_frames_from_zero",
            "integration": "sum(density[bin]) * sampling_rate_hz / nfft",
            "endpoint_rule": "lower_inclusive; internal_upper_exclusive; final_upper_inclusive",
        }


def measure_welch(
    record: SignalRecord, bands: tuple[Band, ...], settings: WelchSettings
) -> Measurement:
    if not isinstance(settings, WelchSettings):
        raise ValueError("settings must be WelchSettings")
    resolved_bands = validate_bands(tuple(bands), record.sampling_rate_hz)
    n = record.samples.size
    length = settings.segment_length
    if length > n:
        raise ValueError("segment_length exceeds record length")
    hop = length - settings.noverlap
    starts = tuple(range(0, n - length + 1, hop))
    window = hann(length, sym=False)
    u = float(np.dot(window, window))
    if u <= 0:
        raise ValueError("window squared energy must be positive")
    with np.errstate(over="raise", invalid="raise"):
        try:
            frequencies, density = welch(
                record.samples,
                fs=record.sampling_rate_hz,
                window=window,
                nperseg=length,
                noverlap=settings.noverlap,
                nfft=length,
                detrend=False,
                return_onesided=True,
                scaling="density",
                axis=-1,
                average="mean",
            )
            record_power = float(np.dot(record.samples, record.samples) / n)
            weighted = sum(
                float(
                    np.dot(
                        window * record.samples[s : s + length],
                        window * record.samples[s : s + length],
                    )
                )
                for s in starts
            )
            method_total = weighted / (len(starts) * u)
            spectral_total = float(np.sum(density) * record.sampling_rate_hz / length)
        except FloatingPointError as exc:
            raise ValueError("numerical range exceeded in Welch measurement") from exc
    if not all(np.isfinite(v) for v in (record_power, method_total, spectral_total)) or not np.all(
        np.isfinite(density)
    ):
        raise ValueError("numerical range exceeded in Welch measurement")
    if not np.isclose(spectral_total, method_total, rtol=1e-12, atol=1e-12 * method_total):
        raise ValueError("Welch spectral total disagrees with windowed time-domain identity")
    powers = []
    for band in resolved_bands:
        mask = frequencies >= band.lower_hz
        mask &= frequencies <= band.upper_hz if band.include_upper else frequencies < band.upper_hz
        if not np.any(mask):
            raise ValueError(f"band {band.name!r} contains no Welch estimator bins")
        powers.append(float(np.sum(density[mask]) * record.sampling_rate_hz / length))
    if not np.isclose(sum(powers), spectral_total, rtol=1e-12, atol=1e-12 * method_total):
        raise ValueError("Welch bins were not accounted for exactly once")
    record_reasons = tuple("zero_record_power" if record_power == 0 else None for _ in powers)
    method_reasons = tuple("zero_method_total_power" if method_total == 0 else None for _ in powers)
    covered = set(j for s in starts for j in range(s, s + length))
    zero_weight = sorted(
        j for j in covered if all(window[j - s] == 0 for s in starts if s <= j < s + length)
    )
    support = {
        "frame_starts": starts,
        "frame_count": len(starts),
        "frame_weights": [1 / len(starts)] * len(starts),
        "frame_weight_policy": "equal_arithmetic_1/K",
        "covered_sample_count": len(covered),
        "omitted_sample_indices": sorted(set(range(n)) - covered),
        "zero_taper_weight_sample_indices": zero_weight,
        "window_squared_energy": u,
        "frequency_bins_hz": frequencies.tolist(),
    }
    resolved = settings.resolved()
    record_id = sha256(np.asarray(record.samples, dtype="<f8", order="C").tobytes()).hexdigest()
    return Measurement(
        METHOD_ID,
        "finite_record_dft_v1",
        "finite_record_windowed_band_power",
        resolved_bands,
        tuple(powers),
        record_power,
        tuple(None if record_power == 0 else p / record_power for p in powers),
        "undefined" if record_power == 0 or method_total == 0 else "ok",
        record_reasons,
        measurement_kind=CONTRACT.measurement_kind,
        method_total_power=method_total,
        method_total_fractions=tuple(
            None if method_total == 0 else p / method_total for p in powers
        ),
        method_total_reasons=method_reasons,
        power_statuses=tuple("ok" for _ in powers),
        power_reasons=tuple(None for _ in powers),
        settings=resolved,
        settings_hash=sha256(
            json.dumps(
                resolved, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False
            ).encode("utf-8")
        ).hexdigest(),
        support=support,
        record_id=record_id,
        accounting_error=spectral_total - method_total,
        n_samples=n,
        sampling_rate_hz=record.sampling_rate_hz,
        sample_unit=record.sample_unit,
        power_unit=f"({record.sample_unit})^2",
        density_unit=f"({record.sample_unit})^2/Hz",
    )
