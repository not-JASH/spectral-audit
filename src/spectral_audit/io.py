"""Deterministic run artifacts and truthful provenance."""

import csv
import hashlib
import importlib.metadata
import io
import json
import os
import platform
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

import numpy as np
import pywt
import scipy

from spectral_audit import __version__
from spectral_audit.comparisons import (
    ComparisonRequest,
    band_quantity,
    compare_quantities,
)
from spectral_audit.config import (
    MeasureConfig,
    canonical_json_bytes,
    resolved_config,
    resolved_measure_config,
)
from spectral_audit.estimators.dwt import NativeScaleResult
from spectral_audit.types import DemoConfig, Measurement, SignalRecord

CSV_COLUMNS = (
    "experiment_id",
    "method_id",
    "reference_id",
    "band",
    "lower_hz",
    "upper_hz",
    "include_upper",
    "band_power",
    "power_unit",
    "record_power",
    "record_power_fraction",
    "status",
    "reason",
)


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def json_bytes(value: object) -> bytes:
    return (
        json.dumps(value, sort_keys=True, indent=2, ensure_ascii=False, allow_nan=False) + "\n"
    ).encode("utf-8")


def _number(value: float | None) -> str:
    return "" if value is None else format(value, ".17g")


def _git(root: Path, *args: str) -> str | None:
    try:
        result = subprocess.run(
            ["git", "-C", str(root), *args], capture_output=True, text=True, check=False
        )
    except FileNotFoundError:
        return None
    return result.stdout.strip() if result.returncode == 0 else None


def _source_inventory(root: Path) -> tuple[list[dict], str]:
    files = sorted((root / "src" / "spectral_audit").rglob("*.py"))
    expected_modules = {
        "__init__.py",
        "__main__.py",
        "types.py",
        "config.py",
        "signals.py",
        "reference.py",
        "io.py",
        "cli.py",
    }
    missing = expected_modules - {path.name for path in files}
    if missing:
        raise FileNotFoundError(f"expected source modules missing: {sorted(missing)}")
    files += [root / "pyproject.toml", root / "requirements-lock.txt"]
    inventory = []
    for path in sorted(files, key=lambda p: p.relative_to(root).as_posix()):
        if not path.is_file():
            raise FileNotFoundError(f"expected source file missing: {path}")
        inventory.append(
            {"path": path.relative_to(root).as_posix(), "sha256": digest(path.read_bytes())}
        )
    return inventory, digest(canonical_json_bytes(inventory))


def _atomic_write(path: Path, data: bytes) -> None:
    descriptor, temporary = tempfile.mkstemp(prefix=".spectral-audit-", dir=path.parent)
    try:
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


@dataclass(frozen=True)
class RunPaths:
    csv: Path
    summary: Path
    manifest: Path
    native_scales: Path | None = None


def write_demo_run(
    out: Path,
    config: DemoConfig,
    record: SignalRecord,
    measurement: Measurement,
    config_path: Path,
    root: Path,
    started_at: datetime,
    elapsed_seconds: float,
    command_arguments: list[str],
) -> RunPaths:
    if out.exists() and (not out.is_dir() or any(out.iterdir())):
        raise ValueError(f"output directory already exists and is nonempty: {out}")
    out.mkdir(parents=True, exist_ok=True)
    rows = io.StringIO(newline="")
    writer = csv.writer(rows, lineterminator="\n")
    writer.writerow(CSV_COLUMNS)
    power_unit = f"({record.sample_unit})^2"
    summary_bands = []
    for band, power, fraction, reason in zip(
        measurement.bands,
        measurement.powers,
        measurement.fractions,
        measurement.reasons,
        strict=True,
    ):
        status = "undefined" if reason else "ok"
        writer.writerow(
            (
                config.experiment_id,
                measurement.method_id,
                measurement.reference_id,
                band.name,
                _number(band.lower_hz),
                _number(band.upper_hz),
                str(band.include_upper).lower(),
                _number(power),
                power_unit,
                _number(measurement.record_power),
                _number(fraction),
                status,
                reason or "",
            )
        )
        summary_bands.append(
            {
                "name": band.name,
                "lower_hz": band.lower_hz,
                "upper_hz": band.upper_hz,
                "include_upper": band.include_upper,
                "band_power": power,
                "record_power_fraction": fraction,
                "status": status,
                "reason": reason,
            }
        )
    summary = {
        "schema_version": 1,
        "experiment_id": config.experiment_id,
        "method_id": measurement.method_id,
        "reference_id": measurement.reference_id,
        "target_id": measurement.target_id,
        "n_samples": record.samples.size,
        "sampling_rate_hz": record.sampling_rate_hz,
        "sample_unit": record.sample_unit,
        "power_unit": power_unit,
        "mean_policy": config.record.mean_policy,
        "record_power": measurement.record_power,
        "sum_band_power": measurement.method_total,
        "power_accounting_error": measurement.method_total - measurement.record_power,
        "bands": summary_bands,
        "status": measurement.status,
    }
    csv_data = rows.getvalue().encode("utf-8")
    summary_data = json_bytes(summary)
    resolved = resolved_config(config)
    inventory, source_digest = _source_inventory(root)
    revision = _git(root, "rev-parse", "HEAD")
    git_root = _git(root, "rev-parse", "--show-toplevel")
    git_status = _git(root, "status", "--porcelain")
    if (
        revision is None
        or git_root is None
        or git_status is None
        or Path(git_root).resolve() != root.resolve()
    ):
        state = "unversioned"
    else:
        state = "dirty" if git_status else "clean"
    samples = np.asarray(record.samples, dtype="<f8", order="C")
    manifest = {
        "schema_version": 1,
        "package_version": __version__,
        "run_status": "complete",
        "resolved_configuration": resolved,
        "resolved_configuration_sha256": digest(canonical_json_bytes(resolved)),
        "source_config_sha256": digest(config_path.read_bytes()),
        "signal": {
            "sha256": digest(samples.tobytes(order="C")),
            "dtype": "float64",
            "byte_order": "little",
            "shape": [record.samples.size],
            "order": "C",
        },
        "python_version": platform.python_version(),
        "numpy_version": np.__version__,
        "platform": platform.platform(),
        "source_revision": revision if state != "unversioned" else None,
        "source_state": state,
        "source_files": inventory,
        "source_digest": source_digest,
        "measurement": {
            "method_id": measurement.method_id,
            "target_id": measurement.target_id,
            "fft_norm": "ortho",
            "bin_selection": "absolute_physical_frequency",
            "mean_policy": "none",
            "denominator": "actual_record_mean_square",
            "endpoint_rule": "lower_inclusive; internal_upper_exclusive; final_upper_inclusive",
            "boundary_policy": "finite_record_periodic_dft",
        },
        "outputs": {"band_powers.csv": digest(csv_data), "summary.json": digest(summary_data)},
        "invocation": {
            "started_at_utc": started_at.astimezone(UTC).isoformat(),
            "elapsed_seconds": elapsed_seconds,
            "arguments": command_arguments,
            "output_directory": str(out.resolve()),
            "executable": sys.executable,
        },
    }
    paths = RunPaths(out / "band_powers.csv", out / "summary.json", out / "manifest.json")
    _atomic_write(paths.csv, csv_data)
    _atomic_write(paths.summary, summary_data)
    _atomic_write(paths.manifest, json_bytes(manifest))
    return paths


MEASURE_COLUMNS = (
    "case_id",
    "record_id",
    "method_id",
    "measurement_kind",
    "population_target_kind",
    "settings_hash",
    "band",
    "lower_hz",
    "upper_hz",
    "include_upper",
    "band_power",
    "power_unit",
    "power_status",
    "power_reason",
    "record_power",
    "record_power_status",
    "record_power_reason",
    "method_total_power",
    "method_total_status",
    "method_total_reason",
    "method_total_minus_record_power",
    "method_total_minus_record_power_status",
    "method_total_minus_record_power_reason",
    "record_power_fraction",
    "record_fraction_status",
    "record_fraction_reason",
    "method_total_fraction",
    "method_fraction_status",
    "method_fraction_reason",
    "comparison_reference_id",
    "difference_from_dft",
    "difference_status",
    "difference_reason",
    "comparison_status",
    "comparison_reason",
)

NATIVE_COLUMNS = (
    "case_id", "record_id", "method_id", "measurement_kind", "support_kind",
    "settings_hash", "group", "coefficient_count", "nominal_lower_hz",
    "nominal_upper_hz", "record_power_quantity_id", "record_power_contribution",
    "record_contribution_status", "record_contribution_reason",
    "coefficient_mean_square_quantity_id", "coefficient_mean_square",
    "coefficient_mean_square_status", "coefficient_mean_square_reason",
    "power_unit", "absolute_status", "absolute_reason", "record_power",
    "method_total_power", "record_fraction_denominator_id", "record_power_fraction",
    "record_fraction_status",
    "record_fraction_reason", "method_total_fraction", "method_fraction_status",
    "method_fraction_reason", "method_fraction_denominator_id", "difference_from_dft",
    "difference_status",
    "difference_reason",
)


def write_measure_run(
    out: Path,
    config: MeasureConfig,
    record: SignalRecord,
    reference: Measurement,
    estimate: Measurement,
    config_path: Path,
    root: Path,
    started_at: datetime,
    elapsed_seconds: float,
    command_arguments: list[str],
    native: NativeScaleResult | None = None,
) -> RunPaths:
    if out.exists() and (not out.is_dir() or any(out.iterdir())):
        raise ValueError(f"output directory already exists and is nonempty: {out}")
    if len(reference.bands) != len(estimate.bands):
        raise ValueError("comparison requires matching band collections")
    if reference.record_power != estimate.record_power:
        raise ValueError("comparison record-power metadata disagree")
    sample_bytes = np.asarray(record.samples, dtype="<f8", order="C").tobytes(order="C")
    record_id = digest(sample_bytes)
    if reference.record_id != record_id or estimate.record_id != record_id:
        raise ValueError("comparison measurements do not match the input record")
    for measurement in (reference, estimate):
        if (
            measurement.n_samples != record.samples.size
            or measurement.sampling_rate_hz != record.sampling_rate_hz
            or measurement.sample_unit != record.sample_unit
            or measurement.preprocessing != "none"
        ):
            raise ValueError("comparison measurements do not match the shared record")
    if (config.dwt is None) != (native is None):
        raise ValueError("DWT configuration and native result must occur together")
    if native is not None and (
        native.record_id != record_id
        or native.n_samples != record.samples.size
        or native.sampling_rate_hz != record.sampling_rate_hz
        or native.sample_unit != record.sample_unit
        or native.preprocessing != "none"
        or native.record_power != reference.record_power
    ):
        raise ValueError("native measurement does not match the shared record")
    reference_by_support = {
        (b.lower_hz, b.upper_hz, b.include_upper): i
        for i, b in enumerate(reference.bands)
    }
    comparisons = {}
    for i, band in enumerate(estimate.bands):
        key = (band.lower_hz, band.upper_hz, band.include_upper)
        if key not in reference_by_support:
            raise ValueError("comparison requires matching Fourier band support")
        j = reference_by_support[key]
        comparisons[key] = compare_quantities(
            band_quantity(reference, j), band_quantity(estimate, i),
            ComparisonRequest("descriptive_difference"),
        )
        if comparisons[key].decision != "accepted":
            raise ValueError(f"comparison policy: {comparisons[key].reason}")
    out.mkdir(parents=True, exist_ok=True)
    resolved = resolved_measure_config(config)
    dft_settings = {
        "method_id": reference.method_id,
        "fft_norm": "ortho",
        "preprocessing": "none",
        "support": "full_finite_record",
        "bin_selection": "absolute_physical_frequency",
        "endpoint_rule": "lower_inclusive; internal_upper_exclusive; final_upper_inclusive",
        "normalization": "unitary_dft_squared_magnitude_divided_by_n",
    }
    dft_hash = digest(canonical_json_bytes(dft_settings))
    rows = io.StringIO(newline="")
    writer = csv.writer(rows, lineterminator="\n")
    writer.writerow(MEASURE_COLUMNS)
    power_unit = f"({record.sample_unit})^2"
    summary_methods = []
    for measurement, settings, settings_hash, is_candidate in (
        (reference, dft_settings, dft_hash, False),
        (estimate, estimate.settings, estimate.settings_hash, True),
    ):
        method_bands = []
        for i, band in enumerate(measurement.bands):
            power = measurement.powers[i]
            record_fraction = measurement.fractions[i]
            record_reason = measurement.reasons[i]
            method_fraction = (
                measurement.method_total_fractions[i]
                if measurement.method_total_fractions
                else None
                if measurement.method_total == 0
                else power / measurement.method_total
            )
            method_reason = (
                measurement.method_total_reasons[i]
                if measurement.method_total_reasons
                else "zero_method_total_power"
                if measurement.method_total == 0
                else None
            )
            power_status = measurement.power_statuses[i] if measurement.power_statuses else "ok"
            power_reason = measurement.power_reasons[i] if measurement.power_reasons else None
            key = (band.lower_hz, band.upper_hz, band.include_upper)
            comparison = comparisons[key] if is_candidate else compare_quantities(
                band_quantity(reference, reference_by_support[key]),
                band_quantity(reference, reference_by_support[key]),
                ComparisonRequest("exact_target"),
            )
            if comparison.decision != "accepted":
                raise ValueError(f"comparison policy: {comparison.reason}")
            difference = comparison.signed_difference
            writer.writerow(
                (
                    config.tones.experiment_id,
                    record_id,
                    measurement.method_id,
                    measurement.measurement_kind,
                    measurement.population_target_kind or "",
                    settings_hash,
                    band.name,
                    _number(band.lower_hz),
                    _number(band.upper_hz),
                    str(band.include_upper).lower(),
                    _number(power),
                    power_unit,
                    power_status,
                    power_reason or "",
                    _number(measurement.record_power),
                    "ok",
                    "",
                    _number(measurement.method_total),
                    "ok",
                    "",
                    _number(measurement.method_total - measurement.record_power),
                    "ok",
                    "",
                    _number(record_fraction),
                    "undefined" if record_reason else "ok",
                    record_reason or "",
                    _number(method_fraction),
                    "undefined" if method_reason else "ok",
                    method_reason or "",
                    reference.method_id,
                    _number(difference),
                    "ok",
                    "",
                    "descriptive",
                    "different_finite_record_functionals"
                    if comparison.relation == "different_functionals" else "same_method",
                )
            )
            method_bands.append(
                {
                    "name": band.name,
                    "lower_hz": band.lower_hz,
                    "upper_hz": band.upper_hz,
                    "include_upper": band.include_upper,
                    "band_power": power,
                    "power_status": power_status,
                    "power_reason": power_reason,
                    "record_power_fraction": record_fraction,
                    "record_fraction_status": "undefined" if record_reason else "ok",
                    "record_fraction_reason": record_reason,
                    "method_total_fraction": method_fraction,
                    "method_fraction_status": "undefined" if method_reason else "ok",
                    "method_fraction_reason": method_reason,
                    "difference_from_dft": difference,
                    "difference_status": "ok",
                    "difference_reason": None,
                }
            )
        summary_methods.append(
            {
                "method_id": measurement.method_id,
                "measurement_kind": measurement.measurement_kind,
                "population_target_kind": measurement.population_target_kind,
                "settings": settings,
                "settings_hash": settings_hash,
                "support": measurement.support
                or {
                    "sample_indices": [0, record.samples.size - 1],
                    "sample_count": record.samples.size,
                },
                "record_power": measurement.record_power,
                "record_power_status": "ok",
                "record_power_reason": None,
                "method_total_power": measurement.method_total,
                "method_total_status": "ok",
                "method_total_reason": None,
                "method_total_minus_record_power": measurement.method_total
                - measurement.record_power,
                "method_total_minus_record_power_status": "ok",
                "method_total_minus_record_power_reason": None,
                "accounting_error": measurement.accounting_error
                if measurement.accounting_error is not None
                else measurement.method_total - measurement.record_power,
                "accounting_error_status": "ok",
                "accounting_error_reason": None,
                "bands": method_bands,
            }
        )
    csv_data = rows.getvalue().encode("utf-8")
    native_data = None
    if native is not None:
        native_rows = io.StringIO(newline="")
        native_writer = csv.writer(native_rows, lineterminator="\n")
        native_writer.writerow(NATIVE_COLUMNS)
        group_summaries = []
        for i, group in enumerate(native.groups):
            record_reason = native.record_fraction_reasons[i]
            method_reason = native.method_fraction_reasons[i]
            native_writer.writerow((
                config.tones.experiment_id, record_id, native.method_id,
                "native_scale_record_power", group.support_kind, native.settings_hash,
                group.name, group.coefficient_count, _number(group.nominal_lower_hz),
                _number(group.nominal_upper_hz), "native_scale_record_power",
                _number(group.record_power_contribution), "ok", "",
                "native_scale_coefficient_mean_square", _number(group.coefficient_mean_square),
                "ok", "",
                native.power_unit, "ok", "", _number(native.record_power),
                _number(native.method_total_power), "actual_record_mean_square",
                _number(native.record_power_fractions[i]),
                "undefined" if record_reason else "ok", record_reason or "",
                _number(native.method_total_fractions[i]),
                "undefined" if method_reason else "ok", method_reason or "",
                "sum_native_record_power_contributions", "", "unavailable",
                "native_scale_not_exact_fourier_band",
            ))
            group_summaries.append({
                "name": group.name,
                "support_kind": group.support_kind,
                "coefficient_count": group.coefficient_count,
                "nominal_lower_hz": group.nominal_lower_hz,
                "nominal_upper_hz": group.nominal_upper_hz,
                "record_power_quantity_id": "native_scale_record_power",
                "record_power_contribution": group.record_power_contribution,
                "record_contribution_status": "ok",
                "record_contribution_reason": None,
                "coefficient_mean_square_quantity_id": "native_scale_coefficient_mean_square",
                "coefficient_mean_square": group.coefficient_mean_square,
                "coefficient_mean_square_status": "ok",
                "coefficient_mean_square_reason": None,
                "sum_squared_coefficients": group.sum_squared_coefficients,
                "power_unit": native.power_unit,
                "absolute_status": "ok", "absolute_reason": None,
                "record_power_fraction": native.record_power_fractions[i],
                "record_fraction_denominator_id": "actual_record_mean_square",
                "record_fraction_status": "undefined" if record_reason else "ok",
                "record_fraction_reason": record_reason,
                "method_total_fraction": native.method_total_fractions[i],
                "method_fraction_denominator_id": "sum_native_record_power_contributions",
                "method_fraction_status": "undefined" if method_reason else "ok",
                "method_fraction_reason": method_reason,
                "difference_from_dft": None,
                "difference_status": "unavailable",
                "difference_reason": "native_scale_not_exact_fourier_band",
            })
        native_data = native_rows.getvalue().encode("utf-8")
        summary_methods.append({
            "method_id": native.method_id,
            "measurement_kind": "native_scale_record_power",
            "population_target_kind": None,
            "settings": native.settings,
            "settings_hash": native.settings_hash,
            "support": {"kind": "native_scale_group", "sample_indices": [0, native.n_samples - 1],
                        "input_length": native.n_samples,
                        "effective_extended_length": native.n_samples,
                        "wavelet": native.settings["wavelet"],
                        "level": native.settings["level"],
                        "mode": native.settings["mode"],
                        "group_coefficient_counts": {
                            group.name: group.coefficient_count for group in native.groups
                        },
                        "coefficient_count": native.n_samples,
                        "retained_coefficient_policy": "all_coefficients"},
            "record_power": native.record_power,
            "record_power_status": "ok", "record_power_reason": None,
            "method_total_power": native.method_total_power,
            "method_total_status": "ok", "method_total_reason": None,
            "accounting_error": native.method_total_power - native.record_power,
            "accounting_error_status": "ok", "accounting_error_reason": None,
            "power_unit": native.power_unit,
            "preprocessing": native.preprocessing,
            "groups": group_summaries,
        })
    summary = {
            "schema_version": 3 if native is not None else 2,
            "case_id": config.tones.experiment_id,
            "record_id": record_id,
            "n_samples": record.samples.size,
            "sampling_rate_hz": record.sampling_rate_hz,
            "sample_unit": record.sample_unit,
            "power_unit": power_unit,
            "density_unit": f"({record.sample_unit})^2/Hz" if native is None else None,
            "preprocessing": "none",
            "comparison_reference_id": reference.method_id,
            "comparison_status": "descriptive",
            "comparison_reason": "different_finite_record_functionals",
            "methods": summary_methods,
        }
    if native is not None:
        summary["density_unit"] = None
        summary["methods"][1]["density_unit"] = f"({record.sample_unit})^2/Hz"
        summary["methods"][0]["power_unit"] = power_unit
        summary["methods"][1]["power_unit"] = power_unit
        summary["comparison_scope"] = "DFT_and_Welch_exact_frequency_bands_only"
    summary_data = json_bytes(summary)
    inventory, source_digest = _source_inventory(root)
    revision = _git(root, "rev-parse", "HEAD")
    git_root = _git(root, "rev-parse", "--show-toplevel")
    git_status = _git(root, "status", "--porcelain")
    state = (
        "unversioned"
        if revision is None
        or git_root is None
        or git_status is None
        or Path(git_root).resolve() != root.resolve()
        else "dirty"
        if git_status
        else "clean"
    )
    manifest = {
        "schema_version": 3 if native is not None else 2,
        "package_version": __version__,
        "run_status": "complete",
        "resolved_configuration": resolved,
        "resolved_configuration_sha256": digest(canonical_json_bytes(resolved)),
        "source_config_sha256": digest(config_path.read_bytes()),
        "signal": {
            "sha256": record_id,
            "dtype": "float64",
            "byte_order": "little",
            "shape": [record.samples.size],
            "order": "C",
        },
        "python_version": platform.python_version(),
        "numpy_version": np.__version__,
        "scipy_version": scipy.__version__,
        "platform": platform.platform(),
        "source_revision": revision if state != "unversioned" else None,
        "source_state": state,
        "source_files": inventory,
        "source_digest": source_digest,
        "outputs": {"comparisons.csv": digest(csv_data), "summary.json": digest(summary_data)},
        "invocation": {
            "started_at_utc": started_at.astimezone(UTC).isoformat(),
            "elapsed_seconds": elapsed_seconds,
            "arguments": command_arguments,
            "output_directory": str(out.resolve()),
            "executable": sys.executable,
        },
    }
    if native_data is not None:
        manifest["pywavelets_version"] = pywt.__version__
        manifest["pywavelets_distribution_version"] = importlib.metadata.version("PyWavelets")
        manifest["outputs"]["native_scales.csv"] = digest(native_data)
    paths = RunPaths(
        out / "comparisons.csv", out / "summary.json", out / "manifest.json",
        out / "native_scales.csv" if native_data is not None else None,
    )
    _atomic_write(paths.csv, csv_data)
    if native_data is not None:
        _atomic_write(paths.native_scales, native_data)
    _atomic_write(paths.summary, summary_data)
    _atomic_write(paths.manifest, json_bytes(manifest))
    return paths
