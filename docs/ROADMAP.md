# Roadmap and intended deliverables

Status: M0 local implementation verified on 2026-10-30; public push status is recorded separately after publication. M1–M4 remain planned. Update this document only from actual completed work and recorded checks.

## 1. Milestone plan

Effort ranges are planning estimates for one experienced engineer, not work already performed, promised results, or a required commit count. Literature access, mathematical issues, and implementation findings may change the estimates. Total planned scope is approximately 43-76 focused hours; there is substantial work after the initial scaffold.

| Milestone | Estimate | Deliverables | Exit evidence |
| --- | --- | --- | --- |
| **M0: Bootstrap** | 2-4 h | Package skeleton, strict demo config, Fourier reference, two-tone demo, meaningful tests, documentation, CI, initial public commit | Isolated install; tests/lint; verified demo outputs; actual remote commit and visibility |
| **M1: Estimator contracts and implementations** | 10-16 h | Welch/STFT and DWT adapters, complete settings metadata, matched input preprocessing, independent checks; focused prior-work review | Correct scale/units and explicit target definitions; relevant acceptance gates pass |
| **M2: Measurement operators and diagnostics** | 12-22 h | Exact small-record Q construction, response probes, power-accounting and boundary diagnostics, inspect command | Direct/operator agreement; known failure cases and diagnostic limitations documented |
| **M3: Development studies and calibration** | 10-18 h | Paired experiment runner, deterministic seeds, stationary/boundary/comparison studies, provisional diagnostic policy, tables/figures | Complete case accounting; development findings; locked proposed confirmation plan |
| **M4: Confirmation, report, and release** | 9-16 h | Frozen configuration/protocol, held-out runs, sensitivity and coverage analysis, technical report, examples, reproducibility bundle | Independent rerun; complete positive/negative results; accurate release claims |

Milestones depend sequentially on their measurement contracts. Literature review and documentation can run alongside implementation, but confirmation starts only after the relevant contracts, diagnostics, thresholds, and analysis are frozen.

## 2. M0: bounded bootstrap assignment

Implement only the M0 files in [ENGINEERING_SPEC.md](ENGINEERING_SPEC.md). Read the entire design so choices leave room for later stages, but stop after a runnable, tested scaffold and initial public push.

The demo is a fixed coherent two-tone signal with a finite-record Fourier reference. It is a numerical sanity check, not the research study. The initial README records M0 capabilities and labels subsequent work as planned. Only completed M0 checks are marked done.

One initial commit should describe the actual bootstrap change. Normal timestamps and the verified author's identity are used. There is no target number of commits and no manufactured history.

## 3. First few hours after bootstrap

Use actual available time to complete one useful increment at a time. This sequence makes the early project useful while leaving meaningful research work ahead.

### Increment A: first estimator contract

Define the first `EstimatorContract` and extend result types to carry the target, native normalization, segment/window settings, and denominator explicitly. The DFT normalization and endpoint checks already belong to M0; reuse them as the reference. Write a small hand-calculated segment/window case that will independently verify the new adapter.

### Increment B: first classical estimator

Implement one explicitly configured Welch/STFT adapter with fixed window, overlap, frame selection, detrending, and PSD normalization. Check it on coherent tones and white noise. Report its own total and actual record power separately. Include a case where taper/coverage weighting makes the two differ.

### Increment C: first comparison artifact

Add a small measure configuration and produce a table comparing the Fourier reference to the implemented estimator with target labels and documented caveats. Keep the full wavelet/operator/confirmation study on the roadmap.

These are examples of coherent development increments. Commit when a meaningful change is complete. A few hours of authentic work may complete part of this sequence; report that state accurately rather than forcing a maturity label.

## 4. Detailed backlog

### M1 tasks

- Read and summarize the closest literature in `docs/NOVELTY_AUDIT.md`; distinguish existing estimator/correction theory from the proposed diagnostic study.
- Define `EstimatorContract` and `Measurement` without conflating finite-record Fourier bands and native wavelet scale groups.
- Implement fixed-settings Welch/STFT; validate window-density scaling, one-sided multiplicities, frame averaging, and mean policy.
- Implement DWT group powers with explicit mode, filter, level, boundary coefficients, and input length.
- Establish an orthonormal periodized case where Parseval is independently verified; document where that property does not apply.
- Add direct adapter tests, configuration validation, and the `measure` CLI.

**Decision gate:** if simple established normalization/target corrections resolve the initial mismatch, retain the software result and narrow the novel research question. Do not claim that detecting a known scaling bug is a new general theory.

### M2 tasks

- Construct small-record operators independently from direct measurements.
- Check symmetry/Hermitian structure, nonnegative power, direct/quadratic agreement, and total-power identities under their actual assumptions.
- Plot response to frequency sweeps and endpoint-position probes.
- Separate boundary-weight diagnostics from evidence of actual error; formulate testable predictions.
- Implement explicit invalid/unresolved/unsupported states.
- Add `inspect` outputs and document memory limits.

**Decision gate:** the diagnostic must add useful information beyond reading a nominal frequency label. If a candidate diagnostic cannot be defined independently of the desired outcome, revise it before studying performance.

### M3 tasks

- Implement deterministic case enumeration and stable seed derivation.
- Generate paired inputs so methods see byte-identical signals.
- Run known-spectrum stationary cases, controlled endpoint/burst cases, and null/positive comparison experiments.
- Measure appropriate-reference error, method disagreement, diagnostic false flags, and coverage/retention.
- Explore candidate diagnostic rules on development cases only.
- Record all failures and unsupported configurations; do not silently drop them.
- Freeze selected rules, numerical tolerances, targets, effect sizes, case counts, intervals, seed lists, and code identity for confirmation.

**Decision gate:** choose at most a small number of prespecified primary claims. If no diagnostic succeeds in development, a complete negative evaluation remains a valid M4 scope.

### M4 tasks

- Commit the confirmation protocol and exact case manifest before running confirmation.
- Execute confirmation without adjusting decisions after seeing its results.
- Verify all declared cases completed or have an explicit failure reason.
- Analyze uncertainty at the independent simulation-replicate level and use paired comparisons where designed.
- Report false flags, retained coverage, sensitivity to real changes, and failure cases alongside any improvements.
- Write limitations, nearest prior-work comparison, and an accurate novelty assessment.
- Reproduce selected results in a fresh environment from the release source and recorded dependencies.
- Prepare `v0.1.0` release materials with the actual report and evidence; publication is a deliberate later action.

## 5. Scope controls

Start with three bands, uniformly sampled real input, and CPU execution. A first research release needs a defensible comparison, not every transform family. Add MODWT, multitaper, irregular sampling, field data, or acceleration only when a completed result motivates it and the additional contract is explicit.

Do not make a fixed Q claim for data-adaptive or nonlinear preprocessing. Do not force every output into the same frequency-bin labels. Do not treat a zero denominator, unavailable reference, or unresolved band as a zero-valued scientific observation.

## 6. Intended final evidence bundle

The final bundle contains an installable source revision, exact resolved configurations, run manifests, all declared case statuses, machine-readable estimates/diagnostics/comparisons, selected figures, an analysis script or command sequence, and the report. Include a compact reproduction route plus the full-study command and expected resource range measured on the reference machine.

The report answers what was measured, what was compared, what the controls ruled out, where the diagnostic helped, where it failed, and what remains uncertain. Claims must match the evidence tier.

## M0 local verification record — 2026-10-30

- Implemented the strict schema-v1 two-tone configuration, immutable validated values, full unitary-DFT finite-record band reference, installed CLI, deterministic CSV/summary, and completion manifest with source/configuration/signal/output digests. No later estimator or diagnostic is implemented.
- In a CPython 3.11 Windows virtual environment with the recorded lock, editable installation and `spectral-audit --help` / `--version` succeeded; the version was `0.0.1.dev0`.
- `python -m pytest -q`: 28 passed. The tests include analytic fixture powers, independent rFFT and small explicit-DFT checks, even/odd endpoints, scaling, zero fractions, invalid inputs/configuration, artifact determinism, provenance digests, collision refusal, and interrupted-write completion behavior.
- `python -m ruff check .`: passed. The installed demo wrote the three required artifacts twice; CSV and summary files were byte-identical across the two fresh directories. A repeat into the first nonempty directory returned an error without overwriting it.
- Observed mean-square band powers were `0.49999999999999978`, `0.12500000000000006`, and `5.3127602986847614e-30` `(a.u.)^2`. Record power was `0.6249999999999999`; fractions were `0.79999999999999982`, `0.20000000000000012`, and `8.5004164778956202e-30`. The accounting error was `-1.1102230246251565e-16`; all are within the M0 numerical tolerances. The near-zero high-band result is floating-point residue, not a new measured component.
- The inspected local pre-commit manifest truthfully recorded `source_state=unversioned` and no source revision. Generated run files are ignored. Remote publication and CI had not occurred when this record was written.

## First Welch increment of M1 — local verification, 2026-10-30

- Commit `1248c1b0870fc82458cf9cc9885ada43b69eb288` implements the explicit Welch contract, strict schema-v2 measure command, two fixtures, independent numerical checks, and separate comparison/accounting fields. M0 schema-v1 demo remains intact. This is **partial M1**, not M1 completion.
- Project environment: CPython 3.11.9, NumPy 2.4.6, SciPy 1.17.1, pytest 9.2.0, Ruff 0.17.3 on Windows; the refreshed lock records installed versions. Before the code commit, `python -m pytest -q` yielded 53 passed and `python -m ruff check .` passed. Earlier baseline in the project environment was 28 passed and lint passed; an accidental system-Python 3.10 invocation failed collection and is not counted as baseline evidence.
- After that commit, installed `spectral-audit --help`, `--version`, the M0 demo, and both `measure` configs completed. Each comparison's numerical files were byte-identical across two new output directories, and independent reads matched every manifest output SHA-256. A third invocation into a nonempty output directory returned a nonzero status without overwrite. Both source manifests truthfully recorded `source_state=clean`, that commit, and source digest `1c41ea2d4fa6a2c9992fcd9fbd887b153dc660168a80adc2c982691034e7a52e`.
- Observed powers and their analytical fixture expectations are separated in [M1_WELCH_EXAMPLE.md](M1_WELCH_EXAMPLE.md). The independent tests cover even/odd explicit DFT matrices, DC/Nyquist, scaling, taper and tail support, zero denominators, white-noise windowed identity and six-standard-error ensemble bound, invalid settings, empty-bin bands, CLI determinism/digests, collision refusal, and failed-write manifest behavior.
- DWT, complete nearest-work review, dense operators, diagnostics, sweeps, calibration, confirmation, and research conclusions remain open. Next bounded task: DWT native-group contract and independently verified periodized orthonormal case, alongside continuation of the prior-work audit.

