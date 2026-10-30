# References and prior-work audit

**Status:** starting bibliography for a prospective project. The sources establish mathematical and implementation context; they do not establish novelty or completed results for this repository. Links were checked during preparation of this specification. Software documentation is mutable: the implementation must record installed versions and use documentation matching those versions.

The mathematical contracts and research questions are in [RESEARCH_PROTOCOL.md](RESEARCH_PROTOCOL.md).

## Primary research

### S1 — Public motivating spectral-comparison study

Jashua Luna (16 July 2026). “Spectral Signatures in SPY and BTC Intraday Returns: A Sample-Limited, Specification-Sensitive Comparison.” Public research report.

- [Full report](https://www.jashualuna.info/Spectral-Signature-SPY-vs-BTC).
- Relevance: motivates examining whether transform definitions and finite-record choices explain apparently substantive spectral differences. The new project uses generic signal experiments and must establish its own results; the earlier report is not a substitute for analytical ground truth or independent validation.

### W1967 — Welch's averaged modified periodograms

Peter D. Welch (1967). “The use of fast Fourier transform for the estimation of power spectra…” [title abbreviated]. *IEEE Transactions on Audio and Electroacoustics*, **15**(2), 70–73.

- DOI and publisher record: [10.1109/TAU.1967.1161901](https://doi.org/10.1109/TAU.1967.1161901).
- Relevance: the original segment-and-average construction and taper normalization underlying Welch estimation. It anchors the distinction between a spectral estimator and an exact whole-record Fourier projection.
- Audit implication: averaging modified periodograms, segment-length tradeoffs, and their spectral-window interpretation are established methods, not proposed inventions.

### P1995 — Native wavelet variance and maximal overlap

D. B. Percival (1995). “On estimation of the wavelet variance.” *Biometrika*, **82**(3), 619–631.

- DOI: [10.1093/biomet/82.3.619](https://doi.org/10.1093/biomet/82.3.619).
- Publisher record: [Oxford Academic](https://academic.oup.com/biomet/article-abstract/82/3/619/260725).
- Author's abstract: [University of Washington](https://faculty.washington.edu/dbp/ABSTRACTS/wavevar.html).
- Relevance: native wavelet-scale variance, DWT and maximal-overlap estimators, sampling distributions, efficiency, and uncertainty. Author initials follow the author's University of Washington summary.
- Audit implication: scale-wise variance estimation and maximal overlap are mature research topics. A project must distinguish coefficient-scale variance from a finite record's power contribution and from ideal Fourier-band power, rather than treating existing distinctions as a new discovery.

### A2024 — Finite-sample correction of Welch estimation

Lachlan C. Astfalck, Adam M. Sykulski, and Edward J. Cripps (2024). “Debiasing Welch's method for spectral density estimation.” *Biometrika*, **111**(4), 1313–1329.

- Author publication list, confirming publication metadata: [Lachlan Astfalck](https://astfalckl.github.io/publications.html).
- Author preprint: [arXiv:2312.13643](https://arxiv.org/abs/2312.13643); first submitted in 2023 and revised in 2024. Cite the journal year separately from the preprint submission year.
- Relevance: a principled correction for finite-sample Welch bias, with theory, simulations, and accompanying implementations.
- Audit implication: the project cannot claim novelty merely for correcting Welch bias, observing a bias–variance tradeoff, or evaluating frequency-dependent correction. Any proposed correction must be compared with this work using a declared target and comparable assumptions.

### A2025 — Bias correction for the quadratic-estimator family

Lachlan C. Astfalck, Adam M. Sykulski, and Edward J. Cripps (2025). “Bias correction of quadratic spectral estimators.” *Biometrika*, **112**(3), article asaf033.

- DOI: [10.1093/biomet/asaf033](https://doi.org/10.1093/biomet/asaf033).
- Publisher record: [Oxford Academic](https://academic.oup.com/biomet/article/112/3/asaf033/8121249).
- Author preprint: [arXiv:2410.12386](https://arxiv.org/abs/2410.12386).
- Authors' support repository: [astfalckl/dquad](https://github.com/astfalckl/dquad).
- Relevance: extends finite-sample bias correction beyond Welch to a broader quadratic-estimator family, including lag-window and multitaper estimators.
- Audit implication: expressing a spectral estimate as a quadratic form and using its expected response are established foundations. A claim about a new general correction, equivalence framework, or diagnostic must be checked against this article and the work it cites. The current project proposes a narrower comparability study; it does not yet implement or outperform the paper's correction.

## Official implementation documentation

### NUMPY-FFT — Fourier convention and real-input multiplicities

NumPy Developers. “Discrete Fourier Transform.” Official NumPy reference documentation.

- [FFT reference](https://numpy.org/doc/stable/reference/routines.fft.html).
- Use to confirm forward/inverse normalization, frequency ordering, real transforms, and DC/Nyquist conventions. The specification's unitary mathematical transform and an implementation's default unnormalized forward transform must be reconciled explicitly.

### SCIPY-WELCH — Explicit estimator parameters

SciPy Developers. “scipy.signal.welch.” Official SciPy API documentation.

- [Welch API](https://docs.scipy.org/doc/scipy/reference/generated/scipy.signal.welch.html).
- Use to verify density versus spectrum scaling, taper energy, overlap, FFT length, sidedness, detrending, and averaging options. Defaults must be passed explicitly when they affect the measurement contract.

### SCIPY-SPECTRAL — Normalization and spectral analysis context

SciPy Developers. “Signal Processing (scipy.signal),” spectral-analysis section. Official SciPy tutorial.

- [Signal-processing tutorial](https://docs.scipy.org/doc/scipy/tutorial/signal.html#spectral-analysis).
- Use as implementation-level context for amplitude, power, PSD, windowing, and frequency resolution. It complements the research papers; it is not evidence that all estimators target the same finite-record quantity.

### PYWT-MODES — Extension is an assumption

PyWavelets Developers. “Signal extension modes.” Official PyWavelets documentation.

- [Extension modes](https://pywavelets.readthedocs.io/en/latest/ref/signal-extension-modes.html).
- Use for exact semantics of `periodization`, `periodic`, `symmetric`, `reflect`, and other extensions. Boundary behavior depends on both the extension and the actual signal. Documentation of a mode does not justify claiming that it always reduces bias or removes artifacts.

### PYWT-DWT — Coefficient layout and finite-transform size

PyWavelets Developers. “Discrete Wavelet Transform (DWT).” Official PyWavelets documentation.

- [DWT reference](https://pywavelets.readthedocs.io/en/latest/ref/dwt-discrete-wavelet-transform.html).
- Use to confirm coefficient lengths, decomposition levels, group ordering, and extension effects. Coefficient counts need not sum to the input length under every mode. Test the actual finite transform before invoking orthogonal power accounting.

### PYWT-SWT — Optional future redundant transforms

PyWavelets Developers. “Stationary Wavelet Transform.” Official PyWavelets documentation.

- [SWT reference](https://pywavelets.readthedocs.io/en/latest/ref/swt-stationary-wavelet-transform.html).
- Use only if the project later adds an undecimated transform. Energy conservation depends on stated wavelet and normalization settings. The documentation also distinguishes its implementation from the published MODWT formulation. SWT/MODWT is not required for M0–M1.

## Novelty audit to complete before a research claim

| Proposed element | Established context | Evidence still needed from this project |
|---|---|---|
| Absolute Fourier-band accounting | DFT normalization and Parseval identities | Correct implementation and transparent conventions |
| Welch normalization and leakage explanation | W1967; SCIPY-WELCH; A2024 | Controlled comparisons with targets and coverage held explicit |
| Wavelet-scale measurement | P1995 and the wavelet-variance literature | Correct native-estimand reporting; any claimed cross-method benefit |
| Quadratic-form response analysis | A2025 and its cited foundations | Added diagnostic value beyond reproducing known expectations |
| Comparability/refusal contracts | Existing estimator theory and software conventions | False acceptance, false rejection, and retained coverage on held-out cases |
| Boundary and transient failure atlas | Established finite-filter and extension effects | Clearly scoped new experiments, useful coverage, and reproducible evidence |

The initial literature check is selective. Before a paper or novelty claim, review the references of P1995, A2024, and A2025; search for prior cross-method band-power comparisons, wavelet/Fourier response matching, finite-record boundary studies, and spectral measurement validation software. Record each relevant method's estimand, assumptions, available implementation, and overlap with the proposed contribution. Do not infer novelty from a search returning few results.

No source code or data from a referenced repository is automatically incorporated into this project. If later reused, record the exact source revision, applicable license, attribution, and changes. An independently written mathematical implementation should still cite its methodological sources.
