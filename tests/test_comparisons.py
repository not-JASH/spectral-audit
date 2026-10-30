"""Assertions on target decisions and authorized arithmetic, independent of CSV labels."""

import csv
import json
import shutil
import subprocess
from dataclasses import replace
from pathlib import Path

import numpy as np
import pytest

from spectral_audit.comparison_audit import _fixtures, run
from spectral_audit.comparisons import ComparisonRequest, compare_quantities
from spectral_audit.types import SignalRecord

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "configs/m1_comparison_controls.toml"


@pytest.fixture(scope="module")
def controls():
    return _fixtures(ROOT)[0]


def test_parseval_rules_have_metadata_evidence(controls):
    for name in ("direct_dft_total", "haar_dft_total", "db4_partition"):
        result = compare_quantities(*controls[name])
        assert (result.decision, result.relation, result.numerical_status) == (
            "accepted", "same_target", "agree"
        )
        assert "B_actual_record_mean_square_v1" in result.rules
        assert result.common_target == ("actual_record_mean_square",)


def test_numerical_fault_does_not_change_target(controls):
    result = compare_quantities(*controls["perturbed_value"])
    assert result.decision == "accepted"
    assert result.numerical_status == "disagree"
    assert result.signed_difference == pytest.approx(0.1)
    assert result.tolerance_unit == "(a.u.)^2"


def test_equal_values_do_not_establish_target(controls):
    exact = compare_quantities(*controls["coincident_dft_welch_exact"])
    descriptive = compare_quantities(*controls["dft_welch_descriptive"])
    assert exact.reference_value == pytest.approx(exact.candidate_value)
    assert exact.decision == "refused" and exact.signed_difference is None
    assert descriptive.relation == "different_functionals"
    assert descriptive.signed_difference == pytest.approx(0)
    assert descriptive.numerical_status == "descriptive"
    assert descriptive.tolerance is None


def test_conversion_is_explicit_and_valid_for_redundant_group(controls):
    for name in ("haar_conversion", "redundant_conversion"):
        ref, cand, request = controls[name]
        result = compare_quantities(ref, cand, request)
        assert result.relation == "exact_conversion"
        assert result.conversion_factor == cand.coefficient_count / cand.n
        assert result.converted_candidate_value == pytest.approx(ref.value)
        assert result.original_n == cand.n
        assert result.coefficient_count == cand.coefficient_count
        assert compare_quantities(ref, cand, ComparisonRequest()).decision == "refused"


def test_odd_accidental_equality_and_denominator_values(controls):
    odd = compare_quantities(*controls["odd_periodization_partition"])
    assert odd.reference_value == pytest.approx(odd.candidate_value)
    assert odd.decision == "refused" and odd.signed_difference is None
    ratios = compare_quantities(*controls["welch_ratio_denominators"])
    assert ratios.reference_value == pytest.approx(ratios.candidate_value)
    assert ratios.decision == "refused" and ratios.signed_difference is None


def test_zero_absolute_and_undefined_ratio(controls):
    absolute = compare_quantities(*controls["zero_absolute"])
    ratio = compare_quantities(*controls["zero_ratio"])
    assert absolute.decision == "accepted" and absolute.signed_difference == 0
    assert ratio.decision == "accepted" and ratio.relation == "same_target"
    assert ratio.reason == "zero_denominator" and ratio.numerical_status == "unavailable_metric"
    assert ratio.signed_difference is None


def test_context_and_malformed_values(controls):
    for name in ("opposite_records", "different_rate", "different_unit"):
        result = compare_quantities(*controls[name])
        assert result.decision == "refused" and result.signed_difference is None
    for name in ("settings_hash_conflict", "impossible_count", "nonfinite_value"):
        assert compare_quantities(*controls[name]).decision == "invalid"
    assert compare_quantities(*controls["unknown_method"]).decision == "unavailable"


def test_audit_determinism_hashes_and_refusal(tmp_path):
    a, b = tmp_path / "a", tmp_path / "b"
    first = run(CONFIG, a, ROOT)
    second = run(CONFIG, b, ROOT)
    assert first["outputs"] == second["outputs"]
    assert first["run_status"] == "complete"
    for name, expected_hash in first["outputs"].items():
        from spectral_audit.io import digest

        assert digest((a / name).read_bytes()) == expected_hash
    summary = json.loads((a / "summary.json").read_text())
    assert summary["control_count"] == 38
    assert summary["unexpected_outcomes"] == []
    assert summary["false_acceptances"]["count"] == 0
    assert summary["false_rejections"]["count"] == 0
    with (a / "comparison_controls.csv").open(newline="") as stream:
        rows = list(csv.DictReader(stream))
    assert len(rows) == 38 and all(r["expected_match"] == "True" for r in rows)
    with pytest.raises(ValueError, match="nonempty"):
        run(CONFIG, a, ROOT)


def test_archive_and_checkout_provenance(tmp_path, monkeypatch):
    import spectral_audit.comparison_audit as audit

    source = tmp_path / "source"
    shutil.copytree(ROOT / "src", source / "src")
    shutil.copytree(ROOT / "configs", source / "configs")
    for name in ("pyproject.toml", "requirements-lock.txt"):
        shutil.copy2(ROOT / name, source / name)
    config = source / "configs/m1_comparison_controls.toml"

    missing = run(config, tmp_path / "missing", source)
    assert (missing["source_state"], missing["source_revision"]) == ("unversioned", None)
    assert missing["source_files"] and missing["source_digest"]

    original_git = audit._git
    monkeypatch.setattr(audit, "_git", lambda root, *args: None if args == (
        "status", "--porcelain"
    ) else original_git(root, *args))
    unusable = run(config, tmp_path / "unusable", source)
    assert (unusable["source_state"], unusable["source_revision"]) == ("unversioned", None)
    monkeypatch.setattr(audit, "_git", original_git)

    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)
    unrelated = run(config, tmp_path / "unrelated", source)
    assert (unrelated["source_state"], unrelated["source_revision"]) == (
        "unversioned", None
    )

    subprocess.run(["git", "init", "-q", str(source)], check=True)
    subprocess.run(["git", "-C", str(source), "add", "src", "configs",
                    "pyproject.toml", "requirements-lock.txt"], check=True)
    subprocess.run(["git", "-C", str(source), "-c", "user.name=Test",
                    "-c", "user.email=test@example.invalid", "commit", "-qm", "source"], check=True)
    revision = subprocess.check_output(["git", "-C", str(source), "rev-parse", "HEAD"],
                                       text=True).strip()
    clean = run(config, tmp_path / "clean", source)
    assert (clean["source_state"], clean["source_revision"]) == ("clean", revision)

    (source / "pyproject.toml").write_text((source / "pyproject.toml").read_text() + "\n")
    dirty = run(config, tmp_path / "dirty", source)
    assert (dirty["source_state"], dirty["source_revision"]) == ("dirty", revision)


def test_audit_manifest_is_last_and_unexpected_outcome_fails(tmp_path, monkeypatch):
    import spectral_audit.comparison_audit as audit

    original = audit._atomic_write

    def fail_summary(path, data):
        if path.name == "summary.json":
            raise OSError("injected output failure")
        return original(path, data)

    monkeypatch.setattr(audit, "_atomic_write", fail_summary)
    out = tmp_path / "failed"
    with pytest.raises(OSError, match="injected output failure"):
        run(CONFIG, out, ROOT)
    assert not (out / "manifest.json").exists()
    monkeypatch.setattr(audit, "_atomic_write", original)
    text = CONFIG.read_text().replace(
        'perturbed_value = { decision = "accepted", reason = "supported_exact_identity", '
        'numerical_status = "disagree"',
        'perturbed_value = { decision = "accepted", reason = "supported_exact_identity", '
        'numerical_status = "agree"',
    )
    wrong = tmp_path / "wrong.toml"
    wrong.write_text(text)
    with pytest.raises(ValueError, match="unexpected outcomes"):
        run(wrong, tmp_path / "unexpected", ROOT)
    manifest = json.loads((tmp_path / "unexpected" / "manifest.json").read_text())
    assert manifest["run_status"] == "unexpected_outcomes"


def test_pairing_uses_semantic_support_and_group_role(controls):
    assert compare_quantities(*controls["reordered_bands"]).decision == "accepted"
    assert compare_quantities(*controls["reordered_groups"]).decision == "accepted"
    ref, cand, request = controls["reordered_bands"]
    changed = replace(cand, support=(1.0, 16.0, False))
    assert compare_quantities(ref, changed, request).decision == "refused"


def test_record_bytes_are_separate_from_units(controls):
    ref, changed, request = controls["different_unit"]
    assert ref.record_id == changed.record_id
    assert ref.context_fingerprint != changed.context_fingerprint
    assert compare_quantities(ref, changed, request).decision == "refused"


def test_unavailable_population_request_even_for_identical_operands(controls):
    ref, _, _ = controls["direct_dft_total"]
    result = compare_quantities(ref, ref, ComparisonRequest(target_scope="population"))
    assert result.decision == "unavailable"
    assert result.signed_difference is None


def test_zero_sample_record_has_valid_power():
    from spectral_audit.comparisons import direct_power

    q = direct_power(SignalRecord(np.zeros(32), 128, "V"))
    assert compare_quantities(q, q, ComparisonRequest()).signed_difference == 0
