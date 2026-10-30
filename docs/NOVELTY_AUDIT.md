# Novelty audit — initial note

Welch's 1967 modified-periodogram method, its averaging over windowed segments,
and window-energy normalization are established methods [W1967]. SciPy documents
the production `welch` API's density versus spectrum scaling, one-sided folding,
segment detrending, and mean averaging [SCIPY-WELCH]. SciPy's Hann API distinguishes
the default symmetric window from the periodic spectral-analysis window
[SCIPY-HANN]. This increment implements and independently checks that known
normalization; it makes no novelty claim for Welch or its Parseval accounting.

The prospective research question concerns whether explicit measurement contracts
and later diagnostics help identify misleading comparisons between distinct
finite-record and population quantities. No diagnostic evaluation or research
conclusion has been completed. The broader nearest-work review remains an M1 task.

[W1967]: https://doi.org/10.1109/TAU.1967.1161901
[SCIPY-WELCH]: https://docs.scipy.org/doc/scipy/reference/generated/scipy.signal.welch.html
[SCIPY-HANN]: https://docs.scipy.org/doc/scipy/reference/generated/scipy.signal.windows.hann.html

## Focused nearest-work review — 2026-10-30

This is a focused review of three full texts and one repository README, not an
exhaustive search. Publication dates below refer to the journal issues; arXiv
version dates identify the text actually inspected. The journal metadata was
checked separately against the publisher records.

| Source/version | Sections inspected | Target and assumptions | Normalization/boundaries | Established result or software | Overlap with Spectral Audit | Unresolved distinction | Evidence needed |
| --- | --- | --- | --- | --- | --- | --- | --- |
| [Percival, *On Estimation of the Wavelet Variance*](https://staff.washington.edu/dbp/PDFFILES/wavevar.pdf), full PDF, [*Biometrika* 82(3), 619–631 (1995)](https://academic.oup.com/biomet/article-abstract/82/3/619/260725) | Full-text inspection: introduction, §§2–3, §6; definitions, estimators, boundary terms, and higher-scale filters. | Wavelet variance of a stochastic process with stationary differences of sufficient order; at scale λ it is a filter-response integral of a process spectrum, not a hard Fourier band power. | The paper's wavelet variance uses scale and filter normalization, including `1/(2λ)` in its population definition. Its unbiased finite-sample estimators use coefficients unaffected by boundaries and account for their count. Dyadic frequency ranges are approximate filter associations. | DWT and maximal-overlap wavelet-variance estimators and their large-sample properties are established. | Scale energy, normalization, approximate frequency interpretation, and boundary-coefficient treatment are directly relevant. | This repository's all-coefficient finite-record `sum(c²)/n` and `sum(c²)/n_g` are deliberately distinct quantities; neither alone asserts Percival's population wavelet variance. | Derive mappings and boundary support for any proposed population target; compare responses and estimate bias under declared processes. |
| [Astfalck, Sykulski & Cripps, *Debiasing Welch’s Method for Spectral Density Estimation*, arXiv:2312.13643v2 (11 Apr 2024)](https://arxiv.org/html/2312.13643v2); [*Biometrika* 111(4), 1313–1329 (2024)](https://academic.oup.com/biomet/article/111/4/1313/7703280) | Full-text HTML inspection: §§2.3, 3.1–3.3 and Theorem 1. | Population PSD estimation for stationary processes; its theorem states fourth-order stationarity, finite fourth moments, and cumulant summability. | Welch's unit-energy taper and segment averaging give a finite-window expected PSD equal to a convolution with the window response. Correct density scaling does not remove this population spectral bias. | Biased-basis fitting debiases Welch's PSD estimate under a spectral basis model; finite-sample bias and variance trade-off are established. | The project implements a correctly normalized but uncorrected Welch finite-record measurement and later plans response diagnostics. | Whether the proposed contract/diagnostic workflow adds practical decision value beyond known Welch bias accounting is unresolved. | Match population targets and assumptions; compare diagnostic decisions and prediction residuals with this correction on held-out cases. |
| [Astfalck, Sykulski & Cripps, *Bias correction of quadratic spectral estimators*, arXiv:2410.12386v2 (22 Oct 2024)](https://arxiv.org/html/2410.12386v2); [*Biometrika* 112(3), asaf033 (2025)](https://academic.oup.com/biomet/article/112/3/asaf033/8121249) | Full-text HTML inspection: §§1–3.1, including Welch/lag-window/multitaper examples and response/bias equations. | Zero-mean stationary linear process with iid innovations, finite fourth moment, and covariance regularity (Assumption 1); target is population PSD. | A trace-normalized quadratic spectral estimator has a taper/eigenvalue representation; its expectation convolves the PSD with a weighted response. Bias correction fits deliberately biased spectral bases. | General quadratic representation, response-kernel bias accounting, and a correction construction are established. | The project's planned finite quadratic operators and responses overlap substantially at the mathematical level. | A quadratic or response explanation alone is no novelty claim. The possible distinction is empirically useful comparison refusal/diagnostics across finite Fourier, Welch, and native-scale quantities. | Specify operational decisions and test useful valid retention and misleading comparison rejection against existing methods, with held-out errors and limitations. |
| [`astfalckl/dquad` support repository README](https://github.com/astfalckl/dquad), viewed 2026-10-30; software review only, unexecuted | README introductory statement and example code for generating AR data, Welch, multitaper, lag-window, and `speccy::debias_quad` calls. No package source or runtime was inspected. | Example reproduces Figure 1 of the quadratic-estimator paper on one simulated AR record. | README invokes `speccy` methods; it does not provide evidence that this project has matched their implementation or boundary conventions. | The README says the main implementation resides in [`speccy`](https://github.com/astfalckl/speccy); `dquad` demonstrates it. | Nearby operational implementation of bias-corrected spectral estimators. | Features, correctness, and output comparison with Spectral Audit have not been tested. | Inspect and execute a pinned `speccy` revision and compare like-for-like targets if a software differentiation claim is pursued. |

**Current assessment.** The DFT/Welch/Haar normalization identities, wavelet
scale associations, quadratic representation, and response-based population
bias accounting are established or implementation obligations. A prospective
contribution could be a rigorously specified measurement contract and a
diagnostic study showing that it improves comparison decisions across distinct
targets and support conventions. Usefulness beyond existing theory and software
remains untested. No population inference, general boundary result, exhaustive
search, or established novelty is claimed by this increment.
