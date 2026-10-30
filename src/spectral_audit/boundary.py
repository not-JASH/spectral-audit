"""Bounded two-level db4 finite-record boundary measurements."""

import hashlib
import json
from dataclasses import dataclass

import numpy as np
import pywt

from spectral_audit.boundary_reference import DB4_HIGH, DB4_LOW, decompose
from spectral_audit.types import SignalRecord

GROUPS = ("A2", "D2", "D1")


@dataclass(frozen=True)
class BoundarySettings:
    wavelet: str
    level: int
    mode: str

    def __post_init__(self):
        if self.wavelet != "db4" or type(self.wavelet) is not str:
            raise ValueError("boundary wavelet must be db4")
        if type(self.level) is not int or self.level != 2:
            raise ValueError("boundary level must be integer 2")
        if type(self.mode) is not str or self.mode not in {"periodic", "periodization"}:
            raise ValueError("boundary mode must be periodic or periodization")

    @property
    def method_id(self):
        return f"dwt_db4_{self.mode}_level2_v1"

    def resolved(self):
        wavelet = pywt.Wavelet("db4")
        actual = tuple(float(v) for v in wavelet.dec_lo)
        high = tuple(float(v) for v in wavelet.dec_hi)
        if not (
            np.allclose(actual, DB4_LOW, rtol=0, atol=1e-14)
            and np.allclose(high, DB4_HIGH, rtol=0, atol=1e-14)
        ):
            raise ValueError("runtime db4 filter bank disagrees with checked-in v1.9.0 taps")
        filter_bytes = np.asarray((actual, high), dtype="<f8").tobytes()
        return {
            "method_id": self.method_id,
            "wavelet": "db4",
            "level": 2,
            "mode": self.mode,
            "preprocessing": "none",
            "retained_coefficient_policy": "all",
            "coefficient_order": list(GROUPS),
            "decomposition_low_pass": list(actual),
            "decomposition_high_pass": list(high),
            "decomposition_filter_sha256": hashlib.sha256(filter_bytes).hexdigest(),
            "filter_source": "PyWavelets v1.9.0 wavelets_coeffs.template.h and wavelets.c",
        }


def evaluate(record: SignalRecord, settings: BoundarySettings) -> dict:
    if not isinstance(record, SignalRecord) or not isinstance(settings, BoundarySettings):
        raise ValueError("boundary evaluation requires SignalRecord and BoundarySettings")
    n = len(record.samples)
    if n < 28:
        raise ValueError("db4 two-level record requires at least 28 samples")
    resolved = settings.resolved()
    x = record.samples
    try:
        with np.errstate(over="raise", invalid="raise"):
            coefficients = pywt.wavedec(x.copy(), "db4", mode=settings.mode, level=2)
            reference, a1, ledger, flags = decompose(x, settings.mode)
            energies = [float(np.dot(c, c)) for c in coefficients]
            reference_energies = [float(np.dot(c, c)) for c in reference]
            original_energy = float(np.dot(x, x))
            method_total = sum(energies) / n
            if settings.mode == "periodization":
                reference_total = (
                    original_energy
                    + (float(x[-1] ** 2) if n % 2 else 0.0)
                    + (float(a1[-1] ** 2) if len(a1) % 2 else 0.0)
                ) / n
                reference_kind = "periodization_recursive_endpoint_identity"
            else:
                reference_total = sum(reference_energies) / n
                reference_kind = "explicit_finite_filter_bank"
    except (FloatingPointError, OverflowError) as exc:
        raise ValueError("numerical range exceeded in boundary measurement") from exc
    if not all(
        np.isfinite(v)
        for v in (*energies, *reference_energies, original_energy, method_total, reference_total)
    ):
        raise ValueError("numerical range exceeded in boundary measurement")
    scale = max(original_energy, sum(reference_energies), 1e-300)
    for actual, expected in zip(coefficients, reference, strict=True):
        if len(actual) != len(expected) or not np.allclose(
            actual, expected, rtol=1e-12, atol=1e-12 * np.sqrt(scale)
        ):
            raise ValueError("signed db4 coefficients disagree with direct reference")
    if not np.isclose(method_total, reference_total, rtol=1e-12, atol=1e-12 * scale / n):
        raise ValueError("boundary energy accounting disagrees with independent reference")
    reconstructed = pywt.waverec(coefficients, "db4", mode=settings.mode)
    if len(reconstructed) < n or not np.allclose(
        reconstructed[:n], x, rtol=1e-12, atol=1e-12 * np.sqrt(scale)
    ):
        raise ValueError("boundary reconstruction disagrees over original record")
    record_power = original_energy / n
    groups = []
    for name, coeff, energy, dependency in zip(GROUPS, coefficients, energies, flags, strict=True):
        contribution = energy / n
        groups.append(
            {
                "name": name,
                "coefficient_count": len(coeff),
                "sum_squared_coefficients": energy,
                "record_normalized_coefficient_energy": contribution,
                "coefficient_mean_square": energy / len(coeff),
                "record_power_ratio": contribution / record_power if record_power else None,
                "record_power_ratio_reason": None if record_power else "zero_record_power",
                "method_total_share": contribution / method_total if method_total else None,
                "method_total_share_reason": None if method_total else "zero_method_total_power",
                "structural_extension_dependency_count": sum(dependency),
                "nominal_frequency_hz": {
                    "A2": [0, record.sampling_rate_hz / 8],
                    "D2": [record.sampling_rate_hz / 8, record.sampling_rate_hz / 4],
                    "D1": [record.sampling_rate_hz / 4, record.sampling_rate_hz / 2],
                }[name],
            }
        )
    record_id = hashlib.sha256(np.asarray(x, dtype="<f8").tobytes()).hexdigest()
    return {
        "method_id": settings.method_id,
        "settings": resolved,
        "settings_hash": hashlib.sha256(
            json.dumps(resolved, sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest(),
        "record_id": record_id,
        "n_samples": n,
        "sampling_rate_hz": record.sampling_rate_hz,
        "sample_unit": record.sample_unit,
        "power_unit": f"({record.sample_unit})^2",
        "record_power": record_power,
        "method_total_power": method_total,
        "signed_method_total_minus_record_power": method_total - record_power,
        "accounting_reference_kind": reference_kind,
        "accounting_reference_power": reference_total,
        "accounting_residual": method_total - reference_total,
        "periodization_original_endpoint_correction": float(x[-1] ** 2) / n
        if settings.mode == "periodization" and n % 2
        else 0.0,
        "periodization_approximation_endpoint_correction": float(a1[-1] ** 2) / n
        if settings.mode == "periodization" and len(a1) % 2
        else 0.0,
        "extension_ledger": ledger,
        "reconstruction_length": len(reconstructed),
        "reconstruction_extra_samples": reconstructed[n:].tolist(),
        "reconstruction_max_abs_error": float(np.max(np.abs(reconstructed[:n] - x))),
        "groups": groups,
    }
