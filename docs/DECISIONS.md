# Implementation decisions

## 2026-10-30 — M0 contracts

- Use CPython 3.11, NumPy float64 input and complex128 unitary full FFT, with strict TOML schema v1. The resolved configuration records the sine-generation convention and reference denominator before hashing.
- Accept only complete contiguous bands over `[0, fs/2]`; canonicalize adjacent user edges after a scale-aware validation. Assign bins with exact lower-inclusive comparisons and only the final upper-inclusive comparison.
- Keep the DFT reference as absolute mean-square power. Fractions divide by actual record mean square; zero-power fractions are null with `zero_reference_power`.
- Write deterministic CSV/summary bytes and a final completion manifest through temporary files and atomic replacement. The manifest includes an inventory of source package Python files, `pyproject.toml`, and the environment lock. Generated output directories remain ignored.
- The M0 CLI has only `demo`; later estimators, diagnostics, and study commands remain planned. Numerical artifacts are not committed.
