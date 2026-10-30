import numpy as np
import pytest

from spectral_audit.config import load_demo_config
from spectral_audit.reference import fourier_reference
from spectral_audit.signals import make_tones
from spectral_audit.types import Band, SignalRecord

ATOL = 1e-12
RTOL = 1e-12


def oracle_rfft(samples, fs, bands):
    """Independent one-sided route; no production masks or normalization helpers."""
    n = len(samples)
    spectrum = np.fft.rfft(samples, norm="ortho")
    frequencies = np.arange(len(spectrum)) * fs / n
    contributions = np.abs(spectrum) ** 2 / n
    for k in range(1, len(spectrum) - (1 if n % 2 == 0 else 0)):
        contributions[k] *= 2
    selected = []
    for lo, hi, last in bands:
        selected.append(
            sum(
                p
                for f, p in zip(frequencies, contributions, strict=True)
                if lo <= f <= hi and (last or f < hi)
            )
        )
    return np.array(selected), sum(contributions)


def test_analytic_demo_and_scaled_inputs():
    config = load_demo_config(__import__("pathlib").Path("configs/m0_tones.toml"))
    samples = make_tones(config.signal, config.record).samples
    for scale in (1, 1e-6, 1e6):
        record = SignalRecord(samples * scale, 128, "a.u.")
        result = fourier_reference(record, config.bands)
        expected = np.array([0.5, 0.125, 0]) * scale**2
        np.testing.assert_allclose(result.powers, expected, rtol=RTOL, atol=ATOL * scale**2)
        np.testing.assert_allclose(result.fractions, [0.8, 0.2, 0], rtol=RTOL, atol=ATOL)
        assert result.record_power == pytest.approx(sum(record.samples**2) / 256, rel=RTOL)
        one_sided, total = oracle_rfft(
            record.samples, 128, [(0, 16, False), (16, 32, False), (32, 64, True)]
        )
        np.testing.assert_allclose(result.powers, one_sided, rtol=RTOL, atol=ATOL * scale**2)
        assert total == pytest.approx(result.record_power, rel=RTOL)


@pytest.mark.parametrize("n", [8, 9])
def test_explicit_dft_and_endpoint_multiplicity(n):
    fs = 8.0
    index = np.arange(n)
    samples = (
        1 + 0.75 * np.cos(2 * np.pi * index / n) + 0.25 * np.cos(2 * np.pi * (n // 2) * index / n)
    )
    record = SignalRecord(samples, fs, "V")
    bands = (
        Band("dc", 0, fs / n),
        Band("interior", fs / n, 3 * fs / n),
        Band("upper", 3 * fs / n, fs / 2, True),
    )
    result = fourier_reference(record, bands)
    matrix = np.exp(-2j * np.pi * np.outer(index, index) / n) / np.sqrt(n)
    explicit = matrix @ samples
    np.testing.assert_allclose(explicit, np.fft.fft(samples, norm="ortho"), rtol=RTOL, atol=ATOL)
    frequencies = np.abs(np.where(index <= n // 2, index, index - n) * fs / n)
    expected = [
        sum(
            abs(explicit[k]) ** 2 / n
            for k, f in enumerate(frequencies)
            if lo <= f and (f < hi or last and f <= hi)
        )
        for lo, hi, last in [
            (0, fs / n, False),
            (fs / n, 3 * fs / n, False),
            (3 * fs / n, fs / 2, True),
        ]
    ]
    np.testing.assert_allclose(result.powers, expected, rtol=RTOL, atol=ATOL)
    one_sided, total = oracle_rfft(
        samples, fs, [(0, fs / n, False), (fs / n, 3 * fs / n, False), (3 * fs / n, fs / 2, True)]
    )
    np.testing.assert_allclose(result.powers, one_sided, rtol=RTOL, atol=ATOL)
    assert total == pytest.approx(sum(samples**2) / n, rel=RTOL)


def test_dc_nyquist_exact_internal_edges_and_zero():
    n = 256
    j = np.arange(n)
    bands = (Band("low", 0, 16), Band("mid", 16, 32), Band("high", 32, 64, True))
    for samples, expected in [
        (np.ones(n), [1, 0, 0]),
        ((-1.0) ** j, [0, 0, 1]),
        (np.cos(2 * np.pi * 16 * j / 128), [0, 0.5, 0]),
        (np.cos(2 * np.pi * 32 * j / 128), [0, 0, 0.5]),
    ]:
        result = fourier_reference(SignalRecord(samples, 128, "V"), bands)
        np.testing.assert_allclose(result.powers, expected, rtol=RTOL, atol=ATOL)
    zero = fourier_reference(SignalRecord(np.zeros(n), 128, "V"), bands)
    assert zero.powers == (0, 0, 0)
    assert zero.fractions == (None, None, None)
    assert zero.reasons == ("zero_reference_power",) * 3
    assert zero.status == "undefined"


@pytest.mark.parametrize("samples", [[], [1], [[1, 2], [3, 4]], [1, float("nan")], [1, 1j]])
def test_invalid_samples(samples):
    with pytest.raises(ValueError):
        SignalRecord(samples, 128, "V")


def test_overflow_rejected():
    with pytest.raises(ValueError, match="numerical range"):
        fourier_reference(SignalRecord([1e308, 1e308], 128, "V"), (Band("all", 0, 64, True),))
