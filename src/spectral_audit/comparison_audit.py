"""Deterministic finite-record comparison controls from current measurement outputs."""

import csv
import importlib.metadata
import io
import platform
import tomllib
from collections import Counter
from dataclasses import replace
from pathlib import Path

import numpy as np
import pywt
import scipy

from spectral_audit import __version__
from spectral_audit.boundary import BoundarySettings, evaluate
from spectral_audit.comparisons import (
    POLICY_VERSION,
    ComparisonRequest,
    band_quantity,
    compare_quantities,
    direct_power,
    native_quantity,
    native_total,
    total_quantity,
)
from spectral_audit.config import canonical_json_bytes, load_demo_config, load_measure_config
from spectral_audit.estimators.dwt import DWTSettings, measure_dwt
from spectral_audit.estimators.welch import measure_welch
from spectral_audit.io import _atomic_write, _git, _number, _source_inventory, digest, json_bytes
from spectral_audit.reference import fourier_reference
from spectral_audit.signals import make_tones
from spectral_audit.types import SignalRecord


def load_config(path: Path) -> dict:
    with path.open("rb") as stream:
        data = tomllib.load(stream)
    if set(data) != {"config_kind", "schema_version", "controls"}:
        raise ValueError("comparison audit requires config_kind, schema_version, controls")
    if data["config_kind"] != "m1_comparison_controls" or data["schema_version"] != 1:
        raise ValueError("unsupported comparison audit configuration")
    if not isinstance(data["controls"], dict) or not data["controls"]:
        raise ValueError("comparison controls must be a nonempty table")
    for name, expected in data["controls"].items():
        if (
            not name
            or not isinstance(expected, dict)
            or set(expected) != {"decision", "reason", "numerical_status", "category"}
        ):
            raise ValueError(f"invalid expected outcome for {name}")
        if expected["decision"] not in {"accepted", "refused", "unavailable", "invalid"}:
            raise ValueError(f"invalid expected decision for {name}")
    return data


def _fixtures(root: Path):
    m0 = load_demo_config(root / "configs/m0_tones.toml")
    m1 = load_measure_config(root / "configs/m1_welch_tones.toml")
    edge = load_measure_config(root / "configs/m1_welch_edge_tone.toml")
    x = make_tones(m0.signal, m0.record)
    dft = fourier_reference(x, m0.bands)
    welch = measure_welch(x, m1.tones.bands, m1.welch)
    haar = measure_dwt(x, DWTSettings())
    xe = make_tones(edge.tones.signal, edge.tones.record)
    de = fourier_reference(xe, edge.tones.bands)
    we = measure_welch(xe, edge.tones.bands, edge.welch)
    short = SignalRecord(np.eye(1, 32, 15)[0], 128, "V")
    odd = SignalRecord(np.eye(1, 31, 15)[0], 128, "V")
    db4 = {
        mode: evaluate(short, BoundarySettings("db4", 2, mode))
        for mode in ("periodic", "periodization")
    }
    db4_long = evaluate(x, BoundarySettings("db4", 2, "periodization"))
    odd_db4 = evaluate(odd, BoundarySettings("db4", 2, "periodization"))
    z = SignalRecord(np.zeros(256), x.sampling_rate_hz, x.sample_unit)
    dz = fourier_reference(z, m0.bands)
    wz = measure_welch(z, m1.tones.bands, m1.welch)
    band = band_quantity(dft, 0)
    wband = band_quantity(welch, 0)
    a2 = native_quantity(haar, "A2")
    db4a = native_quantity(db4["periodization"], "A2")
    periodic = native_quantity(db4["periodic"], "A2")
    periodized = native_quantity(db4["periodization"], "A2")
    direct = direct_power(x)
    exact = ComparisonRequest()
    descriptive = ComparisonRequest("descriptive_difference")
    convert = ComparisonRequest(conversion="C_native_mean_to_record_energy_v1")
    cases = {
        "direct_dft_total": (direct, total_quantity(dft), exact),
        "haar_dft_total": (total_quantity(dft), native_total(haar), exact),
        "db4_partition": (direct_power(short), native_total(db4["periodization"]), exact),
        "haar_conversion": (a2, native_quantity(haar, "A2", "coefficient_mean_square"), convert),
        "redundant_conversion": (
            periodic,
            native_quantity(db4["periodic"], "A2", "coefficient_mean_square"),
            convert,
        ),
        "independent_calls": (band, band_quantity(fourier_reference(x, m0.bands), 0), exact),
        "cosmetic_band_name": (band, replace(band, labels=("renamed",)), exact),
        "explicit_defaults": (
            wband,
            band_quantity(
                measure_welch(
                    x,
                    m1.tones.bands,
                    type(m1.welch)(
                        m1.welch.segment_length, m1.welch.noverlap, m1.welch.segment_length
                    ),
                ),
                0,
            ),
            exact,
        ),
        "perturbed_value": (band, replace(band, value=band.value + 0.1), exact),
        "coincident_dft_welch_exact": (band, wband, exact),
        "dft_welch_descriptive": (band, wband, descriptive),
        "edge_descriptive": (band_quantity(de, 0), band_quantity(we, 0), descriptive),
        "haar_fourier": (a2, band, exact),
        "haar_db4": (a2, native_quantity(db4_long, "A2"), exact),
        "periodic_partition": (direct_power(short), native_total(db4["periodic"]), exact),
        "odd_periodization_partition": (direct_power(odd), native_total(odd_db4), exact),
        "welch_ratio_denominators": (
            band_quantity(welch, 0, "record_power_ratio"),
            band_quantity(welch, 0, "method_total_share"),
            exact,
        ),
        "opposite_records": (
            direct,
            direct_power(SignalRecord(-x.samples, x.sampling_rate_hz, x.sample_unit)),
            exact,
        ),
        "different_rate": (
            direct,
            direct_power(SignalRecord(x.samples, 256, x.sample_unit)),
            exact,
        ),
        "different_unit": (
            direct,
            direct_power(SignalRecord(x.samples, x.sampling_rate_hz, "mV")),
            exact,
        ),
        "unknown_method": (
            band,
            replace(
                band,
                method_id="unknown_v1",
                settings={"method_id": "unknown_v1"},
                settings_hash=digest(canonical_json_bytes({"method_id": "unknown_v1"})),
            ),
            exact,
        ),
        "population_request": (band, band, ComparisonRequest(target_scope="population")),
        "unknown_conversion": (
            a2,
            native_quantity(haar, "A2", "coefficient_mean_square"),
            ComparisonRequest(conversion="unknown_mapping"),
        ),
        "zero_absolute": (
            band_quantity(dz, 0),
            band_quantity(fourier_reference(z, m0.bands), 0),
            exact,
        ),
        "zero_ratio": (
            band_quantity(dz, 0, "record_power_ratio"),
            band_quantity(fourier_reference(z, m0.bands), 0, "record_power_ratio"),
            exact,
        ),
        "settings_hash_conflict": (band, replace(band, settings_hash="0" * 64), exact),
        "impossible_count": (a2, replace(a2, coefficient_count=a2.n + 1), exact),
        "nonfinite_value": (band, replace(band, value=float("nan")), exact),
        "changed_preprocessing": (band, replace(band, preprocessing="demeaned"), exact),
        "changed_normalization": (a2, replace(a2, normalization="coefficient_count"), exact),
        "changed_fourier_support": (band, replace(band, support=(0.0, 15.0, False)), exact),
        "changed_retention": (a2, replace(a2, retained="interior_only"), exact),
        "missing_evidence": (band, replace(band, settings_hash=""), exact),
        "db4_mode_descriptive": (periodized, periodic, descriptive),
        "conversion_required": (a2, native_quantity(haar, "A2", "coefficient_mean_square"), exact),
        "reordered_bands": (
            band,
            band_quantity(
                replace(dft, bands=tuple(reversed(dft.bands)), powers=tuple(reversed(dft.powers))),
                len(dft.bands) - 1,
            ),
            exact,
        ),
        "reordered_groups": (
            periodized,
            native_quantity(
                {**db4["periodization"], "groups": list(reversed(db4["periodization"]["groups"]))},
                "A2",
            ),
            exact,
        ),
        "zero_welch_absolute": (
            band_quantity(wz, 0),
            band_quantity(measure_welch(z, m1.tones.bands, m1.welch), 0),
            exact,
        ),
    }
    return cases, {
        "m0": direct.record_id,
        "edge": de.record_id,
        "db4_32": db4a.record_id,
        "db4_31": odd_db4["record_id"],
        "zero": dz.record_id,
    }


def run(config_path: Path, out: Path, root: Path) -> dict:
    if out.exists() and (not out.is_dir() or any(out.iterdir())):
        raise ValueError(f"output directory already exists and is nonempty: {out}")
    config = load_config(config_path)
    cases, contexts = _fixtures(root)
    if set(config["controls"]) != set(cases):
        raise ValueError(
            "control inventory mismatch: " + str(sorted(set(cases) ^ set(config["controls"])))
        )
    rows = []
    by_category = Counter()
    decisions = Counter()
    unexpected = []
    false_accept = false_reject = 0
    valid_exact = invalid_exact = 0
    for name, (reference, candidate, request) in cases.items():
        expected = config["controls"][name]
        result = compare_quantities(reference, candidate, request)
        matched = (
            result.decision == expected["decision"]
            and result.reason == expected["reason"]
            and result.numerical_status == expected["numerical_status"]
        )
        if not matched:
            unexpected.append(name)
        by_category[expected["category"]] += 1
        decisions[result.decision] += 1
        if request.kind == "exact_target" and expected["decision"] in {"accepted", "refused"}:
            if expected["decision"] == "accepted":
                valid_exact += 1
                false_reject += result.decision != "accepted"
            else:
                invalid_exact += 1
                false_accept += result.decision == "accepted"
        rows.append(
            {
                "case_id": name,
                "control_fixture": name
                in {
                    "perturbed_value",
                    "settings_hash_conflict",
                    "impossible_count",
                    "nonfinite_value",
                    "changed_preprocessing",
                    "changed_normalization",
                    "changed_fourier_support",
                    "changed_retention",
                    "missing_evidence",
                },
                "category": expected["category"],
                "claim": request.kind,
                "conversion_request": request.conversion,
                "reference_method": reference.method_id,
                "candidate_method": candidate.method_id,
                "reference_record_id": reference.record_id,
                "candidate_record_id": candidate.record_id,
                "reference_context": reference.context_fingerprint,
                "candidate_context": candidate.context_fingerprint,
                "reference_kind": reference.kind,
                "candidate_kind": candidate.kind,
                "reference_labels": "|".join(reference.labels),
                "candidate_labels": "|".join(candidate.labels),
                "reference_support": repr(reference.support),
                "candidate_support": repr(candidate.support),
                "reference_settings": canonical_json_bytes(reference.settings).decode("utf-8"),
                "candidate_settings": canonical_json_bytes(candidate.settings).decode("utf-8"),
                "reference_settings_hash": reference.settings_hash,
                "candidate_settings_hash": candidate.settings_hash,
                "reference_n": reference.n,
                "candidate_n": candidate.n,
                "reference_sampling_rate_hz": reference.fs,
                "candidate_sampling_rate_hz": candidate.fs,
                "reference_input_unit": reference.unit,
                "candidate_input_unit": candidate.unit,
                "reference_preprocessing": reference.preprocessing,
                "candidate_preprocessing": candidate.preprocessing,
                "reference_normalization": reference.normalization,
                "candidate_normalization": candidate.normalization,
                "reference_denominator": repr(reference.denominator and (
                    reference.denominator.method_id, reference.denominator.kind,
                    reference.denominator.normalization, reference.denominator.support)),
                "candidate_denominator": repr(candidate.denominator and (
                    candidate.denominator.method_id, candidate.denominator.kind,
                    candidate.denominator.normalization, candidate.denominator.support)),
                "decision": result.decision,
                "relation": result.relation,
                "reason": result.reason,
                "rules": "|".join(result.rules),
                "common_target": repr(result.common_target),
                "reference_value": result.reference_value,
                "candidate_value": result.candidate_value,
                "converted_candidate_value": result.converted_candidate_value,
                "conversion_factor": result.conversion_factor,
                "coefficient_count": result.coefficient_count,
                "original_n": result.original_n,
                "signed_difference": result.signed_difference,
                "orientation": result.orientation,
                "numerical_status": result.numerical_status,
                "tolerance": result.tolerance,
                "tolerance_unit": result.tolerance_unit,
                "expected_decision": expected["decision"],
                "expected_reason": expected["reason"],
                "expected_numerical_status": expected["numerical_status"],
                "expected_match": matched,
            }
        )
    stream = io.StringIO(newline="")
    writer = csv.DictWriter(stream, fieldnames=list(rows[0]), lineterminator="\n")
    writer.writeheader()
    for row in rows:
        writer.writerow(
            {
                key: _number(value) if isinstance(value, float) else "" if value is None else value
                for key, value in row.items()
            }
        )
    csv_data = stream.getvalue().encode("utf-8")
    summary = {
        "policy_version": POLICY_VERSION,
        "config_kind": config["config_kind"],
        "complete_control_inventory": list(cases),
        "coverage_by_category": dict(sorted(by_category.items())),
        "decision_counts": dict(sorted(decisions.items())),
        "control_count": len(cases),
        "false_acceptances": {"count": false_accept, "denominator": invalid_exact},
        "false_rejections": {"count": false_reject, "denominator": valid_exact},
        "unavailable_count": decisions["unavailable"],
        "invalid_count": decisions["invalid"],
        "descriptive_count": sum(r["numerical_status"] == "descriptive" for r in rows),
        "undefined_metric_count": sum(r["numerical_status"] == "unavailable_metric" for r in rows),
        "unexpected_outcomes": unexpected,
        "scope": "finite deterministic controls; no general diagnostic performance estimate",
    }
    summary_data = json_bytes(summary)
    inventory, source_digest = _source_inventory(root)
    revision = _git(root, "rev-parse", "HEAD")
    status = _git(root, "status", "--porcelain")
    output_data = {"comparison_controls.csv": csv_data, "summary.json": summary_data}
    manifest = {
        "config_kind": config["config_kind"],
        "schema_version": 1,
        "policy_version": POLICY_VERSION,
        "package_version": __version__,
        "run_status": "complete" if not unexpected else "unexpected_outcomes",
        "resolved_configuration": config,
        "resolved_configuration_sha256": digest(canonical_json_bytes(config)),
        "source_config_sha256": digest(config_path.read_bytes()),
        "input_contexts": contexts,
        "python_version": platform.python_version(),
        "numpy_version": np.__version__,
        "scipy_version": scipy.__version__,
        "pywavelets_version": pywt.__version__,
        "pywavelets_distribution_version": importlib.metadata.version("PyWavelets"),
        "source_revision": revision,
        "source_state": "dirty" if status else "clean",
        "source_files": inventory,
        "source_digest": source_digest,
        "outputs": {name: digest(data) for name, data in output_data.items()},
    }
    out.mkdir(parents=True, exist_ok=True)
    for name, data in output_data.items():
        _atomic_write(out / name, data)
    _atomic_write(out / "manifest.json", json_bytes(manifest))
    if unexpected:
        raise ValueError(f"comparison audit unexpected outcomes: {unexpected}")
    return manifest
