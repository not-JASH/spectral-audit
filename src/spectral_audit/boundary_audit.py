"""Fixed, reproducible M1 db4 boundary comparison; no Welch dependency in the path."""

import csv
import importlib.metadata
import io
import json
import platform
import sys
import tomllib
from datetime import UTC, datetime
from pathlib import Path
from time import perf_counter

import numpy as np
import pywt

from spectral_audit import __version__
from spectral_audit.boundary import BoundarySettings, evaluate
from spectral_audit.boundary_reference import DB4_HIGH, DB4_LOW, decompose
from spectral_audit.io import _atomic_write, _git, _number, _source_inventory, digest, json_bytes
from spectral_audit.types import SignalRecord


def load_config(path: Path) -> dict:
    with path.open("rb") as stream:
        data = tomllib.load(stream)
    if set(data) != {"config_kind", "schema_version", "audit"}:
        raise ValueError("boundary audit requires exactly config_kind, schema_version, audit")
    if (
        data["config_kind"] != "dwt_boundary_audit"
        or type(data["schema_version"]) is not int
        or data["schema_version"] != 1
    ):
        raise ValueError("unsupported boundary audit kind or schema version")
    audit = data["audit"]
    if not isinstance(audit, dict) or set(audit) != {
        "sampling_rate_hz",
        "sample_unit",
        "lengths",
        "modes",
        "response_length",
    }:
        raise ValueError("invalid boundary audit settings")
    fs = audit["sampling_rate_hz"]
    if type(fs) not in (float, int) or not np.isfinite(fs) or fs <= 0:
        raise ValueError("sampling_rate_hz must be finite and positive")
    if not isinstance(audit["sample_unit"], str) or not audit["sample_unit"].strip():
        raise ValueError("sample_unit must be nonempty")
    if audit["lengths"] != [30, 31, 32] or audit["modes"] != ["periodization", "periodic"]:
        raise ValueError("this bounded audit requires lengths 30,31,32 and both declared modes")
    if type(audit["response_length"]) is not int or audit["response_length"] != 64:
        raise ValueError("this bounded audit requires 64-sample response panel")
    return data


def cases(n: int):
    index = np.arange(n)
    return (
        ("ones", np.ones(n), "x[j]=1"),
        ("impulse_first", np.eye(1, n, 0)[0], "x[0]=1; other samples=0"),
        ("impulse_middle", np.eye(1, n, n // 2)[0], "x[floor(n/2)]=1; other samples=0"),
        ("impulse_final", np.eye(1, n, n - 1)[0], "x[n-1]=1; other samples=0"),
        ("ramp", index / (n - 1), "x[j]=j/(n-1)"),
        ("mixed_sign", (-1.0) ** index * (index + 1) / n, "x[j]=(-1)^j*(j+1)/n"),
    )


def _csv_bytes(fields: list[str], rows: list[dict]) -> bytes:
    stream = io.StringIO(newline="")
    writer = csv.DictWriter(stream, fieldnames=fields, lineterminator="\n")
    writer.writeheader()
    for row in rows:
        writer.writerow(
            {
                key: _number(value) if isinstance(value, float) else "" if value is None else value
                for key, value in row.items()
            }
        )
    return stream.getvalue().encode("utf-8")


def _response_reference(omega: float, mode: str, cosine: np.ndarray, sine: np.ndarray, n: int):
    if mode == "periodic":
        c = decompose(cosine, mode)[0]
        s = decompose(sine, mode)[0]
        return [
            float((np.dot(a, a) + np.dot(b, b)) / n) for a, b in zip(c, s, strict=True)
        ], "explicit_finite_filter_bank"
    h = sum(tap * np.exp(-1j * omega * j) for j, tap in enumerate(DB4_LOW))
    g = sum(tap * np.exp(-1j * omega * j) for j, tap in enumerate(DB4_HIGH))
    h2 = sum(tap * np.exp(-2j * omega * j) for j, tap in enumerate(DB4_LOW))
    g2 = sum(tap * np.exp(-2j * omega * j) for j, tap in enumerate(DB4_HIGH))
    return [
        float(abs(h * h2) ** 2 / 4),
        float(abs(h * g2) ** 2 / 4),
        float(abs(g) ** 2 / 2),
    ], "circular_filter_response"


def run(config_path: Path, out: Path, root: Path) -> dict:
    if out.exists() and (not out.is_dir() or any(out.iterdir())):
        raise ValueError(f"output directory already exists and is nonempty: {out}")
    started = datetime.now(UTC)
    clock = perf_counter()
    config = load_config(config_path)
    audit = config["audit"]
    fs, unit = audit["sampling_rate_hz"], audit["sample_unit"]
    native_rows, comparison_rows, response_rows, summaries, case_list = [], [], [], [], []
    response_records = []
    for n in audit["lengths"]:
        for case_name, x, construction in cases(n):
            record = SignalRecord(x, fs, unit)
            pair = {
                mode: evaluate(record, BoundarySettings("db4", 2, mode)) for mode in audit["modes"]
            }
            case_id = f"n{n}_{case_name}"
            case_list.append(
                {
                    "case_id": case_id,
                    "construction": construction,
                    "record_id": pair["periodization"]["record_id"],
                    "n_samples": n,
                }
            )
            for mode, result in pair.items():
                summaries.append({"case_id": case_id, "mode": mode, **result})
                for group in result["groups"]:
                    native_rows.append(
                        {
                            "case_id": case_id,
                            "record_id": result["record_id"],
                            "method_id": result["method_id"],
                            "mode": mode,
                            "group": group["name"],
                            "support_kind": "native_scale_group",
                            "coefficient_count": group["coefficient_count"],
                            "original_n_denominator": n,
                            "coefficient_count_denominator": group["coefficient_count"],
                            "sum_squared_coefficients": group["sum_squared_coefficients"],
                            "record_normalized_coefficient_energy": group[
                                "record_normalized_coefficient_energy"
                            ],
                            "coefficient_mean_square": group["coefficient_mean_square"],
                            "record_power": result["record_power"],
                            "record_power_ratio": group["record_power_ratio"],
                            "record_power_ratio_reason": group["record_power_ratio_reason"],
                            "method_total_power": result["method_total_power"],
                            "method_total_share": group["method_total_share"],
                            "method_total_share_reason": group["method_total_share_reason"],
                            "structural_extension_dependency_count": group[
                                "structural_extension_dependency_count"
                            ],
                            "power_unit": result["power_unit"],
                            "status": "ok",
                        }
                    )
            for left, right in zip(
                pair["periodic"]["groups"], pair["periodization"]["groups"], strict=True
            ):
                comparison_rows.append(
                    {
                        "case_id": case_id,
                        "record_id": pair["periodic"]["record_id"],
                        "group_role": left["name"],
                        "comparison_status": "descriptive",
                        "difference_label": (
                            "periodic_minus_periodization_record_normalized_coefficient_energy"
                        ),
                        "periodic_method_id": pair["periodic"]["method_id"],
                        "periodization_method_id": pair["periodization"]["method_id"],
                        "periodic_value": left["record_normalized_coefficient_energy"],
                        "periodization_value": right["record_normalized_coefficient_energy"],
                        "difference": left["record_normalized_coefficient_energy"]
                        - right["record_normalized_coefficient_energy"],
                        "power_unit": pair["periodic"]["power_unit"],
                    }
                )
    n = audit["response_length"]
    j = np.arange(n)
    for k in range(n // 2 + 1):
        omega = 2 * np.pi * k / n
        cosine = np.cos(omega * j)
        sine = np.sin(omega * j)
        for kind_name, samples in (("cosine", cosine), ("sine", sine)):
            response_records.append({
                "case_id": f"response_k{k}_{kind_name}",
                "construction": f"x[j]={kind_name}(2*pi*{k}*j/64)",
                "record_id": digest(np.asarray(samples, dtype="<f8").tobytes()),
                "n_samples": n,
            })
        for mode in audit["modes"]:
            c = evaluate(SignalRecord(cosine, fs, unit), BoundarySettings("db4", 2, mode))
            s = evaluate(SignalRecord(sine, fs, unit), BoundarySettings("db4", 2, mode))
            expected, kind = _response_reference(omega, mode, cosine, sine, n)
            for group, cg, sg, value in zip(
                ("A2", "D2", "D1"), c["groups"], s["groups"], expected, strict=True
            ):
                combined = (
                    cg["record_normalized_coefficient_energy"]
                    + sg["record_normalized_coefficient_energy"]
                )
                response_rows.append(
                    {
                        "mode": mode,
                        "group": group,
                        "frequency_bin": k,
                        "frequency_hz": fs * k / n,
                        "omega_radians": omega,
                        "combined_cosine_plus_sine_response": combined,
                        "reference_kind": kind,
                        "reference_applicable": True,
                        "reference_value": value,
                        "residual": combined - value,
                        "circular_formula_applicable": mode == "periodization",
                        "circular_formula_unavailable_reason": None
                        if mode == "periodization"
                        else "redundant_finite_periodic_transform",
                    }
                )
    native_data = _csv_bytes(list(native_rows[0]), native_rows)
    comparison_data = _csv_bytes(list(comparison_rows[0]), comparison_rows)
    response_data = _csv_bytes(list(response_rows[0]), response_rows)
    summary = {
        "config_kind": "dwt_boundary_audit",
        "schema_version": 1,
        "resolved_configuration": config,
        "case_list": case_list,
        "response_panel": {
            "n_samples": 64,
            "unit_amplitude": True,
            "coherent_bins": list(range(33)),
            "combination": "cosine_plus_sine_not_average",
            "input_records": response_records,
        },
        "results": summaries,
    }
    output_data = {
        "native_groups.csv": native_data,
        "mode_comparisons.csv": comparison_data,
        "responses.csv": response_data,
        "summary.json": json_bytes(summary),
    }
    inventory, source_digest = _source_inventory(root)
    revision = _git(root, "rev-parse", "HEAD")
    git_root = _git(root, "rev-parse", "--show-toplevel")
    status = _git(root, "status", "--porcelain")
    state = (
        "unversioned"
        if revision is None
        or git_root is None
        or status is None
        or Path(git_root).resolve() != root.resolve()
        else "dirty"
        if status
        else "clean"
    )
    manifest = {
        "config_kind": "dwt_boundary_audit",
        "schema_version": 1,
        "package_version": __version__,
        "run_status": "complete",
        "resolved_configuration": config,
        "resolved_configuration_sha256": digest(
            json.dumps(config, sort_keys=True, separators=(",", ":")).encode()
        ),
        "source_config_sha256": digest(config_path.read_bytes()),
        "input_records": [
            {
                "case_id": c["case_id"],
                "sha256": c["record_id"],
                "dtype": "float64",
                "byte_order": "little",
                "shape": [c["n_samples"]],
            }
            for c in case_list + response_records
        ],
        "python_version": platform.python_version(),
        "numpy_version": np.__version__,
        "pywavelets_distribution_version": importlib.metadata.version("PyWavelets"),
        "pywavelets_version": pywt.__version__,
        "pywavelets_import_path": str(Path(pywt.__file__).resolve()),
        "source_revision": revision if state != "unversioned" else None,
        "source_state": state,
        "source_files": inventory,
        "source_digest": source_digest,
        "outputs": {name: digest(data) for name, data in output_data.items()},
        "invocation": {
            "started_at_utc": started.isoformat(),
            "elapsed_seconds": perf_counter() - clock,
            "arguments": [
                "boundary-audit",
                "--config",
                str(config_path),
                "--out",
                "<output-directory>",
            ],
            "output_directory": str(out.resolve()),
            "executable": sys.executable,
        },
    }
    out.mkdir(parents=True, exist_ok=True)
    for name, data in output_data.items():
        _atomic_write(out / name, data)
    _atomic_write(out / "manifest.json", json_bytes(manifest))
    return manifest
