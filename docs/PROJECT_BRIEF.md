# Project brief: Spectral Audit

Status: proposed research and implementation plan.  
Working research title: **When Are Spectral Band-Energy Estimates Comparable?**  
Software name: **Spectral Audit**.  
Target first research release: `v0.1.0`; bootstrap version: `0.0.1.dev0`.

## 1. Purpose

Spectral Audit is a Python command-line tool and research library for inspecting how Fourier and wavelet analysis choices affect reported band powers on finite signals. It makes the measurement target, units, normalization, filter response, and boundary behavior explicit, then evaluates whether those measurements support a meaningful comparison.

The intended users are scientific programmers and researchers who compare frequency-band contributions in short sensor, laboratory, or simulated time series. A useful result is a reproducible explanation of which differences arise from the signal, which arise from the measurement procedure, and which remain unresolved.

The motivating public study, *Spectral Signatures in SPY and BTC Intraday Returns*, reported strong specification sensitivity when comparing Fourier and wavelet summaries [S1 in REFERENCES.md]. This project investigates that methodological issue on controlled signals. The initial study is independent of any financial dataset, forecasting task, or learned model.

## 2. Research question and proposed contribution

**Question:** Can diagnostics based on finite-record measurement operators, effective filter responses, and boundary influence identify when nominally similar Fourier and wavelet band-power estimates support misleading comparisons?

The proposed contributions are:

1. A clearly specified comparison protocol that keeps finite-record Fourier power, population spectral power, and native wavelet scale variance distinct.
2. A tested implementation of classical estimators with inspectable normalization and measurement operators.
3. Controlled experiments quantifying error, method disagreement, and the effect of sampling/window/boundary choices.
4. A predeclared diagnostic assessment: whether flags predict unreliable comparisons on held-out signal configurations, with both false flags and retained coverage reported.

These are proposed contributions. Quadratic spectral estimators, wavelet variance, boundary corrections, and spectral-bias correction are established work. A literature audit and reproduction of relevant baselines must precede any novelty claim. The software can be useful even if the proposed diagnostic supplies no advantage.

## 3. What success means

The project succeeds as research software if an independent user can install it, run a small deterministic example, reproduce the controlled studies from recorded configurations, and identify the assumptions behind every reported quantity.

The scientific outcome may be a successful diagnostic, a narrower domain of usefulness than expected, or a negative result. Agreement between methods is not enough: accuracy against an appropriate reference and the reliability of the resulting comparison are the central criteria.

The first complete report must distinguish established numerical identities, development observations, held-out findings, and unresolved assumptions. It must include configurations where the preferred method or diagnostic fails.

## 4. Scope

### Included in the first research release

- Uniformly sampled finite real signals with explicit sample rate and units.
- Float64 CPU implementations and small, independent analytical checks.
- A finite-record Fourier reference defined by a unitary DFT and disjoint frequency bands.
- Welch/STFT measurements and orthonormal DWT scale-group measurements with explicit contracts.
- Exact dense operators for short records and practical direct evaluation for larger experiments.
- Controlled signals: coherent/off-grid sinusoids, white noise, prescribed stationary processes, and defined transient cases.
- Boundary, frequency-response, total-power, and comparison diagnostics.
- Reproducible development and held-out experiments, tables, figures, and a technical report.

### Deferred extensions

- Irregular sampling and missing-data methods.
- Two-dimensional fields, complex-valued input APIs, CWT, multitaper, MODWT, and redundant transforms beyond the explicitly implemented contracts.
- GPU acceleration, a web interface, live acquisition, and external data ingestion.

Each extension needs a specific scientific purpose and a new acceptance gate. The initial work is a signal-measurement study; AI models, AI model evaluation, AI-oriented datasets, and model-serving systems are outside its scope.

## 5. First executable example

Let `fs=128 Hz`, `n=256`, and `t[j]=j/fs`. Define

`x[j] = sin(2*pi*8*t[j]) + 0.5*sin(2*pi*24*t[j])`.

Use no mean removal, no noise, and bands `[0,16)`, `[16,32)`, and `[32,64]` Hz. The final band includes Nyquist. The exact finite-record reference powers are `0.5`, `0.125`, and `0`, with total mean-square power `0.625` and record-power fractions `0.8`, `0.2`, and `0` up to floating-point error.

M0 implements and verifies that reference. These are analytical expectations, not a claim that the broader research has been performed.

## 6. Deliverables

| Deliverable | Completion condition |
| --- | --- |
| Installable Python package and CLI | Documented commands work in an isolated environment; meaningful tests pass |
| Estimator and operator library | Contracts, units, validity conditions, and independent numerical checks are implemented |
| Controlled experiment configurations | Development and confirmation inputs are explicit, versioned, and reproducible |
| Diagnostics and comparison outputs | Flags, reasons, reference quantities, and missing/unavailable values are unambiguous |
| Research evidence bundle | Machine-readable results, manifests, plots, and exact source revision are included |
| Technical report | Methods, prior work, limitations, negative cases, and held-out findings are explained |
| Public reproducibility release | Installation, demo, licenses, provenance, and rerun instructions are complete |

## 7. Delivery strategy

M0 is a bounded bootstrap: project scaffold, reference example, tests, documentation, and a public initial commit. M1 adds estimators; M2 adds operators and diagnostics; M3 runs development studies; M4 freezes the protocol, performs confirmation, and produces the research release.

The canonical technical rules are in [RESEARCH_PROTOCOL.md](RESEARCH_PROTOCOL.md). The exact proposed files and interfaces are in [ENGINEERING_SPEC.md](ENGINEERING_SPEC.md). Scheduling and acceptance are in [ROADMAP.md](ROADMAP.md) and [ACCEPTANCE_CRITERIA.md](ACCEPTANCE_CRITERIA.md).

