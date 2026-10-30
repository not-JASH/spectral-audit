"""Deterministic analytical signal construction."""

import numpy as np

from spectral_audit.types import RecordConfig, SignalRecord, ToneSignalConfig


def make_tones(config: ToneSignalConfig, record: RecordConfig) -> SignalRecord:
    index = np.arange(record.n_samples, dtype=np.float64)
    samples = np.zeros(record.n_samples, dtype=np.float64)
    for frequency, amplitude, phase in zip(
        config.frequencies_hz, config.amplitudes, config.phases_rad, strict=True
    ):
        samples += amplitude * np.sin(
            2 * np.pi * frequency * index / record.sampling_rate_hz + phase
        )
    return SignalRecord(samples, record.sampling_rate_hz, record.sample_unit)
