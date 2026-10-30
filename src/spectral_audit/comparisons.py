"""Bounded paired finite-record comparison contract (policy v1)."""

from dataclasses import dataclass, field, replace
from hashlib import sha256
from math import isfinite

from spectral_audit.config import canonical_json_bytes
from spectral_audit.estimators.dwt import METHOD_ID as HAAR_ID
from spectral_audit.estimators.dwt import NativeScaleResult
from spectral_audit.estimators.welch import METHOD_ID as WELCH_ID
from spectral_audit.types import Measurement, SignalRecord

POLICY_VERSION = "m1_comparison_v1"
DFT_ID = "finite_record_dft_v1"
DB4_MODES = {"periodic", "periodization"}
GROUPS = {"A2", "D2", "D1"}
DFT_SETTINGS = {
    "method_id": DFT_ID,
    "fft_norm": "ortho",
    "preprocessing": "none",
    "support": "full_finite_record",
    "bin_selection": "absolute_physical_frequency",
    "endpoint_rule": "lower_inclusive; internal_upper_exclusive; final_upper_inclusive",
    "normalization": "unitary_dft_squared_magnitude_divided_by_n",
}


def _hash(value):
    return sha256(canonical_json_bytes(value)).hexdigest()


@dataclass(frozen=True)
class Quantity:
    method_id: str
    record_id: str
    n: int
    fs: float
    unit: str
    preprocessing: str
    settings: dict
    settings_hash: str
    kind: str
    normalization: str
    value: float | None
    value_unit: str
    support: tuple | None = None
    group: str | None = None
    coefficient_count: int | None = None
    denominator: "Quantity | None" = None
    labels: tuple[str, ...] = ()
    origin: str = "result"
    retained: str = "all"
    source_result: object = field(default=None, repr=False, compare=False)

    @property
    def context(self):
        return (self.record_id, self.n, self.fs, self.unit, self.preprocessing)

    @property
    def context_fingerprint(self):
        return _hash(self.context)


@dataclass(frozen=True)
class ComparisonRequest:
    kind: str = "exact_target"
    conversion: str | None = None
    target_scope: str = "finite_record"
    atol: float = 1e-12
    rtol: float = 1e-12


@dataclass(frozen=True)
class ComparisonResult:
    decision: str
    relation: str
    reason: str
    rules: tuple[str, ...] = ()
    common_target: tuple | None = None
    reference_value: float | None = None
    candidate_value: float | None = None
    converted_candidate_value: float | None = None
    conversion_factor: float | None = None
    coefficient_count: int | None = None
    original_n: int | None = None
    signed_difference: float | None = None
    orientation: str = "candidate_minus_reference"
    numerical_status: str = "not_evaluated"
    tolerance: float | None = None
    tolerance_unit: str | None = None


def direct_power(record: SignalRecord) -> Quantity:
    from numpy import dot

    n = len(record.samples)
    value = float(dot(record.samples, record.samples) / n)
    record_id = sha256(record.samples.astype("<f8", copy=False).tobytes()).hexdigest()
    settings = {
        "method_id": "direct_record_mean_square_v1",
        "preprocessing": "none",
        "normalization": "dot(x,x)/n",
        "support": "all_original_samples",
    }
    return Quantity(
        settings["method_id"],
        record_id,
        n,
        record.sampling_rate_hz,
        record.sample_unit,
        "none",
        settings,
        _hash(settings),
        "actual_record_mean_square",
        "original_n",
        value,
        f"({record.sample_unit})^2",
        origin="direct",
        source_result=record,
    )


def band_quantity(result: Measurement, index: int, kind: str = "band_power") -> Quantity:
    if index < 0 or index >= len(result.bands):
        raise IndexError(index)
    band = result.bands[index]
    settings = DFT_SETTINGS if result.method_id == DFT_ID else result.settings
    if settings is None:
        settings = {}
    settings_hash = _hash(settings) if result.method_id == DFT_ID else result.settings_hash or ""
    base = Quantity(
        result.method_id,
        result.record_id or "",
        result.n_samples or 0,
        result.sampling_rate_hz or 0,
        result.sample_unit or "",
        result.preprocessing,
        settings,
        settings_hash,
        "band_power",
        "band_bin_sum_record_power",
        result.powers[index],
        result.power_unit or "",
        support=(band.lower_hz, band.upper_hz, band.include_upper),
        labels=(band.name,),
        source_result=result,
    )
    if kind == "band_power":
        return base
    if kind == "record_power_ratio":
        denominator = replace(
            base,
            kind="actual_record_mean_square",
            normalization="original_n",
            value=result.record_power,
            support=None,
            labels=(),
        )
        value = result.fractions[index]
    elif kind == "method_total_share":
        denominator = total_quantity(result)
        value = (
            result.method_total_fractions[index]
            if result.method_total_fractions
            else None
            if result.method_total == 0
            else base.value / result.method_total
        )
    else:
        raise ValueError("unsupported band quantity kind")
    return replace(
        base,
        kind="ratio",
        normalization="numerator_over_denominator",
        value=value,
        value_unit="1",
        denominator=denominator,
    )


def total_quantity(result: Measurement) -> Quantity:
    settings = DFT_SETTINGS if result.method_id == DFT_ID else result.settings or {}
    bands = tuple((b.lower_hz, b.upper_hz, b.include_upper) for b in result.bands)
    return Quantity(
        result.method_id,
        result.record_id or "",
        result.n_samples or 0,
        result.sampling_rate_hz or 0,
        result.sample_unit or "",
        result.preprocessing,
        settings,
        _hash(settings) if result.method_id == DFT_ID else result.settings_hash or "",
        "method_total",
        "sum_complete_band_powers",
        result.method_total,
        result.power_unit or "",
        support=bands,
        labels=tuple(b.name for b in result.bands),
        source_result=result,
    )


def native_quantity(
    result: NativeScaleResult | dict, group: str, kind: str = "record_normalized_coefficient_energy"
) -> Quantity:
    if isinstance(result, NativeScaleResult):
        groups = {g.name: g for g in result.groups}
        if group not in groups:
            raise ValueError("unknown native group")
        g = groups[group]
        count, energy, mean = (
            g.coefficient_count,
            g.record_power_contribution,
            g.coefficient_mean_square,
        )
        retained = result.settings["retained_coefficient_policy"]
        settings = result.settings
        data = result.__dict__
    else:
        groups = {g["name"]: g for g in result["groups"]}
        if group not in groups:
            raise ValueError("unknown native group")
        g = groups[group]
        count = g["coefficient_count"]
        energy = g["record_normalized_coefficient_energy"]
        mean = g["coefficient_mean_square"]
        retained = result["settings"].get("retained_coefficient_policy")
        settings = result["settings"]
        data = result
    if kind not in {"record_normalized_coefficient_energy", "coefficient_mean_square"}:
        raise ValueError("unsupported native quantity kind")
    return Quantity(
        data["method_id"],
        data["record_id"],
        data["n_samples"],
        data["sampling_rate_hz"],
        data["sample_unit"],
        data.get("preprocessing", settings.get("preprocessing", "")),
        settings,
        data["settings_hash"],
        kind,
        "original_n" if kind == "record_normalized_coefficient_energy" else "coefficient_count",
        energy if kind == "record_normalized_coefficient_energy" else mean,
        data["power_unit"],
        group=group,
        coefficient_count=count,
        labels=(group,),
        retained=retained,
        source_result=result,
    )


def native_total(result: NativeScaleResult | dict) -> Quantity:
    groups = result.groups if isinstance(result, NativeScaleResult) else result["groups"]
    names = tuple(g.name if isinstance(result, NativeScaleResult) else g["name"] for g in groups)
    counts = tuple(
        (g.name, g.coefficient_count)
        if isinstance(result, NativeScaleResult)
        else (g["name"], g["coefficient_count"])
        for g in groups
    )
    first = native_quantity(result, names[0])
    value = (
        result.method_total_power
        if isinstance(result, NativeScaleResult)
        else result["method_total_power"]
    )
    return replace(
        first,
        kind="method_total",
        normalization="sum_all_native_group_energy_over_n",
        value=value,
        group=None,
        coefficient_count=None,
        support=counts,
        labels=names,
    )


def _validate(q: Quantity) -> str | None:
    if not isinstance(q, Quantity) or q.source_result is None:
        return "missing_result_binding"
    if (
        not q.record_id
        or len(q.record_id) != 64
        or any(c not in "0123456789abcdef" for c in q.record_id)
    ):
        return "malformed_context"
    if (
        type(q.n) is not int
        or q.n < 2
        or not isinstance(q.fs, (int, float))
        or not isfinite(q.fs)
        or q.fs <= 0
    ):
        return "malformed_context"
    if not q.unit or q.value_unit != ("1" if q.kind == "ratio" else f"({q.unit})^2"):
        return "malformed_units"
    if (
        not isinstance(q.settings, dict)
        or not q.settings_hash
        or _hash(q.settings) != q.settings_hash
    ):
        return "settings_hash_mismatch"
    if q.settings.get("method_id") != q.method_id:
        return "settings_method_mismatch"
    if q.value is not None and (not isinstance(q.value, (int, float)) or not isfinite(q.value)):
        return "nonfinite_value"
    if q.coefficient_count is not None and (
        type(q.coefficient_count) is not int
        or q.coefficient_count < 1
        or q.coefficient_count > 4 * q.n
    ):
        return "impossible_coefficient_count"
    if q.group in GROUPS and q.coefficient_count is not None:
        expected = None
        if q.method_id == HAAR_ID and q.n % 4 == 0:
            expected = q.n // (2 if q.group == "D1" else 4)
        elif q.method_id == "dwt_db4_periodization_level2_v1":
            half = (q.n + 1) // 2
            expected = half if q.group == "D1" else (half + 1) // 2
        if expected is not None and q.coefficient_count != expected:
            return "impossible_coefficient_count"
    if q.kind == "ratio" and (q.denominator is None or q.denominator.kind == "ratio"):
        return "malformed_denominator"
    if q.denominator is not None:
        problem = _validate(q.denominator)
        if problem:
            return problem
        if q.denominator.context != q.context:
            return "contradictory_denominator_context"
    return None


def _supported(q: Quantity) -> bool:
    if q.denominator is not None and not _supported(q.denominator):
        return False
    s = q.settings
    if q.method_id == DFT_ID:
        return s == DFT_SETTINGS and q.kind in {
            "band_power",
            "method_total",
            "ratio",
            "actual_record_mean_square",
        }
    if q.method_id == WELCH_ID:
        from spectral_audit.estimators.welch import WelchSettings

        try:
            return s == WelchSettings(s["segment_length"], s["noverlap"]).resolved() and q.kind in {
                "band_power",
                "method_total",
                "ratio",
                "actual_record_mean_square",
            }
        except (KeyError, ValueError, TypeError):
            return False
    if q.method_id == HAAR_ID:
        from spectral_audit.estimators.dwt import DWTSettings

        return s == DWTSettings().resolved() and q.kind in {
            "record_normalized_coefficient_energy",
            "coefficient_mean_square",
            "method_total",
        }
    if q.method_id.startswith("dwt_db4_"):
        mode = s.get("mode")
        if mode not in DB4_MODES or q.method_id != f"dwt_db4_{mode}_level2_v1":
            return False
        from spectral_audit.boundary import BoundarySettings

        return s == BoundarySettings("db4", 2, mode).resolved() and q.kind in {
            "record_normalized_coefficient_energy",
            "coefficient_mean_square",
            "method_total",
        }
    return (
        q.method_id == "direct_record_mean_square_v1"
        and q.kind == "actual_record_mean_square"
        and s
        == {
            "method_id": q.method_id,
            "preprocessing": "none",
            "normalization": "dot(x,x)/n",
            "support": "all_original_samples",
        }
    )


def _normalization_supported(q: Quantity) -> bool:
    if q.denominator is not None and not _normalization_supported(q.denominator):
        return False
    return q.normalization == {
        "band_power": "band_bin_sum_record_power",
        "ratio": "numerator_over_denominator",
        "actual_record_mean_square": "original_n",
        "record_normalized_coefficient_energy": "original_n",
        "coefficient_mean_square": "coefficient_count",
        "method_total": (
            "sum_complete_band_powers"
            if q.method_id in {DFT_ID, WELCH_ID}
            else "sum_all_native_group_energy_over_n"
        ),
    }.get(q.kind, "dot(x,x)/n" if q.method_id == "direct_record_mean_square_v1" else None)


def _partition(q: Quantity) -> bool:
    if q.kind != "method_total" or q.retained not in {"all", "all_coefficients"}:
        return False
    if q.method_id == DFT_ID:
        bands = q.support
        return (
            bool(bands)
            and bands[0][0] == 0
            and bands[-1][1] == q.fs / 2
            and bands[-1][2]
            and all(a[1] == b[0] and not a[2] for a, b in zip(bands, bands[1:], strict=False))
        )
    if q.method_id in {HAAR_ID, "dwt_db4_periodization_level2_v1"}:
        expected = {"A2": q.n // 4, "D2": q.n // 4, "D1": q.n // 2}
        return (
            q.n % 4 == 0
            and isinstance(q.support, tuple)
            and len(q.support) == 3
            and all(isinstance(item, tuple) and len(item) == 2 for item in q.support)
            and dict(q.support) == expected
        )
    return False


def _target(q: Quantity):
    if q.kind == "ratio":
        return (
            "ratio",
            _target(
                replace(
                    q,
                    kind="band_power",
                    denominator=None,
                    normalization="band_bin_sum_record_power",
                )
            ),
            _target(q.denominator),
        )
    if q.kind == "actual_record_mean_square" or _partition(q):
        return ("actual_record_mean_square",)
    return (
        q.method_id,
        _hash(q.settings),
        q.kind,
        q.normalization,
        q.support,
        q.group,
        q.retained,
        q.coefficient_count,
    )


def _rules(q: Quantity) -> tuple[str, ...]:
    if q.kind == "actual_record_mean_square" or _partition(q):
        return ("B_actual_record_mean_square_v1",)
    if q.kind == "ratio":
        return _rules(q.denominator)
    return ("A_identical_definition_v1",)


def compare_quantities(
    reference: Quantity, candidate: Quantity, request: ComparisonRequest
) -> ComparisonResult:
    """Decide a claim from metadata first; evaluate a permitted operation second."""
    base = {
        "reference_value": getattr(reference, "value", None),
        "candidate_value": getattr(candidate, "value", None),
    }
    if not isinstance(request, ComparisonRequest) or request.kind not in {
        "exact_target",
        "descriptive_difference",
    }:
        return ComparisonResult("invalid", "unresolved", "malformed_request", **base)
    for q in (reference, candidate):
        problem = _validate(q)
        if problem:
            return ComparisonResult("invalid", "unresolved", problem, **base)
    if (
        not isfinite(request.atol)
        or not isfinite(request.rtol)
        or request.atol < 0
        or request.rtol < 0
    ):
        return ComparisonResult("invalid", "unresolved", "invalid_tolerance", **base)
    if request.target_scope != "finite_record":
        return ComparisonResult(
            "unavailable", "unresolved", "population_mapping_unavailable", **base
        )
    if not _supported(reference) or not _supported(candidate):
        return ComparisonResult("unavailable", "unresolved", "unsupported_definition", **base)
    if reference.context != candidate.context:
        return ComparisonResult("refused", "unresolved", "paired_record_context_mismatch", **base)
    if reference.preprocessing != "none" or candidate.preprocessing != "none":
        return ComparisonResult("unavailable", "unresolved", "unsupported_preprocessing", **base)
    converted = candidate.value
    factor = None
    rules = ()
    target_candidate = candidate
    if request.conversion is not None:
        if request.conversion != "C_native_mean_to_record_energy_v1":
            return ComparisonResult("unavailable", "unresolved", "unsupported_conversion", **base)
        if (
            reference.kind != "record_normalized_coefficient_energy"
            or candidate.kind != "coefficient_mean_square"
            or reference.method_id != candidate.method_id
            or reference.group != candidate.group
            or reference.settings != candidate.settings
            or reference.coefficient_count != candidate.coefficient_count
            or reference.retained != candidate.retained
            or candidate.coefficient_count is None
        ):
            return ComparisonResult(
                "refused", "unresolved", "conversion_preconditions_failed", **base
            )
        factor = candidate.coefficient_count / candidate.n
        converted = None if candidate.value is None else candidate.value * factor
        target_candidate = replace(
            candidate, kind=reference.kind, normalization=reference.normalization, value=converted
        )
        rules = (request.conversion,)
    elif (
        reference.normalization != candidate.normalization
        and reference.method_id == candidate.method_id
        and (reference.kind == candidate.kind or reference.group == candidate.group)
        and reference.kind != "ratio"
    ):
        return ComparisonResult(
            "refused", "different_functionals", "normalization_mismatch", **base
        )
    if not _normalization_supported(reference) or not _normalization_supported(candidate):
        return ComparisonResult("unavailable", "unresolved", "unsupported_normalization", **base)
    ref_target, cand_target = _target(reference), _target(target_candidate)
    if request.kind == "exact_target":
        if ref_target != cand_target:
            return ComparisonResult(
                "refused", "different_functionals", "different_finite_record_functionals", **base
            )
        relation = "exact_conversion" if factor is not None else "same_target"
        rules += _rules(reference) + (
            () if _rules(candidate) == _rules(reference) else _rules(candidate)
        )
        common = ref_target
        reason = "supported_exact_identity"
    else:
        dft_welch = (
            {reference.method_id, candidate.method_id} == {DFT_ID, WELCH_ID}
            and reference.kind == candidate.kind == "band_power"
            and reference.support == candidate.support
        )
        db4_modes = (
            {reference.method_id, candidate.method_id}
            == {"dwt_db4_periodic_level2_v1", "dwt_db4_periodization_level2_v1"}
            and reference.kind == candidate.kind == "record_normalized_coefficient_energy"
            and reference.group == candidate.group
            and reference.retained == candidate.retained == "all"
        )
        if factor is not None or not (dft_welch or db4_modes):
            return ComparisonResult(
                "refused", "unresolved", "descriptive_permission_missing", **base
            )
        relation, common, reason = "different_functionals", None, "permitted_descriptive_pair"
        rules = ("D_dft_welch_band_v1" if dft_welch else "D_db4_mode_group_v1",)
    if reference.kind == "ratio" and (
        reference.denominator.value == 0 or candidate.denominator.value == 0
    ):
        return ComparisonResult(
            "accepted",
            relation,
            "zero_denominator",
            rules,
            common,
            **base,
            numerical_status="unavailable_metric",
            tolerance_unit="1",
        )
    if reference.value is None or converted is None:
        return ComparisonResult(
            "accepted",
            relation,
            reason,
            rules,
            common,
            **base,
            converted_candidate_value=converted,
            numerical_status="unavailable_metric",
            tolerance_unit=reference.value_unit,
        )
    difference = converted - reference.value
    if not isfinite(difference):
        return ComparisonResult(
            "accepted",
            relation,
            "numerical_range",
            rules,
            common,
            **base,
            numerical_status="unavailable_metric",
            tolerance_unit=reference.value_unit,
        )
    tolerance = request.atol + request.rtol * max(abs(reference.value), abs(converted))
    status = (
        "descriptive"
        if request.kind == "descriptive_difference"
        else "agree"
        if abs(difference) <= tolerance
        else "disagree"
    )
    return ComparisonResult(
        "accepted",
        relation,
        reason,
        rules,
        common,
        **base,
        converted_candidate_value=converted,
        conversion_factor=factor,
        coefficient_count=candidate.coefficient_count if factor is not None else None,
        original_n=candidate.n if factor is not None else None,
        signed_difference=difference,
        numerical_status=status,
        tolerance=tolerance if request.kind == "exact_target" else None,
        tolerance_unit=reference.value_unit if request.kind == "exact_target" else None,
    )
