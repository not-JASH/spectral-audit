# Implementation decisions

## 2026-10-30 — M0 contracts

- Use CPython 3.11, NumPy float64 input and complex128 unitary full FFT, with strict TOML schema v1. The resolved configuration records the sine-generation convention and reference denominator before hashing.
- Accept only complete contiguous bands over `[0, fs/2]`; canonicalize adjacent user edges after a scale-aware validation. Assign bins with exact lower-inclusive comparisons and only the final upper-inclusive comparison.
- Keep the DFT reference as absolute mean-square power. Fractions divide by actual record mean square; zero-power fractions are null with `zero_reference_power`.
- Write deterministic CSV/summary bytes and a final completion manifest through temporary files and atomic replacement. The manifest includes an inventory of source package Python files, `pyproject.toml`, and the environment lock. Generated output directories remain ignored.
- The M0 CLI has only `demo`; later estimators, diagnostics, and study commands remain planned. Numerical artifacts are not committed.

## 2026-10-30 — bounded first M1 Welch increment

- Keep schema-v1 `demo` unchanged. Add strict schema-v2 `measure` for one deterministic tone record, the existing DFT reference, and `welch_mean_density_v1` only. Resolve and hash the complete supported Welch setting family before evaluation.
- Use `finite_record_windowed_band_power` as the Welch measurement kind, with no population target asserted for deterministic tones. The DFT retains `finite_record_fourier`. Label differences `difference_from_dft` and comparison status `descriptive`.
- Use periodic Hann, all complete frames from zero, no padding or detrending, one-sided mean density, window-squared-energy normalization, and discrete-bin integration. Reject bands with no estimator bins. Report omitted samples and zero-taper-weight covered samples separately.
- Preserve M0 fractions as fractions of actual record mean square. Add a separately named fraction of Welch method total. The Welch accounting error compares its spectral total to the independent windowed time-domain identity; its signed difference from unweighted record power is a distinct descriptive field.
- The first implementation and contract were committed as `1248c1b0870fc82458cf9cc9885ada43b69eb288`; clean local runs from that revision are documented in `M1_WELCH_EXAMPLE.md`. This decision does not accept full M1 or make a new research claim.

## 2026-10-30 — bounded Haar DWT increment

- Add strict schema v3 only; v1 demo and v2 DFT/Welch remain strict. Keep the existing exact-band `Measurement` and comparison serializer for Fourier bands. Use a separate validated native group/result type for DWT, with `support_kind = native_scale_group` and no ordinary DFT difference.
- Support `pywt.wavedec(x, wavelet="haar", mode="periodization", level=2)` only for finite real 1D records of length divisible by four. Reject incompatible lengths before PyWavelets can extend them. Retain every coefficient; do not add preprocessing or claim a population target. Record `sum(c²)/n` and `sum(c²)/n_g` as distinct, non-variance quantities.
- Use nominal dyadic Hz ranges only as annotations. A 16 Hz phase change can move native `A2` and `D2` contributions while leaving finite-record DFT band power unchanged; this follows the declared decimated transform, not a demonstrated bug or population bias.
- Package metadata resolves PyWavelets 1.9.0 in the Windows Python 3.11.9 environment. The imported package reports `pywt.__version__ = 1.8.0`; both installed distribution and runtime-reported versions are recorded in v3 manifests rather than silently treating them as the same string.

## 2026-10-30 — bounded db4 boundary audit

- Keep the Haar schema-v3 method and square Parseval checks intact. Add a separate strict boundary-audit configuration and DWT-only CLI path for db4 level 2 at lengths 30, 31, and 32, with a 64-sample response panel.
- Give periodic and periodization distinct method identities. Record the runtime decomposition taps and their hash, and check them against attributed release constants. Use a direct reference with explicit stage indexing, convolution, and downsampling for signed coefficient, extension, and periodic energy checks.
- Normalize every group energy by original record length. Keep raw coefficient sums and counts, coefficient mean squares, original record power, method total, signed discrepancy, and independent accounting residual separate. Do not apply a scalar redundancy correction.
- Treat periodization as the descriptive comparison baseline. Structural extension dependencies describe filter support and inherited dependencies, not measured error. Response formulas are applicable only to compatible periodization; use the explicit finite reference for periodic response rows.
- Retain both installed PyWavelets distribution and imported runtime version strings. The tagged upstream metadata offers a plausible explanation for their difference, without identifying installed files by itself.
