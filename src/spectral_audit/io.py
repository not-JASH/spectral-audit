"""Deterministic run artifacts and truthful provenance."""

import csv
import hashlib
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

from spectral_audit import __version__
from spectral_audit.config import canonical_json_bytes, resolved_config
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
