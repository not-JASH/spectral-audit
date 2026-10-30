"""Exact finite-record Fourier band measurement."""

from collections.abc import Sequence
from hashlib import sha256

import numpy as np

from spectral_audit.types import Band, Measurement, SignalRecord, validate_bands

METHOD_ID = "finite_record_dft_v1"


def fourier_reference(record: SignalRecord, bands: Sequence[Band]) -> Measurement:
    resolved = validate_bands(tuple(bands), record.sampling_rate_hz)
    n = record.samples.size
    frequencies = np.abs(np.fft.fftfreq(n, d=1 / record.sampling_rate_hz))
    try:
        with np.errstate(over="raise", invalid="raise"):
            coefficients = np.fft.fft(record.samples, norm="ortho")
            bin_power = np.abs(coefficients) ** 2 / n
            record_power = float(np.dot(record.samples, record.samples) / n)
    except FloatingPointError as exc:
        raise ValueError("numerical range exceeded while computing record or band power") from exc
    if not np.isfinite(record_power) or not np.all(np.isfinite(bin_power)):
        raise ValueError("numerical range exceeded while computing record or band power")
    powers = []
    membership = np.zeros(n, dtype=np.int8)
    for band in resolved:
        mask = frequencies >= band.lower_hz
        mask &= frequencies <= band.upper_hz if band.include_upper else frequencies < band.upper_hz
        membership += mask
        powers.append(float(np.sum(bin_power[mask])))
    if not np.all(membership == 1):
        raise ValueError("frequency bins were not assigned exactly once")
    if not np.isclose(sum(powers), record_power, rtol=1e-12, atol=1e-12 * record_power):
        raise ValueError("DFT band powers do not account for record power")
    zero = record_power == 0
    fractions = tuple(None if zero else power / record_power for power in powers)
    reasons = tuple("zero_reference_power" if zero else None for _ in powers)
    return Measurement(
        METHOD_ID,
        METHOD_ID,
        "finite_record_fourier",
        resolved,
        tuple(powers),
        record_power,
        fractions,
        "undefined" if zero else "ok",
        reasons,
        record_id=sha256(np.asarray(record.samples, dtype="<f8", order="C").tobytes()).hexdigest(),
        n_samples=n,
        sampling_rate_hz=record.sampling_rate_hz,
        sample_unit=record.sample_unit,
        power_unit=f"({record.sample_unit})^2",
    )
