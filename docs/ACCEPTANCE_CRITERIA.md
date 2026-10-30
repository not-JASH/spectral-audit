# Acceptance criteria and verification plan

## 1. Purpose and status

This document defines the evidence required to accept each development milestone of Spectral Audit. It is a plan, not a record of completed implementation or successful tests. Every requirement begins in `not_run` status. A milestone is accepted only after its required checks have recorded evidence against a specific source revision and environment.

Read this document alongside `RESEARCH_PROTOCOL.md`, `ENGINEERING_SPEC.md`, and `ROADMAP.md`. The protocol defines the scientific questions and estimands; the engineering specification defines exact configuration and output schemas. The requirement IDs below provide stable links from implementation tasks and future acceptance records.

| Milestone | Acceptance scope | Required outcome |
| --- | --- | --- |
| M0 | Bootstrap and one unitary-DFT demonstration | Installable CLI, independently checked two-tone powers, reproducible machine-readable outputs |
| M1 | Estimator contracts and STFT, Welch, and DWT implementations | Explicit scaling, preprocessing, boundaries, and denominator semantics for every supported method |
| M2 | Measurement operators and diagnostics | Independently validated quadratic operators, expectation identities, and comparability decisions |
| M3 | Development studies, calibration, and study runner | Reproducible experiments, checked controls, fixed analysis definitions, and a confirmation-ready protocol |
| M4 | Frozen confirmation, report, and release | An auditable confirmation run, appropriately limited conclusions, and a reproducible release |

Later milestones must not expand M0 implicitly. In particular, M0 does not require STFT, Welch, DWT, operator diagnostics, a study runner, or figures.

### Protocol traceability

| Protocol requirements | Principal acceptance checks |
| --- | --- |
| R-05, R-06, R-07: distinct estimands | AC-M1-02, AC-M1-11, AC-M1-12, AC-M1-14, AC-M2-07 |
| R-08: normalization inside `Q` | AC-NUM-01, AC-M2-01, AC-M2-02 |
| R-11: Welch total-power accounting | AC-M1-05, AC-M1-06, AC-M2-01 |
| R-13, R-14: DWT orthogonality and boundaries | AC-M1-08 through AC-M1-12, AC-M2-08 |
| R-15: explicit fractions | AC-NUM-04, AC-M1-03, AC-IO-02 |
| R-17: rejection coverage and valid controls | AC-M1-14, AC-M2-07, AC-M3-06 |
| R-23: sampling uncertainty without stochastic CI gates | AC-NUM-05, AC-M3-03, AC-M3-04, AC-M3-07 |
| R-25, R-26: development and confirmation separation | AC-M3-05, AC-M3-07, AC-M4-01 through AC-M4-04 |
| R-27: exact M0 | AC-M0-01 through AC-M0-14 |
| R-30: reproducible evidence | AC-IO-01 through AC-IO-06, AC-EVID-01 through AC-EVID-03 |

## 2. Quantities and numerical comparison rules

### AC-NUM-01 — State the measured quantity

For a real record `x` of length `N`, sampling frequency `fs`, and explicitly selected fixed preprocessing operator `P`, write `y = P x`. The actual-record mean-square power of the analyzed record is

$$
P_{\mathrm{record}}=\frac{1}{N}\sum_{n=0}^{N-1}y_n^2.
$$

The raw-record and analyzed-record powers must both be available when preprocessing changes them. The denominator used by a reported fraction must be identified explicitly. M0 uses `P = I`, so the two record powers coincide.

The formula above assumes length-preserving preprocessing. If trimming defines a new common analyzed record, identify that record and use its own length consistently. Per-segment processing belongs inside the segment estimator and must not be represented as an undeclared replacement of the common record.

`band_power` has units `input^2`. It is a mean-square contribution, not an amplitude, a power spectral density, a coefficient count, or a fraction. A density has units `input^2/Hz`; integrating or summing it requires the declared frequency-bin measure.

### AC-NUM-02 — Use dimensional absolute and relative tolerances

A scalar numerical comparison passes when

$$
|a-b|\leq \mathrm{atol}+\mathrm{rtol}|b|.
$$

Use both terms. Relative error is unsuitable for a reference value of zero; a fixed dimensional absolute tolerance can conceal an error in a very small signal.

For the float64 M0 fixture, use `atol = 1e-12 input^2` and `rtol = 1e-12` for powers, and `atol = rtol = 1e-12` for dimensionless fractions. These thresholds allow accumulated binary64 rounding and trigonometric sample-generation error while remaining far below errors caused by missing endpoint factors or a missing factor of `N`. Machine epsilon is approximately `2.22e-16`; the M0 record contains only 256 samples.

For a fixture obtained by multiplying its signal by a known factor `a`, multiply the power comparison's dimensional `atol` by `a^2`; keep `rtol` unchanged. Include at least `a = 1e-6` and `a = 1e6`. Do not retain a unit-scale absolute tolerance for these checks.

For small, well-conditioned matrix and reconstruction tests, start with `rtol = 1e-11` and `atol = 1e-12` in the fixture's declared natural units. Report the maximum absolute residual and a scale-normalized residual. If a different bound is required, document its dependence on dimension, conditioning, and operation count before accepting the test. Statistical uncertainty and model discrepancy must never be hidden inside a floating-point tolerance.

### AC-NUM-03 — Keep independent oracles independent

At least one correctness oracle for each numerical component must not reuse the production normalization, band-mask, endpoint-weight, or aggregation helper that it is testing. Suitable oracles include analytic sinusoid powers, an explicit small DFT matrix, manual Haar averages and differences, direct time-domain sums, and independently assembled quadratic forms.

A second call to the same library routine with the same wrappers is not independent evidence. Agreement with a reference library is useful additional evidence, provided every option is set explicitly.

### AC-NUM-04 — Preserve zero and near-zero semantics

For an exactly zero analyzed record, absolute powers are zero and every fraction with a zero denominator is undefined. Represent an undefined value using the schema's nullable numeric representation and an explicit status/reason. Do not emit a numeric zero fraction, infinity, a JSON `NaN`, or a plausible-looking value obtained by adding an epsilon to the denominator.

An exactly zero band with a positive denominator has a valid zero fraction. A small but representable nonzero signal must retain scale-invariant fractions. Any optional near-zero classification must be declared separately, with its threshold and units recorded; it must not silently change the estimator.

### AC-NUM-05 — Keep numerical tests deterministic

Ordinary CI verifies identities, reference cases, schemas, and deterministic control flow. It must not pass or fail according to whether a fresh Monte Carlo p-value crosses a significance threshold. Statistical studies have a separate execution and review process in Sections 6–7.

## 3. M0: exact bootstrap acceptance

### Fixed demonstration contract

The demonstration configuration is `configs/m0_tones.toml`. It resolves to:

- `fs = 128 Hz`, `N = 256`, and `t_n = n / fs` for `n = 0, ..., 255`;
- `x_n = sin(2 pi 8 t_n) + 0.5 sin(2 pi 24 t_n)`;
- no noise, no mean removal, no window, and no zero padding;
- a unitary DFT;
- bands `[0, 16) Hz`, `[16, 32) Hz`, and `[32, 64] Hz`, with the Nyquist frequency included only in the final band.

The bin spacing is `0.5 Hz`, so both tones are coherent with the record. Their mean-square powers follow directly from their amplitudes and orthogonality.

| Quantity | Analytic reference |
| --- | ---: |
| First band power | 0.5 |
| Second band power | 0.125 |
| Third band power | 0 |
| Actual-record total power | 0.625 |
| First record-power fraction | 0.8 |
| Second record-power fraction | 0.2 |
| Third record-power fraction | 0 |

The zero reference is a tolerance comparison, not a requirement to round a small computed leakage value to literal zero in output.

### M0 requirement table

| ID | Verification | Acceptance evidence |
| --- | --- | --- |
| AC-M0-01 | Create a clean Python 3.11+ virtual environment and install the package in editable mode with its development dependencies. | Installation succeeds without manually editing import paths; package import and console entry point resolve to this checkout. |
| AC-M0-02 | Run `spectral-audit --help` and `spectral-audit --version`. | Both exit successfully; help documents the implemented demo invocation; version is `0.0.1.dev0`. |
| AC-M0-03 | Run the exact demo command below. | It exits successfully and produces `band_powers.csv`, `summary.json`, and `manifest.json` in the requested output directory. No PNG is required. |
| AC-M0-04 | Compare all three band powers and fractions to the analytic table. | All pass AC-NUM-02; total power is also checked by a separate direct time-domain sum. |
| AC-M0-05 | Use an independent one-sided calculation to check the production full-DFT result and selected bands. | The oracle spectrum sums to actual-record power; the three bands cover every retained frequency exactly once; their sum also equals actual-record power. No additional spectrum-output API is required. |
| AC-M0-06 | Apply known amplitude scale factors to the core numerical routine. | Powers scale by amplitude squared, fractions remain unchanged, and dimensional tolerances scale as specified. |
| AC-M0-07 | Test constant, interior-bin, and Nyquist fixtures. | DC and even-length Nyquist are counted once; positive interior bins receive their conjugate-pair multiplicity. |
| AC-M0-08 | Test an odd-length real record in the core routine. | There is no invented Nyquist bin; the highest retained positive frequency receives multiplicity two. |
| AC-M0-09 | Test bins exactly at 16 Hz and 32 Hz, plus a Nyquist cosine. | Boundary-bin assignment follows the half-open convention and final closed upper endpoint. Use a cosine or `(-1)^n` at Nyquist; a sampled Nyquist sine is not a nonzero reference. |
| AC-M0-10 | Test zero input and a very small nonzero scaled input. | Zero-denominator fractions are undefined with a reason; small nonzero input is not converted to zero by a generic epsilon rule. |
| AC-M0-11 | Exercise meaningful invalid inputs and configurations. | The validation cases in Section 4.5 fail clearly before a successful run manifest is written. |
| AC-M0-12 | Repeat the demo in two new directories under the same recorded environment. | Numerical artifacts are identical under the deterministic serialization contract; only explicitly separated invocation metadata may differ. |
| AC-M0-13 | Recompute output digests independently. | They match the completed manifest; source/configuration provenance is present and truthful. |
| AC-M0-14 | Run the smoke tests and lint checks. | Tests exercising normalization, analytic references, input validation, and output reproducibility pass; lint succeeds. No test exists solely to mirror a constant or implementation branch. |

Suggested POSIX verification sequence after the bootstrap has been implemented:

```bash
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -r requirements-lock.txt
python -m pip install --no-deps -e '.[dev]'
spectral-audit --help
spectral-audit --version
spectral-audit demo --config configs/m0_tones.toml --out results/verification/m0_a
spectral-audit demo --config configs/m0_tones.toml --out results/verification/m0_b
python -m pytest -q
python -m ruff check .
```

This sequence assumes bootstrap has already created the tested environment lock. The paths are examples of fresh output directories under ignored `results/`. A smoke-runtime target may be documented for development convenience, but acceptance must not depend on an unexplained machine-specific wall-clock cutoff.

### Unitary DFT oracle

M0 production uses the full unitary FFT and absolute-frequency masks specified in `ENGINEERING_SPEC.md`. The rFFT route below is an independent test oracle, not an additional production implementation requirement.

For `X = rfft(y, norm="ortho")`, the bin power is

$$
p_k=\frac{m_k|X_k|^2}{N},
\qquad
m_k=\begin{cases}
1 & k=0,\\
1 & N\text{ even and }k=N/2,\\
2 & \text{otherwise}.
\end{cases}
$$

For at least one small even and one small odd length, construct the full complex DFT explicitly from its exponential definition and compare both coefficients and band powers. The oracle must independently fold negative-frequency power into positive frequencies. NumPy's transform conventions are documented in reference [1].

## 4. M1: estimator contracts and implementations

### 4.1 Preprocessing and targets

**AC-M1-01 — Fixed mean-removal operators.** Verify `P = I` for no mean removal and `P = I - 11^T/N` for global sample-mean removal. Check symmetry, idempotence, and removal of a constant record. Show that a constant offset changes the no-removal result and does not change the globally demeaned result, within the dimensional tolerance. The sample mean is data-dependent, but this complete mapping is a fixed linear operator for a fixed record length.

Segment-wise mean removal is a different mapping. Record every segment's selection and centering operator; do not equate it with global mean removal. Do not inherit a library's default detrending setting. For a comparison claiming identical preprocessing, the tests must verify identical effective operators.

**AC-M1-02 — Target labels.** Each result identifies whether it describes a finite-record DFT-band quantity, a native transform-scale quantity, or an estimate of an integrated population spectrum. These targets must remain distinguishable in tables and plots. Even the finite-record DFT's expectation can differ from an ideal population-spectrum integral because of finite-record leakage.

**AC-M1-03 — Denominators.** `record_power_fraction` divides the reported band power by the explicitly identified actual-record power. A method-total fraction, if supported later, has a different field and denominator label. It must never overwrite or silently substitute for the record-power fraction. For methods whose total differs from record power, record-power fractions need not sum to one.

### 4.2 STFT and Welch

**AC-M1-04 — Explicit segment calculation.** For a small record, compute segments, preprocessing, window multiplication, DFTs, one-sided multiplicities, and aggregation in a direct reference implementation. Compare it to the production result. Test both a complete-frame case and a boundary/tail case.

**AC-M1-05 — PSD scaling.** Let `g_jk` be the unnormalized DFT of a windowed, processed segment, `U = sum(w^2)`, and `Nfft` its transform length. For the declared density convention, the direct oracle is

$$
S_{jk}=\frac{m_k|g_{jk}|^2}{f_s U},
\qquad
\Delta f=f_s/N_{\mathrm{fft}}.
$$

Its discrete integrated total is `sum(S_jk * delta_f)`, which equals the window-weighted segment mean square. Averaging these quantities over segments generally produces a taper- and overlap-weighted total, not the unweighted actual-record power. Verify both the appropriate identity and at least one nonstationary example where these totals differ.

A discrete-bin sum must not accidentally be replaced by trapezoidal endpoint weighting. A continuous-spectrum quadrature is a separate calculation. SciPy's Welch density and spectrum scalings differ; choose one explicitly and verify the conversion rather than treating their units as interchangeable [3].

**AC-M1-06 — Window and overlap accounting.** Record and verify the actual window samples, symmetry convention, length, hop, overlap, start positions, padded samples, discarded samples, and averaging weights. For a no-extension example, check the coverage weights `h[n] = sum_j w_j[n]^2` against the sum of frame energies. Where extension changes the mapping, use its actual linear operator.

Test at least one changed hop and one changed window. Reconstructability or an inverse-STFT round trip alone does not establish power preservation. Boundary frames and negative-time frame indices require explicit treatment when the selected API includes them [4].

**AC-M1-07 — Zero padding.** Changing `Nfft` while retaining the same data and window must preserve the correctly integrated total. The bin grid and band allocation may change; zero padding must not be described as adding independent observations or improving the record's underlying resolving power.

### 4.3 DWT and boundary accounting

**AC-M1-08 — Independent Haar oracle.** For a short even-length record, calculate normalized pairwise averages and differences directly. Verify coefficients, reconstruction, total coefficient energy, and the contribution `sum(c_j^2)/N` from each retained coefficient group.

**AC-M1-09 — Periodization is not periodic extension.** Tests must use these exact mode names distinctly. For an orthogonal wavelet and compatible length divisible by `2^J`, verify the claimed periodized orthonormal transform's coefficient count and Parseval identity. Also exercise an odd length or another incompatible case, recording the extension and actual coefficient count rather than assuming the same identity.

PyWavelets documents `periodization` as yielding the smallest coefficient count and extending odd inputs to even length; `periodic` is a separate extension mode [2]. A test with a filter longer than Haar must demonstrate that the two settings have distinguishable boundary/coefficient behavior.

**AC-M1-10 — Redundancy and boundaries.** For each supported boundary mode, record input length, effective extended length where applicable, group lengths, total coefficient count, retained/trimmed coefficients, and the declared power accounting. Check impulses at an edge and in the interior, plus a constant or ramp. If a transform is redundant, do not restore apparent Parseval equality by dividing all energies by its coefficient-count ratio. Validate its actual frame/operator accounting.

**AC-M1-11 — Mean-square contribution versus coefficient second moment.** `sum(c_j^2)/N` is the declared record-power contribution in the orthonormal setting; `sum(c_j^2)/len(c_j)` is a different quantity. Neither is automatically the coefficient variance without the relevant centering convention. Include a fixture that makes the difference visible.

**AC-M1-12 — Nominal scale bands.** Labels such as `A2`, `D2`, and `D1` may carry nominal dyadic frequency ranges, but must not be reported as ideal Fourier bandpass equivalence. Use a frequency sweep or independent filter-response calculation to verify transition-region behavior. Test that the comparison layer declines unsupported hard-band equivalence and accepts genuinely matched definitions.

### 4.4 Cross-method checks

**AC-M1-13 — Scaling and offset controls.** Apply amplitude scaling to every implemented estimator and check the square law. Test offset behavior separately for each declared preprocessing choice. Do not require phase or shift invariance from a boundary-sensitive or decimated representation unless its contract establishes that property.

**AC-M1-14 — Native and common-estimand reports.** A native-estimator table may compare labeled numerical outputs without asserting equality. A common-estimand comparison must declare a shared target, the mapping from each method to that target, and any expected estimator bias. The implementation must include both valid comparison controls and deliberately mismatched controls; a gate that always accepts or always refuses cannot pass.

### 4.5 Invalid-input matrix

**AC-M1-15 — Validate the contract, not incidental library behavior.** The applicable checks begin in M0 and expand with implemented methods.

| Input class | Required behavior |
| --- | --- |
| Empty, non-vector, nonnumeric, nonfinite, or unsupported complex record | Reject with the input field and reason; do not silently flatten, discard imaginary parts, or drop samples. |
| Nonpositive/nonfinite sampling frequency; invalid length; Boolean supplied where an integer parameter is required | Reject before computation. |
| Reversed, zero-width, negative, out-of-Nyquist, overlapping, unsorted, or ambiguously labeled bands | Reject under the declared partition contract. Gaps require an explicitly supported partial-coverage mode; M0 requires its complete partition. |
| Frequency exactly on a shared boundary | Assign it once according to the declared interval convention. |
| Invalid window length, hop, overlap, zero-energy window, or unsupported `Nfft` | Reject; do not silently shorten segments or change the configuration. |
| Unsupported wavelet, mode, level, or length combination | Reject or apply only the explicitly selected extension policy; never relabel a fallback as the requested transform. |
| Unknown configuration field or unsupported method | Reject clearly; do not emit fabricated placeholder results. |
| Numeric overflow or nonfinite result from finite but extreme inputs | Stop with a numerical-range error or the specification's explicit failure status; do not emit a successful finite-looking summary. |
| Unwritable output path, invalid config path, or output collision | Follow the documented policy and return a nonzero exit code; preserve existing data and do not leave a completed success manifest. |

## 5. M2: operators and diagnostic validity

### AC-M2-01 — Quadratic-form convention

Each fixed linear analysis with fixed quadratic aggregation must expose a real symmetric measurement operator `Q_b` satisfying

$$
p_b(x)=x^TQ_bx.
$$

With analysis map `A`, fixed preprocessing `P`, band weights `W_b`, and the record-normalized convention, this can be written

$$
Q_b=\frac{1}{N}\operatorname{Re}\!\left(P^T A^*W_bAP\right),
$$

where `A` must include any method-specific rescaling. `Q_b` contains all normalization factors; do not divide its quadratic form by `N` again. For native Welch quantities, the assembled operator must reproduce Welch's declared window/segment scaling rather than forcing its total to equal record power.

Verify powers on basis vectors, mixtures of basis vectors, and at least one nonsparse record. Cross terms require mixture tests; diagonal-only checks are insufficient.

### AC-M2-02 — Independent operator construction

For small problems, compare the production operator to an independently assembled DFT, direct Haar/filter-bank, or explicit segment-window-DFT operator. Probing the production estimator can be a useful secondary method, but is not the only oracle. Check shape, symmetry, finite values, and positive semidefiniteness within a documented scale-aware numerical tolerance.

For a complete orthonormal partition with preprocessing `P`, verify `sum_b Q_b = P^T P / N`. Do not impose this equation on a redundant or window-weighted estimator that does not have that contract; check its correct total operator instead.

### AC-M2-03 — Covariance and nonzero-mean expectation

For a random real record with mean `mu` and covariance `Sigma`, verify

$$
\mathbb E[p_b]=\operatorname{tr}(Q_b\Sigma)+\mu^TQ_b\mu.
$$

Use a nonzero-mean, colored-covariance fixture as well as white noise. Test preprocessing through the operator; do not subtract the mean in the samples while leaving the uncentered `Q_b` in the reference calculation.

Reference covariances must have matching dimensions and be real symmetric positive semidefinite. Include a legitimate rank-deficient or zero-covariance case; do not require positive definiteness unnecessarily. Invalid covariance inputs must be diagnosed rather than silently replaced by a nearby matrix.

A deterministic expectation oracle is available. For `Sigma = L L^T` in dimension `N`, evaluate the actual estimator at the `2N` records `mu +/- sqrt(N) L e_i` with equal weights. These records have exactly the specified first two moments, so the average of any fixed quadratic estimator must equal the formula above, up to numerical error. This provides a nonflaky test that exercises the estimator and its operator together.

### AC-M2-04 — Trace calibration has a declared scope

For zero-mean white noise with variance `sigma^2`, verify the specialization `E[p_b] = sigma^2 tr(Q_b)`. Add a colored-covariance counterexample demonstrating why white-noise calibration is not automatically universal. If a calibration depends on the assumed covariance, record that assumption and its parameters.

An expectation ratio is not generally the expectation of a ratio. The quadratic identity applies to a power numerator, not automatically to a record-power fraction with a random denominator. Ratio statistics need their own stated analysis.

### AC-M2-05 — Fixed versus adaptive operations

A fixed-operator claim requires fixed preprocessing, windows, band definitions, and aggregation weights for that run. Median aggregation, data-dependent thresholding, and adaptive selection do not automatically have a single fixed `Q_b`. Unsupported diagnostics must be explicitly unavailable, with a null value and reason, rather than computed using a convenient but incorrect linear surrogate.

### AC-M2-06 — Diagnostic applicability

Every diagnostic row identifies its target, assumptions, units, denominator, and status. A diagnostic that is not implemented or not applicable has `null` as its numeric value and a distinct status/reason. Zero is reserved for a computed zero. Include tests that preserve this distinction through JSON, CSV, aggregation, and report generation.

### AC-M2-07 — Meaningful comparability decisions

Create a small reviewed matrix of cases that should and should not qualify for each declared comparison claim. It must include matched operators, different preprocessing, different denominator definitions, finite-record versus population targets, and nominal DWT bands versus ideal DFT bands. Check accepted-valid controls as carefully as rejected-invalid controls.

### AC-M2-08 — Finite-record boundaries remain visible

Operator-based diagnostics must use the actual record length, extension rules, frame placement, trimming, and coefficients retained in the calculation. Verify a boundary-sensitive fixture against the explicit finite matrix. Replacing the real operator with an infinite-length filter response is permitted only as a separately labeled approximation whose error is evaluated.

### AC-M2-09 — Bounded operator inspection

Verify the engineering specification's default dense-operator size cap before large allocations occur. An explicit override must retain a declared memory budget. Matrix-free or iterative diagnostics must distinguish an estimate from a certified bound; an approximate norm estimate cannot silently inherit the guarantee of an exact operator-norm inequality.

## 6. M3: development studies and statistical verification

**AC-M3-01 — Freeze the development experiment definition.** Before each study, record the question, estimand, scenario grid, preprocessing, methods, calibration rules, metrics, aggregation, exclusion rules, seed schedule, and planned number of independent replicates. Preserve amended definitions as new versions rather than silently changing a completed study.

**AC-M3-02 — Separate source variation from measurement effects.** Use controls with known sinusoidal content, offsets, bursts, and boundary placement, followed by declared stochastic processes. For stationary AR-type fixtures, use stationary initialization or explicitly quantify and exclude burn-in effects. Keep population PSD integrals, finite-record reference powers, and method expectations in separate fields.

**AC-M3-03 — Pair method comparisons correctly.** Apply compared methods to the same realized record when the estimand permits paired comparison. Seeds are assigned to scenarios and replicates independently of method ordering. Reordering methods or parallel workers must not change the signal drawn for a replicate. Independent records, overlapping frames, and correlated frequency bins are different observational units; do not count each frame or coefficient as an independent replicate.

**AC-M3-04 — Quantify Monte Carlo error.** Report replicate counts and uncertainty for estimated means, biases, or paired differences. For real Gaussian records and symmetric `Q`, the optional variance oracle is

$$
\operatorname{Var}(x^TQx)=2\operatorname{tr}(Q\Sigma Q\Sigma)
+4\mu^TQ\Sigma Q\mu.
$$

It may guide sample-size and Monte Carlo-error calculations under its assumptions. A discrepancy outside a study's planned error bounds triggers investigation; it is not a flaky unit-test gate. Deterministic CI instead checks the analysis formulas on small fixtures and verifies correct handling of the replicate units.

**AC-M3-05 — Calibration does not use confirmation outcomes.** Fit or choose calibration constants, decision thresholds, numerical tolerances, band choices, and reporting rules using analytic reasoning or development records only. Save the resulting frozen specification. Do not select a threshold to obtain a desired rejection or coverage rate on the confirmation sample.

**AC-M3-06 — Check both usefulness and restraint.** Diagnostic evaluation includes accepted-valid and rejected-invalid controls with independently defined labels. Report false acceptance, false rejection, coverage, and unresolved cases where relevant. An always-refuse diagnostic must be exposed by poor valid-case acceptance; an always-accept diagnostic must be exposed by mismatch controls. Do not turn every ambiguous case into a favorable exclusion.

**AC-M3-07 — Prespecify inferential claims.** If the study will test hypotheses, state effect sizes of interest, sampling units, confidence-interval or testing procedures, and treatment of multiple comparisons before confirmation. Power calculations or simulation-based planning belong to development. Exploratory patterns may be reported, but are labeled exploratory and do not acquire confirmatory status through retrospective threshold selection.

**AC-M3-08 — Verify the runner.** Small deterministic fixtures test scenario enumeration, seed assignment, resumability, duplicate-run detection, interrupted runs, and aggregation. Resuming a partially completed study must preserve completed valid records and identify missing/failed records explicitly. A study summary must not silently average only the successful cases when failures are informative.

## 7. M4: confirmation and release acceptance

| ID | Requirement | Required evidence |
| --- | --- | --- |
| AC-M4-01 | Freeze source, configuration, calibration, metrics, and analysis before confirmation. | Recorded hashes/revisions and a confirmation manifest that identifies the frozen inputs. |
| AC-M4-02 | Use new confirmation realizations and withheld configurations appropriate to the claimed generalization. | Documented separation from development, explicit interpolation/extrapolation domains, and an account of any accidental overlap. New seeds alone do not establish performance on new signal regimes. |
| AC-M4-03 | Preserve unfavorable and inconclusive results. | Complete scenario accounting, uncertainty, failure counts, and deviations; no undocumented exclusions or reruns selected for their outcomes. |
| AC-M4-04 | Treat substantive post-confirmation changes as a new study version. | The original result remains available; new calibration or hypotheses receive a new confirmation design. |
| AC-M4-05 | Produce a scientifically limited report. | Claims distinguish native quantities, common targets, finite-record effects, boundary effects, and population inference. No universal energy-preservation or hard-band-equivalence claim is inferred from a few examples. |
| AC-M4-06 | Reproduce the release from a clean environment. | Installation, M0 smoke demonstration, selected estimator/operator checks, and a small released study reproduce from the documented commands. Larger results have exact run manifests and a declared compute requirement. |

Release is compatible with a negative or inconclusive scientific result. Acceptance concerns the correctness and auditability of the investigation, not whether a preferred method wins.

## 8. File, CLI, and reproducibility contracts

### AC-IO-01 — Exact implemented interface

The M0 interface is:

```text
spectral-audit --help
spectral-audit --version
spectral-audit demo --config configs/m0_tones.toml --out <dir>
```

Help text and examples must distinguish implemented functionality from future functionality. Invalid use returns a nonzero status and a useful diagnostic. Additional commands are accepted only with their own documented contracts and tests.

### AC-IO-02 — Result semantics and schemas

Validate machine-readable outputs against their documented schema/version. Check required fields, units, row identities, band intervals, preprocessing, estimator identity, and denominator identity. M0's `band_powers.csv` includes absolute `band_power` and `record_power_fraction`; it must not normalize by the sum of a method's selected bands implicitly.

The three M0 output files must agree on resolved parameters and numerical values. Unknown or unavailable diagnostic values remain distinguishable from computed zeros. JSON must be standards-compliant; nullable values use JSON `null`, not nonstandard `NaN` tokens.

### AC-IO-03 — Provenance manifest

The engineering schema may choose field names, but the completed manifest must contain:

- schema and package versions;
- the fully resolved configuration, including defaults, and its digest;
- the input definition or input-file digests, including the deterministic fixture definition and generation convention;
- a source digest over a declared source-file set, and a Git commit plus dirty state when available;
- a truthful `unversioned` state when no Git revision exists, rather than an invented commit;
- Python, numerical-library, and platform/environment versions sufficient to interpret a numerical rerun;
- seeds and RNG identification when randomness is actually used; M0 must not suggest random data were generated;
- the estimator's sampling, normalization, preprocessing, endpoint, boundary, and denominator choices;
- output paths or artifact identities and independently recomputable output digests;
- run status and separately identifiable invocation metadata such as timestamps, duration, and output location.

If a dirty tree is permitted, a commit identifier alone is insufficient: the source digest must identify the actual content used. State which files the digest includes. Do not use a fabricated clean state.

### AC-IO-04 — Determinism boundary

Within an unchanged recorded environment, repeated M0 runs must produce byte-identical deterministic numerical files under the chosen stable ordering and serialization. Invocation timestamps, durations, absolute output paths, and similar metadata are kept outside those deterministic values.

Across supported numerical environments, compare parsed numerical results using declared tolerances; byte identity of floating-point text is not promised across arbitrary library/platform versions. Hashes identify the concrete artifacts that were produced, not a claim of universal bitwise numerical equivalence.

### AC-IO-05 — Digest and completion integrity

Verify digests using a separate reading of the completed files. Do not define the manifest's integrity by a recursively self-referential hash of itself. Numerical outputs and the final manifest must have an unambiguous completion order so an interrupted run cannot masquerade as successful. Test one interrupted or failed-write case when this output mechanism is implemented.

### AC-IO-06 — Report traceability

Every reported table and figure in later milestones identifies its source run/configuration and can be regenerated from recorded results. A plotted fraction states its denominator. A plotted density states its integration convention. Labels must not conceal differences in estimands, extension, or retained coefficients.

## 9. Acceptance records and review

**AC-EVID-01 — Record execution honestly.** For each required check, a future acceptance record contains:

| Field | Required content |
| --- | --- |
| Requirement ID and milestone | For example, `AC-M0-04`, `M0` |
| Status | `not_run`, `pass`, `fail`, `blocked`, or `deferred` |
| Source/environment identity | Revision or truthful unversioned state, source digest, dependency environment |
| Command or procedure | Exact reproducible action, including configuration |
| Expected result and tolerance | Oracle, units, absolute/relative tolerances, and any assumptions |
| Observed result | Actual numbers, maximum residuals, exit status, or validation error |
| Evidence artifacts | Test log, manifest, result file, and digests where applicable |
| Review and deviations | Reviewer/date when review occurs; explanation and disposition of any deviation |

The initial handoff must not contain fabricated successful runs, elapsed work, or acceptance evidence. `blocked` and `deferred` are informative states, not synonyms for passing. A milestone with an unmet required criterion remains unaccepted unless its scope is explicitly revised and recorded.

**AC-EVID-02 — Review failures by meaning.** Before changing a tolerance or expected value, determine whether the discrepancy comes from a code error, a mistaken oracle, a changed estimand, a boundary convention, numerical conditioning, or stochastic uncertainty. Preserve the original failure and the reason for the correction. Updating expected values from the implementation's output alone is not validation.

**AC-EVID-03 — Stop at sufficient evidence.** Run the smallest independent cases that resolve the actual risk, then the required milestone suite. Broader tests are warranted by a concrete remaining uncertainty, a changed numerical contract, or the confirmation design. Repeated successful reruns do not compensate for a missing oracle.

## References

1. NumPy, *Discrete Fourier Transform*: transform definitions, normalization, and real-input conventions. https://numpy.org/doc/stable/reference/routines.fft.html
2. PyWavelets, *Signal extension modes*: distinctions among boundary extensions and periodization. https://pywavelets.readthedocs.io/en/latest/ref/signal-extension-modes.html
3. SciPy, *welch*: segment averaging, detrending, one-sided conventions, and density/spectrum scaling. https://docs.scipy.org/doc/scipy/reference/generated/scipy.signal.welch.html
4. SciPy, *ShortTimeFFT*: window/hop conventions, scaling, and finite-record boundary frames. https://docs.scipy.org/doc/scipy/reference/generated/scipy.signal.ShortTimeFFT.html

These links document library behavior; the project must record the actual installed versions rather than rely on the moving `stable` or `latest` documentation labels.
