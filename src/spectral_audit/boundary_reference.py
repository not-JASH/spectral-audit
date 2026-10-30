"""Direct db4 analysis reference, independent of PyWavelets transform helpers.

Taps and indexing follow PyWavelets v1.9.0 wavelets_coeffs.template.h,
wavelets.c, and convolution.template.c (links in M1_BOUNDARY_EXAMPLE.md).
"""

import numpy as np

DB4_LOW = (
    -0.010597401785069032,
    0.0328830116668852,
    0.030841381835560764,
    -0.18703481171909309,
    -0.027983769416859854,
    0.6308807679298589,
    0.7148465705529157,
    0.2303778133088965,
)
DB4_HIGH = tuple((-1) ** (j + 1) * DB4_LOW[7 - j] for j in range(8))


def stage(x: np.ndarray, mode: str, inherited: tuple[bool, ...] | None = None):
    """Explicit extension, convolution, alignment, and decimation for one stage."""
    if mode not in {"periodic", "periodization"}:
        raise ValueError("unsupported db4 mode")
    m = len(x)
    if inherited is None:
        inherited = (False,) * m
    if len(inherited) != m:
        raise ValueError("dependency length mismatch")
    duplicated = mode == "periodization" and bool(m % 2)
    even = np.append(x, x[-1]) if duplicated else x
    support = inherited + ((True,) if duplicated else ())
    width = len(even)
    count = width // 2 if mode == "periodization" else (m + 7) // 2
    offset = 4 if mode == "periodization" else 1
    outputs = []
    flags = []
    for filt in (DB4_LOW, DB4_HIGH):
        values = []
        dependencies = []
        for k in range(count):
            raw = [2 * k + offset - j for j in range(8)]
            indices = [r % width for r in raw]
            values.append(sum(f * even[i] for f, i in zip(filt, indices, strict=True)))
            dependencies.append(
                any(
                    (r < 0 or r >= width or support[i]) and filt[j] != 0
                    for j, (r, i) in enumerate(zip(raw, indices, strict=True))
                )
            )
        outputs.append(np.asarray(values, dtype=float))
        flags.append(tuple(dependencies))
    ledger = {
        "stage_input_length": m,
        "extension_rule": "duplicate_stage_final_value_then_cyclic_index"
        if duplicated
        else "cyclic_index_on_stage_input",
        "duplicated": duplicated,
        "duplicate_source_index": m - 1 if duplicated else None,
        "analysis_filter_length": 8,
        "downsampling_stride": 2,
        "alignment_offset": offset,
        "approximation_output_length": count,
        "detail_output_length": count,
        "retained_coefficient_policy": "all",
        "structural_extension_dependency_counts": {
            "approximation": sum(flags[0]),
            "detail": sum(flags[1]),
        },
    }
    return outputs[0], outputs[1], flags[0], flags[1], ledger


def decompose(x: np.ndarray, mode: str):
    a1, d1, a1_flags, d1_flags, first = stage(x, mode)
    a2, d2, a2_flags, d2_flags, second = stage(a1, mode, a1_flags)
    first["level"] = 1
    first["stage_input_kind"] = "original_record"
    second["level"] = 2
    second["stage_input_kind"] = "level_1_approximation"
    second["duplicate_source_stage"] = "level_1_approximation" if second["duplicated"] else None
    first["duplicate_source_stage"] = "original_record" if first["duplicated"] else None
    return (a2, d2, d1), a1, (first, second), (a2_flags, d2_flags, d1_flags)
