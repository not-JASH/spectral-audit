# Research protocol: spectral measurement comparability

**Status:** prospective specification. No comparative experiment, empirical finding, or novelty claim is asserted here. The initial repository milestone is M0 only. Mathematical expectations below are reference values to be checked by the future implementation.

**Purpose:** determine when different spectral measurements of the same finite signal answer the same question, explain their disagreement when they do not, and test whether explicit measurement contracts and operator diagnostics prevent misleading comparisons.

The study concerns uniformly sampled, real, one-dimensional signals and classical numerical signal processing on a CPU. It is independently useful as a measurement and reproducibility study. It does not require an application-specific dataset. Bibliographic foundations and the outstanding novelty audit are in [REFERENCES.md](REFERENCES.md); implementation acceptance is specified in [ACCEPTANCE_CRITERIA.md](ACCEPTANCE_CRITERIA.md).

## 1. Research requirements and terminology

**R-01 — Declared measurement.** Every result must identify the input record, sampling frequency, preprocessing, target estimand, transform configuration, boundary convention, normalization, and frequency or scale support. A shared label such as “low frequency” is insufficient evidence of comparability.

**R-02 — Units.** The primary outputs are absolute **mean-square band powers**, in input-units squared. They are not the unnormalized discrete energy $x^\mathsf{T}x$, physical energy integrated over time, a power spectral density, or an amplitude. A PSD has units input-units squared per hertz. Report names must preserve these distinctions.

**R-03 — Signal domain.** A record is $x=(x_0,\ldots,x_{n-1})^\mathsf{T}\in\mathbb R^n$, sampled at $t_j=j/f_s$, with $f_s>0$. Reject nonfinite values, unsupported dimensionality, irregular sampling, and missing samples; do not silently interpolate. Record the actual sample indices when comparing subsets.

**R-04 — Preprocessing is part of the estimator.** No demeaning is used in M0. Later fixed mean removal, detrending, trimming, and extension must be explicit linear maps. Constant detrending is not an innocuous library default. If preprocessing changes between methods, label the comparison accordingly or refuse it. Data-adaptive processing is outside the fixed-quadratic analysis unless separately specified.

For the unprocessed record, write

$$
P_x=\frac{x^\mathsf{T}x}{n}.
$$

If a common processed record replaces $x$, name that record and use its own length consistently. Per-segment preprocessing belongs inside the corresponding segment operator and generally does not define one common processed record.

## 2. Three different estimands

### 2.1 Finite-record Fourier projection

Let $F_n$ be the unitary DFT matrix, with entries $n^{-1/2}\exp(-2\pi i kj/n)$. For a one-sided interval $B\subseteq[0,f_s/2]$, let $D_B$ select all two-sided DFT bins whose absolute physical frequency lies in $B$. Include conjugate pairs; count DC and, for even $n$, Nyquist once.

Define

$$
P_B=F_n^*D_BF_n,\qquad
p_B^{\mathrm{DFT}}(x)=\frac{x^\mathsf{T}P_Bx}{n}.
$$

The symmetric bin selection makes the quadratic form real. Its operator is an orthogonal projector before division by $n$. If the bands partition every bin exactly once, their powers sum to $P_x$.

**R-05 — Finite-record reference.** This is an exact measurement of a declared periodic finite-record representation. It is the M0 reference. It is not automatically the physical spectrum of an infinite process or a universally superior estimator.

For an unnormalized real FFT, the equivalent formula is

$$
p_B^{\mathrm{DFT}}=\frac{1}{n^2}\sum_{k:f_k\in B}d_k|X_k|^2,
$$

where $d_k=2$ at interior positive frequencies and $d_k=1$ at DC and an existing Nyquist bin. Odd lengths have no Nyquist bin. Interior band edges are lower-inclusive and upper-exclusive; only the final interval includes $f_s/2$.

### 2.2 Population spectral power

For a zero-mean second-order stationary process with two-sided PSD $S(f)$, define

$$
\theta_B=\int_{\{f:\,|f|\in B\}}S(f)\,df,
\qquad f\in[-f_s/2,f_s/2].
$$

**R-06 — Population target.** Population bias means $\mathbb E[\widehat p_B]-\theta_B$. Finite-record disagreement means $\widehat p_B(x)-p_B^{\mathrm{DFT}}(x)$. Store and analyze these separately. Even the finite-record DFT measurement can have a biased expectation relative to $\theta_B$ because its effective response has finite-record leakage. Deterministic means and spectral lines require their own explicit treatment, rather than being silently folded into a continuous zero-mean PSD.

### 2.3 Native wavelet-scale quantities

For a verified square orthonormal DWT matrix $W$, let $C_j$ select the $n_j$ coefficients in a detail or approximation group. The record-normalized contribution is

$$
p_j^{\mathrm{DWT}}=\frac{\|C_jWx\|_2^2}{n}.
$$

The coefficient mean square is instead $v_j=\|C_jWx\|_2^2/n_j$, so $p_j^{\mathrm{DWT}}=(n_j/n)v_j$. Calling $v_j$ a variance additionally requires a justified coefficient-mean convention. Under a stationary filtering model, the corresponding population coefficient variance involves an integral of the PSD against the squared wavelet-filter response, not an ideal rectangular band [P1995].

**R-07 — No universal scale conversion.** Native wavelet-scale variance, record-normalized wavelet contribution, finite-record Fourier band power, and population hard-band power must have different estimand identifiers. Nominal dyadic intervals are explanatory labels. Assigning all coefficients at a level to a hard Fourier interval does not make the measurements equal.

## 3. Fixed linear measurements as quadratic forms

Let $A_m$ contain all fixed linear analysis steps for method $m$, and let $G_{m,b}$ contain nonnegative coefficient weights and the required method normalization. Define

$$
\widehat p_{m,b}(x)=x^\mathsf{T}Q_{m,b}x,
\qquad
Q_{m,b}=\frac{1}{n}\operatorname{Re}(A_m^*G_{m,b}A_m).
$$

**R-08 — Normalization inside the operator.** The $1/n$ is part of $Q$, not a second normalization applied after evaluating the quadratic form. Any additional segment or coefficient-count normalization belongs in $G$. For the DFT reference, $A=F_n$, $G=D_B$, and $Q_B=P_B/n$. All preprocessing and boundary maps must appear in $A$.

For a random real vector with mean $\mu$ and covariance $\Sigma$,

$$
\mathbb E[\widehat p]=\operatorname{tr}(Q\Sigma)+\mu^\mathsf{T}Q\mu.
$$

For a real Gaussian vector, the variance is

$$
\operatorname{Var}(\widehat p)=2\operatorname{tr}(Q\Sigma Q\Sigma)
+4\mu^\mathsf{T}Q\Sigma Q\mu.
$$

These are mathematical checks, not new research contributions. They support independent references for simulation means and uncertainty. Non-Gaussian processes require their own variance analysis or Monte Carlo estimates.

For a zero-mean stationary process, define $a(f)_j=\exp(2\pi ifj/f_s)$ and $K_Q(f)=a(f)^*Qa(f)$. Then

$$
\mathbb E[\widehat p]=\int_{-f_s/2}^{f_s/2}S(f)K_Q(f)\,df.
$$

**R-09 — Response interpretation.** Compare $K_Q$ with the declared target response to quantify response mismatch. A scalar frequency response characterizes stationary expectations; it does not fully characterize phase-sensitive cross terms or nonstationary behavior. Retain time-domain operator checks and explicit transient experiments.

**R-10 — Independent operator checks.** On small records, construct the analysis matrix by applying the implementation to basis vectors and compare $x^\mathsf{T}Qx$ against the direct estimator. Also compare at least one small case to an independently assembled analytical DFT, Haar, or segment/window operator, so shared implementation errors cannot make the sole check pass. Verify symmetry, positive semidefiniteness within numerical tolerance, and only those partition identities actually claimed. Use dense operators only at bounded sizes; larger sweeps may use matrix-free evaluation.

For a candidate and the finite-record reference, define $\Delta Q=Q_{m,b}-P_B/n$. The deterministic bound

$$
|\widehat p_{m,b}-p_B^{\mathrm{DFT}}|
\leq\|\Delta Q\|_2\|x\|_2^2
$$

is valid. Its normalized version is $|\widehat p-p_B|/P_x\leq n\|\Delta Q\|_2$ for $P_x>0$. A loose bound is not evidence that a practical error predictor is useful.

## 4. Method-specific contracts for M1 onward

### 4.1 STFT and Welch

For $K$ segments of length $L$, taper $w$, $U=\sum_t w_t^2>0$, and unnormalized segment DFTs $Z_{r,k}$, a one-sided density estimate without zero padding is

$$
\widehat S_k=\frac{1}{Kf_sU}\sum_r d_k|Z_{r,k}|^2.
$$

A rectangular frequency-bin sum uses $\Delta f=f_s/L$: $\widehat p_B=\sum_{k:f_k\in B}\widehat S_k\Delta f$. For a complete frequency partition,

$$
\sum_B\widehat p_B=\frac{1}{KU}\sum_{r,t}w_t^2y_{r,t}^2,
$$

where $y_r$ is the explicitly preprocessed segment. This usually differs from $P_x$, because tapering, overlap, incomplete coverage, and segment detrending change sample weights. An STFT needs an equally explicit time aggregation before it becomes a record-level band measurement [W1967, SCIPY-WELCH].

**R-11 — Welch accounting.** Never repair the difference by assigning $P_x-\sum_B\widehat p_B$ to an alleged low-frequency band. Report the method-total power and its discrepancy from actual record power. Explicitly set taper, overlap, FFT length, detrending, sidedness, scaling, and arithmetic averaging. Median averaging is outside the initial fixed-quadratic scope.

**R-12 — Resolution and quadrature.** Zero padding refines the sampled frequency grid; it does not create longer-window resolution. A segment with no bins in a requested band must report that measurement limitation. Do not silently substitute a nearest bin. Density integration, endpoint weights, and any partial-bin integration require a declared convention; a trapezoidal rule must not silently replace the discrete Parseval-compatible sum.

### 4.2 Orthonormal DWT and boundaries

The initial DWT comparison will use orthogonal wavelets, compatible lengths, and an explicitly verified periodized transform. At $f_s=128$, two-level groups $A_2,D_2,D_1$ have nominal low-to-high associations with the M0 bands, but finite filters have overlapping transition responses.

**R-13 — Orthogonality is conditional.** Verify that the actual finite transform is square and orthonormal before claiming $\sum_jp_j=P_x$. PyWavelets `periodization` and `periodic` are distinct modes. Symmetric, reflected, zero-extended, odd-length, or redundant transforms may produce different coefficient counts and accounting [PYWT-MODES, PYWT-DWT]. Perfect reconstruction alone does not prove orthogonality or power preservation.

**R-14 — Boundary statements.** No extension mode is universally “artifact free.” A mode encodes an assumption about unobserved samples. Measure sensitivity against known continuations and controlled transient positions. Removing boundary-dependent coefficients changes support and normalization; it does not preserve the original full-record estimand automatically. Derive affected coefficients from the actual filter cascade and extension map.

MODWT or SWT is optional after the core study. Their normalization and redundancy require a separate contract. Do not substitute a library SWT for a published MODWT estimator without documenting the relationship [P1995, PYWT-SWT].

## 5. Reporting, comparability, and refusal

**R-15 — Two distinct fractions.** If requested, report $\widehat p_{m,b}/P_x$ as a fraction of actual record power, and $\widehat p_{m,b}/\sum_c\widehat p_{m,c}$ as a fraction of the method total. The former need not sum to one; the latter can hide normalization errors. Label both denominators and retain absolute powers. A zero denominator yields an explicit undefined value, never zero, infinity, or an arbitrary epsilon-adjusted share.

**R-16 — Comparison status.** An exact finite-record comparison requires the same record, units, preprocessing target, and declared quadratic measurement. A comparison between different estimators of one population target may be valid while their biases differ. Native-scale versus hard-band comparisons require an explicitly approximate response-based interpretation. Otherwise refuse an equivalence claim while still permitting separately labeled descriptive outputs.

**R-17 — False-comparison rejection coverage.** Maintain an adversarial suite containing mismatched units, sample rates, records, preprocessing, target types, boundary assumptions, normalization, unsupported input, and fraction denominators. Add the deliberately misleading cases “DWT level equals a brick-wall band,” “PSD ordinate equals band power,” and “unaccounted taper loss is low-frequency power.” Report rejection coverage by category, the false-acceptance rate, and the false-rejection rate on valid controls. A system that refuses every comparison fails this requirement.

Compatibility here is a documented measurement decision, not a statistical significance test. An approximate comparison must expose its assumptions and diagnostic uncertainty rather than receiving an unexplained pass flag.

## 6. Questions and falsifiable hypotheses

**R-18 — Separate checks from research.** Parseval equality, normalization identities, Gaussian moment formulas, and the M0 tone powers are implementation obligations. Passing them does not support a new scientific claim.

The prospective research questions are:

1. **H1, explanatory value:** on previously unused stationary configurations, declared normalization and response diagnostics account for observed cross-method disagreement more accurately than nominal band labels alone. Evaluate prediction residuals against analytical expectations and Monte Carlo uncertainty; report failures by signal family.
2. **H2, diagnostic usefulness:** a rule selected using development cases identifies materially misleading approximate comparisons on held-out configurations while retaining useful valid comparisons. Primary outcomes are false acceptance and retained coverage at a frozen error tolerance.
3. **H3, boundary limits:** diagnostics based only on stationary frequency response leave systematic errors for some short or transient records; explicitly adding boundary/support diagnostics improves held-out error detection. A finding of no improvement is acceptable.

“Materially misleading” must be defined numerically before confirmation, in absolute units or relative to a declared positive reference power. Do not choose the tolerance after inspecting confirmation errors. These hypotheses concern a specified diagnostic system and experiment domain; they do not assert universal method superiority or a universal conversion between transforms.

## 7. Experiment design

### 7.1 Deterministic controls

**R-19 — Known-answer cases.** Use zero records, constants, coherent single tones, the M0 two-tone mixture, impulses, and phase or sign transformations with analytically justified expectations. Later include tones exactly at 16 and 32 Hz, DC, even-length Nyquist, and odd-length records. A sinusoid at DC or Nyquist does not generally have the interior-tone mean square $A^2/2$.

Positive controls inject a known change: vary one tone amplitude, move a tone across a declared boundary, or deliberately alter normalization. Negative controls include identical operators through independent implementations and identical records under valid units conversions. Circular shifts preserve finite-record DFT band powers; they do not necessarily preserve a decimated DWT group power. Treat that contrast as expected behavior, not an automatic defect.

### 7.2 Stationary stochastic experiments

Use white Gaussian noise and stationary AR(1) processes with prescribed parameters, then a limited additional smooth or narrowband covariance family if justified. Draw from the declared finite covariance directly for small reference cases, or initialize time-series recursions from their stationary law. Record innovation variance and total process variance separately. Do not use circular FFT synthesis while claiming an ordinary Toeplitz covariance without checking the difference.

**R-20 — Matched repetitions.** Every method sees the same realization within a cell. Pair method differences by realization, not by segment or coefficient. Independent realizations are the replication unit; overlapping Welch segments are not independent experimental replicates. Gaussian analytical moments provide an independent reference; numerical integration error must be bounded separately.

Matched nulls preserve the feature relevant to the null question: same covariance for a stationary measurement null, same record for an operator-equivalence check, or known-continuation pairs for boundary comparisons. Random shuffling is not a generic null because it destroys autocorrelation. Random phase experiments must state what they preserve and cannot certify transient behavior.

### 7.3 Leakage and nonstationarity

Sweep off-grid tones, near-edge tones, chirps, isolated bursts, trends, and changing variance envelopes. Specify their finite sampled construction. Use the finite-record DFT measurement or another declared finite operator as reference; do not invent one stationary population PSD for a nonstationary record. Component-wise powers need not add when finite-record cross terms are present.

**R-21 — Controlled factors.** Vary one factor at a time before selected interactions: record length, segment length, taper, overlap, wavelet/filter length, boundary mode, frequency offset, phase, transient location, and signal-to-noise ratio. Keep physical frequency, record duration, and resolution changes distinguishable. Do not confound longer records with a different sampling rate without declaring that experiment.

### 7.4 Proposed executable study matrix

The following is the default future study design, not an instruction to implement it in M0. M3 may amend it for a documented scientific or computational reason; record amendments before evaluating the replacement cases and freeze the final matrix before M4. Keep $f_s=128$ Hz and the M0 physical bands throughout this initial design.

| Panel | Development/calibration defaults | Candidate confirmation defaults |
|---|---|---|
| Record length | $n\in\{256,512\}$ | $n\in\{384,768\}$, unseen lengths divisible by four |
| Stationary signals | Unit-variance white Gaussian noise; stationary AR(1) with $\phi\in\{-0.7,0.7,0.95\}$ | White noise with new realizations; AR(1) with $\phi\in\{-0.5,0.5,0.9\}$ |
| Off-grid tones | Base frequencies 8 and 24 Hz; offset $\delta f_s/n$, $\delta\in\{0,0.25,0.5\}$; phases $0,\pi/4,\pi/2$ | Offsets $\delta\in\{0.125,0.375\}$; phases $\pi/8,3\pi/8$ |
| Band-edge probes | Single tones at $16+\delta f_s/n$ and $32+\delta f_s/n$, $\delta\in\{-0.5,0,0.5\}$ | Same edges with $\delta\in\{-0.375,-0.125,0.125,0.375\}$ |
| Boundary/transient probes | Impulse; Hann-enveloped 24 Hz burst of length $n/8$; linear 8-to-40 Hz chirp | Burst length $n/16$; linear 12-to-44 Hz chirp; new positions |

For AR(1), initialize $x_0\sim N(0,1)$ and use innovation variance $1-\phi^2$. For tones retain amplitudes 1 and 0.5, changing only one offset or phase at a time initially. Define a burst on local support indices by $x_{s+j}=w_j\sin(2\pi\,24j/f_s)$, with symmetric Hann envelope $w_j=[1-\cos(2\pi j/(L-1))]/2$, zero elsewhere. Place its support at the start, centered, and end in development, and centered at one-quarter and three-quarters of the record in confirmation; define integer centers by flooring. Unit impulses use those same relative positions. Define the unit-amplitude chirp as the sine of phase $2\pi(f_0t+\kappa t^2/2)$, with $\kappa=(f_1-f_0)/[(n-1)/f_s]$. Compare these deterministic records to the finite-record reference, not a purported stationary PSD.

Estimator defaults are Welch segment lengths 64 and 128, rectangular and periodic Hann tapers, overlap 0 and one-half, no detrending, $\mathrm{nfft}=L$, and arithmetic averaging. Use all complete frames starting at zero, with omitted samples reported. DWT defaults are Haar and db4, two levels, and `periodization`; add `symmetric` and `zero` only in the boundary panel with their actual coefficient normalization and support declared. Run every estimator on each base signal case, but keep factor sweeps separate rather than multiplying all signal perturbations into an unnecessarily large Cartesian product. Generate and review the complete case inventory before execution. Dense inspection at $n=768$ requires an explicit increase from the default 512-sample cap and a recorded memory budget; evaluate one operator family at a time or mark the diagnostic unavailable rather than silently omitting those cases.

Use 256 independent realizations per stationary development cell, 512 fresh realizations per calibration cell, and provisionally 1,024 per confirmation cell. At a true rate of 0.05, 1,024 Bernoulli observations give an approximate standard error of 0.0068; actual intervals must use the observed counts. This is a planning precision calculation, not a guaranteed interval width. Increase counts prospectively if the primary effect requires greater precision; do not rerun until significance appears. Deterministic probes need no stochastic replication unless phase or noise is an explicitly declared experimental factor.

The default material-error criterion for finite-record comparisons is $|\widehat p_b-p_b^{\mathrm{DFT}}|/P_x>0.05$, evaluated only when $P_x>0$; zero records use absolute numerical checks. Keep 0.01 and 0.10 thresholds as predeclared descriptive sensitivity analyses. Population-bias experiments retain their own target and uncertainty rather than inheriting this record-level classification.

### 7.5 Candidate diagnostic family v1

These four diagnostics apply only to the declared fixed linear measurements. They are proposed study instruments, not novel estimators or established predictors of practical error.

1. **Finite-record bound:** $b_b=n\|Q_{m,b}-P_B/n\|_2$. This gives the proven relative-to-record-power bound in Section 3. The conservative mathematical rule accepts a finite-record approximation only when $b_b\leq0.05$. Record the numerical norm algorithm and its uncertainty; do not claim numerical certification from an unbounded approximation or decide a near-threshold case without accounting for that uncertainty. A rigorous upper estimate may use a proven matrix-norm upper bound with controlled numerical error. Otherwise label the result a numerically evaluated analytical bound. An iterative norm estimate is not a certified bound unless its error is controlled accordingly.
2. **Stationary response mismatch:** $r_b=f_s^{-1}\int_{-f_s/2}^{f_s/2}|K_{Q_{m,b}}(f)-K_{P_B/n}(f)|\,df$. This is a heuristic for the finite-record-comparison task, not a signal-wise error bound. Integrate with a declared convergence-checked quadrature; a uniform PSD and a sharply concentrated PSD need not respond similarly to the same score.
3. **Declared-edge diagonal mass:** let $E$ contain the first and last $w=\lceil0.1n\rceil$ sample indices, counted once. Define $d_b=\left|\sum_{j\in E}(Q_{m,b})_{jj}/\operatorname{tr}(Q_{m,b})-|E|/n\right|$ when the trace is positive. This describes departure from uniform diagonal weight near the declared edges. It neither measures every boundary-dependent coefficient nor captures off-diagonal interactions; zero does not establish freedom from boundary effects.
4. **Extension sensitivity:** $s_b=n\|Q_{m,b}^{\mathrm{mode}}-Q_{m,b}^{\mathrm{baseline\ mode}}\|_2$. Use `periodization` as the DWT baseline only when record support, preprocessing, group role, units, and normalization are compatible. The score bounds the effect of changing that operator, not error against unknown physical continuation. Otherwise mark it unavailable. Report this diagnostic descriptively in v1 rather than adding another tuning dimension.

Compare a contract-only baseline retaining every explicitly permitted approximate comparison, a response-only rule $r_b\leq t_r$, and a response-plus-edge rule $r_b\leq t_r$ and $d_b\leq t_d$. Use $t_r\in\{0.01,0.02,0.05,0.1,0.2,0.5\}$ and $t_d\in\{0.01,0.05,0.1,0.25,1\}$. Contract violations are refused before any rule; missing diagnostics do not become zero. Report the operator-bound baseline separately with its numerical qualification. These are finite, transparent rules, not fitted classifiers.

Within each heuristic family, select the rule with greatest retained calibration coverage among candidates having empirical error among accepted comparisons at most 0.05 and at least 100 accepted cases. Break ties by fewer conditions, then smaller response and edge thresholds. Report counts by signal family so pooling cannot hide a failed family. This is a selection screen, not a post-selection coverage guarantee. If no rule qualifies, record that failure. M4 evaluates the selected rules once with fresh cases and uncertainty; it does not recalibrate them. Distinguish accepted-case error $N_{\mathrm{accepted,wrong}}/N_{\mathrm{accepted}}$, false acceptance $N_{\mathrm{accepted,wrong}}/N_{\mathrm{wrong}}$, false rejection $N_{\mathrm{rejected,accurate}}/N_{\mathrm{accurate}}$, and coverage $N_{\mathrm{accepted}}/N$; zero denominators are undefined.

## 8. Metrics and inferential discipline

**R-22 — Primary metrics.** Report signed finite-record error, absolute error, population bias when available, Monte Carlo variance/RMSE, power-accounting discrepancy, frequency-response mismatch, refusal rates, and retained comparison coverage. Relative errors are undefined at a zero target; use absolute errors or a predeclared positive scale there. Fraction agreement alone cannot establish accurate absolute power.

Diagnostic evaluation must include both retained-case accuracy and retained-case coverage. A method may appear accurate merely by refusing difficult cases. Record runtime and memory as secondary engineering measurements with environment metadata, not universal performance claims.

**R-23 — Sampling uncertainty.** For stochastic cells, report replicate count, mean, standard error, and a declared interval method. Use paired differences for paired methods. A rejection/error rate for one fixed method-band cell across independent realizations can use binomial uncertainty. Pooled results across methods or bands from the same realization are dependent: use a declared stratified cluster bootstrap that resamples complete independent realizations within each signal/configuration cell, preserving all paired outputs. Fix scenario weights and define whether the target is the finite scenario inventory or a wider population; do not count correlated method-band rows as independent Bernoulli trials. Choose repetitions from a predeclared Monte Carlo precision target or fixed budget; if sequential stopping is used, specify a valid stopping rule. Scientific intervals should not become fixed-seed continuous-integration pass/fail gates.

**R-24 — Multiplicity.** Identify the small confirmatory metric family before M4 and specify its multiplicity treatment or simultaneous interval construction. All additional slices are descriptive. A visually striking heatmap cell does not override the frozen primary criterion. Report all executed planned cells, including unsupported and failed cells.

## 9. Development, calibration, and confirmation

**R-25 — Honest separation.** Development cases may be inspected and changed. Diagnostic threshold calibration uses explicitly identified development/calibration configurations. Confirmation uses separately generated realizations and also withheld configurations: new phases and seeds alone do not demonstrate generalization to new signal regimes.

Before confirmation, freeze the code revision, dependency lock, estimator definitions, comparison rules, tolerances, scenario matrix, seed-generation rule, repetition counts, stopping rules, exclusions, metrics, and report template. Record a manifest hash. A deterministic split of scenario identifiers is acceptable if declared before their outcomes are inspected; the seed itself need not be secret.

**R-26 — Held-out diagnostics.** Evaluate the frozen rule against new record lengths or frequency offsets within its declared domain, plus explicitly marked out-of-domain stress cases. Separate interpolation, extrapolation, and unsupported-input results. If tuning resumes after confirmation inspection, label that analysis exploratory and create a new confirmation version rather than preserving the old claim.

## 10. Milestones and first experiment

### M0 — Bootstrap and one analytical smoke demonstration

**R-27 — Exact initial scope.** M0 contains only the finite-record DFT reference and the following noise-free signal:

$$
f_s=128\ \mathrm{Hz},\quad n=256,\quad
x_j=\sin(2\pi\,8j/128)+0.5\sin(2\pi\,24j/128).
$$

Both phases are zero. Apply no demeaning, taper, noise, padding, or detrending. Use bands $[0,16)$, $[16,32)$, and $[32,64]$ Hz. Coherent Fourier-bin orthogonality gives the analytical reference powers

$$
(p_1,p_2,p_3)=(0.5,0.125,0),\qquad P_x=0.625.
$$

Fractions of actual record power are $(0.8,0.2,0)$. These values are not Monte Carlo means or empirical study results. Numerical zero uses the acceptance tolerance, not a demand for exactly zero floating-point output.

The future M0 command writes `band_powers.csv`, `summary.json`, and `manifest.json` according to the software specification. No plot is required. Do not add Welch, wavelets, noise sweeps, diagnostic thresholds, or a full experiment suite to the initial public scaffold.

### M1 — Estimator contracts and implementations

Implement supported mean-averaged STFT/Welch and orthonormal DWT contracts. Establish normalization, denominators, boundary semantics, and independent known-answer checks. The first actual method comparison is the M0 signal passed through those methods with their native outputs accurately labeled. Their disagreement is a measurement question, not a failed DFT smoke test.

### M2 — Operators and diagnostics

Construct bounded-size quadratic references, response kernels, accounting diagnostics, and the comparability/refusal suite. Verify formulas and support claims before using diagnostics to make research decisions.

### M3 — Development studies and calibration

Execute the controlled signal families, select a compact final scenario matrix, and calibrate diagnostic rules. Record exploratory results and revisions. Produce the frozen M4 plan; no confirmation claim belongs in this stage.

### M4 — Frozen confirmation and report

**R-28 — Reportable outcomes.** Run the frozen plan, publish the full result inventory and uncertainty, and distinguish exact identities, implemented capabilities, development observations, and confirmatory findings. A negative or inconclusive result is a valid outcome. Publish no superiority claim without the corresponding target, domain, comparisons, and evidence.

## 11. Limits and contribution gate

The project does not promise that spectra from all transforms can be made identical, that one padding mode is correct for every unknown continuation, or that a short record identifies a population spectrum without assumptions. Classical wavelet variance, finite-sample spectral bias, and quadratic-estimator corrections already have substantial literature [P1995, A2024, A2025].

**R-29 — Novelty review before claims.** Compare the eventual contribution with that literature and existing implementations. A reproducible measurement-contract toolkit, an unusually clear failure atlas, or validated diagnostic coverage may be useful contributions; none is novel merely because this repository implements it. If the work only recovers established theory, report it accurately as replication, engineering, or educational validation.

**R-30 — Reproducible evidence.** Every quantitative table must derive from identified artifacts, configuration, and code revision. Keep implementation checks, simulation truth, estimator output, and interpretive claims distinguishable. Future amendments must state what changed and which earlier conclusions need recomputation.
