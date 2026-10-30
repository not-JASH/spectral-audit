# Engineering specification

Status: proposed interfaces and implementation plan; no functionality is implied by its appearance in this document.  
Normative science: [RESEARCH_PROTOCOL.md](RESEARCH_PROTOCOL.md).  
Milestones: [ROADMAP.md](ROADMAP.md).  
Verification: [ACCEPTANCE_CRITERIA.md](ACCEPTANCE_CRITERIA.md).

## 1. Implementation decisions

| Decision | Initial choice | Reason |
| --- | --- | --- |
| Repository/distribution/import | `spectral-audit` / `spectral-audit` / `spectral_audit` | Readable project identity; publishing to PyPI is a separate future action |
| Runtime | Python 3.11+ | Standard-library TOML reader and modern typing |
| Arithmetic | Real inputs and float64; internal complex128 Fourier calculations | Explicit numerical precision |
| Build | `pyproject.toml`, setuptools, `src/` layout | Conventional editable installation |
| Numerical dependencies | NumPy in M0; SciPy and PyWavelets from M1 | Add dependencies when exercised by actual code |
| Reporting | Standard-library CSV/JSON in M0; Matplotlib from M2/M3 | Small initial install; deterministic tables first |
| CLI | `argparse`, entry point `spectral-audit` | No extra CLI framework required |
| Configuration | Strict TOML, `schema_version = 1` | Editable, versionable, and standard-library parsing |
| Tests/lint | pytest and Ruff | Numerical correctness and maintainable Python |
| Compute | CPU, serial reference execution | Reproducibility and inspectability before performance |
| Initial version | `0.0.1.dev0` | Clearly a development bootstrap |
| Initial license | MIT, for newly authored project code | Straightforward public reuse; respect dependency/source licenses |

Do not guess future package versions in this specification. During bootstrap, choose compatible available stable versions, resolve them in an isolated environment, record the tested versions, and create the reproducibility lock described below. Avoid dependencies on private repositories, credentials, vendor datasets, or a model framework.

## 2. Proposed repository structure

The tables below are authoritative for file status. A path listed as M1 or later is a planned file and should not be created as a misleading empty implementation during M0.

| Directory | Responsibility |
| --- | --- |
| Repository root | README, license, packaging, small repository instructions, and environment lock |
| `src/spectral_audit/` | Library and CLI |
| `src/spectral_audit/estimators/` | Measurement adapters and their contracts |
| `src/spectral_audit/operators/` | Finite-record operators and diagnostics |
| `src/spectral_audit/studies/` | Study execution, paired observations, metrics, and confirmation |
| `tests/` | Independent numerical, schema, and CLI checks |
| `configs/` | Small example plus development and confirmation specifications |
| `docs/` | Project brief, protocol, engineering plan, roadmap, criteria, references, and eventual results report |
| `examples/` | Later runnable usage examples; no copied private datasets |
| `results/` | Generated runs, ignored by Git by default |
| `.github/workflows/` | Lightweight CI |
| `.briefing/` | Local handoff package, ignored by Git |

### 2.1 Files to implement in M0

| File | Required content |
| --- | --- |
| `README.md` | Purpose, current M0 capabilities, installation, demo command, analytic fixture expectations, limitations, roadmap link, and license |
| `LICENSE` | Standard MIT text, actual creation year and Jashua Luna for new original project files |
| `AGENTS.md` | Short project-specific rules: read protocol; preserve units/contracts; truthful status; no claimed results without evidence; test meaningful numerical changes |
| `.gitignore` | Python caches, `.venv/`, build artifacts, `results/`, `.briefing/`, supplied handoff archives, `.env*` except `.env.example`, editor-local files, secrets |
| `pyproject.toml` | Setuptools build, package metadata, Python requirement, NumPy dependency, `dev` extra, CLI entry point, pytest and Ruff configuration |
| `requirements-lock.txt` | Exact tested direct/transitive environment packages resolved during bootstrap; include a header with Python/platform and regeneration command |
| `src/spectral_audit/__init__.py` | Package version `0.0.1.dev0`; minimal public imports |
| `src/spectral_audit/__main__.py` | Delegate to CLI for `python -m spectral_audit` |
| `src/spectral_audit/types.py` | Immutable configuration/value types, band definitions, input validation |
| `src/spectral_audit/config.py` | Strict schema-v1 TOML parsing and canonical serialization |
| `src/spectral_audit/signals.py` | Deterministic tones using integer sample index divided by sample rate |
| `src/spectral_audit/reference.py` | Full unitary-DFT reference, absolute-frequency band assignment, mean-square power and explicit fractions |
| `src/spectral_audit/io.py` | CSV/strict-JSON writing, hashes, manifest, output-directory validation |
| `src/spectral_audit/cli.py` | `--help`, `--version`, and `demo` command |
| `tests/test_reference.py` | Coherent tones, DC, Nyquist, Parseval, scaling, boundary membership, and odd-length checks |
| `tests/test_config.py` | Invalid bands, nonfinite values, unknown keys, unsupported mean policy, missing parameters |
| `tests/test_cli.py` | Isolated demo outputs, schema and values, no accidental overwrite |
| `configs/m0_tones.toml` | Exact supplied initial demo specification |
| `docs/PROJECT_BRIEF.md` | Copy supplied public brief |
| `docs/RESEARCH_PROTOCOL.md` | Copy supplied proposed protocol |
| `docs/ENGINEERING_SPEC.md` | Copy this specification |
| `docs/ROADMAP.md` | Copy roadmap; update only actual completed M0 work after verification |
| `docs/ACCEPTANCE_CRITERIA.md` | Copy supplied gates |
| `docs/REFERENCES.md` | Copy sources and novelty tasks |
| `docs/DECISIONS.md` | Short dated record of actual implementation choices and resolved ambiguities; begin with the adopted M0 contracts |
| `.github/workflows/ci.yml` | Install package with dev extra, lint, tests, and tiny demo on supported Python; read-only default repository permissions |

A baseline environment lock can be made with `pip freeze --exclude-editable` after installing `.[dev]` in the project virtual environment. Remove only project-local editable/path references if present and record that decision. This file describes the tested environment, not a guarantee that every platform resolves identically. CI should install the recorded requirements and then the local project without silently upgrading them. Document how to refresh and verify the lock.

### 2.2 Files for later milestones

| Milestone | Proposed files | Responsibility |
| --- | --- | --- |
| M1 | `estimators/__init__.py`, `estimators/base.py`, `estimators/welch.py`, `estimators/dwt.py` | Contracts, direct measurements, fixed settings, explicit validity metadata |
| M1 | `tests/test_welch.py`, `tests/test_dwt.py`, `configs/m1_estimator_checks.toml` | Independent reference/scaling/extension checks |
| M1 | `docs/NOVELTY_AUDIT.md` | Closest prior work, existing implementations, and the proposed contribution's actual overlap |
| M2 | `operators/__init__.py`, `operators/dense.py`, `operators/response.py`, `operators/diagnostics.py` | Exact short-record Q matrices, frequency response probes, boundary and total-power diagnostics |
| M2 | `tests/test_operators.py`, `tests/test_diagnostics.py`, `configs/m2_operator_checks.toml` | Direct/operator agreement and valid diagnostic behavior |
| M3 | `studies/__init__.py`, `studies/runner.py`, `studies/metrics.py`, `studies/splits.py` | Deterministic paired cases, metrics, seed derivation, development/confirmation separation |
| M3 | `reporting.py`, `tests/test_runner.py`, `tests/test_metrics.py` | Tables/figures, resume behavior, metric correctness |
| M3 | `configs/dev_stationary.toml`, `configs/dev_boundaries.toml`, `configs/dev_comparisons.toml` | Bounded development studies |
| M3 | Existing `docs/DECISIONS.md` and `docs/NOVELTY_AUDIT.md` | Update the decision history and contribution assessment with development evidence |
| M4 | `configs/confirm_stationary.toml`, `configs/confirm_boundaries.toml`, `configs/confirm_comparisons.toml` | Frozen confirmation cases, counts, seeds, and comparisons |
| M4 | `docs/PROTOCOL_FREEZE.json`, `docs/RESULTS.md`, `docs/REPRODUCIBILITY.md` | Frozen source/config identities, complete findings, rerun instructions |
| M4 | `examples/compare_estimators.py`, `examples/inspect_operator.py`, `CHANGELOG.md`, `CITATION.cff` | Verified public examples and release metadata |

Future implementation may split a module when needed; update this table and API documentation in the same change. Do not implement a large plugin framework before a second concrete adapter demonstrates the need.

## 3. Input and measurement contracts

### 3.1 Input

`SignalRecord` contains `samples: numpy.ndarray`, `sampling_rate_hz: float`, `sample_unit: str`, and optional descriptive metadata. `samples` must be one-dimensional, real, finite, with at least two elements. Convert to a private contiguous float64 array or clearly document ownership to prevent mutation after hashing. Complex, ragged, empty, and nonfinite inputs are errors. Sampling rate must be finite and positive.

Initial data are uniformly sampled at `t[j]=j/fs`; do not infer spacing from a vector of timestamps. No interpolation of missing values is implicit.

The tone generator's convention is exactly `x[j] = sum(amplitude[r] * sin(2*pi*frequency_hz[r]*j/fs + phase_rad[r]) for r in tones)`. Phase zero means sine phase zero. Do not substitute a cosine convention: it would preserve the M0 powers but change the record and its hash.

M0 supports `mean_policy="none"` only. M1 may add explicit global demeaning, represented by the fixed projection `H=I-11^T/n` in operator work. Per-frame detrending is a distinct measurement setting and must be modeled as its actual linear operation. A mean policy changes both the measured signal and its reference; do not compare a demeaned estimator to an undeclared raw-power target.

### 3.2 Bands

`Band` contains `name`, `lower_hz`, `upper_hz`, and `include_upper` (default false). All bands have inclusive lower bounds. M0 requires ordered, nonoverlapping, contiguous bands covering `[0, fs/2]`; only the final band includes its upper edge. Use a scale-aware tolerance only when validating adjoining user-supplied edges, not a broad fuzzy bin assignment. Canonicalize validated shared edges once.

Reference bin assignment uses the absolute physical frequencies from `numpy.fft.fftfreq(n, d=1/fs)`. An exact internal edge belongs to the higher band. The last band's upper edge includes Nyquist for even n. For odd n, no Nyquist bin exists. Never use integer division to approximate arbitrary bands or count a bin twice.

M1 may allow partial bands explicitly. It must then report uncovered power and may not claim a full partition.

### 3.3 Initial reference

Let `z = fft(x, norm="ortho")`. For band b with both positive and negative absolute frequencies selected by its mask,

`band_power[b] = sum(abs(z[mask_b])**2) / n`.

`record_power = dot(x,x) / n`.

The full-FFT implementation is the M0 production reference; independently verify it with an rFFT implementation in tests, using multiplicity one for DC and even-length Nyquist, and two for interior positive frequencies. That independent route must not reuse the production mask/multiplicity logic in a way that makes the test tautological.

These are absolute **mean-square powers** with units `sample_unit^2`. The code may discuss energy conceptually, but an unnormalized sum of squares must be named separately. For an implemented complete partition, the powers sum to record power within the numerical tolerance.

`record_power_fraction = band_power / record_power` is undefined when record power is zero. Serialize undefined fractions as JSON `null` or blank CSV cells, with reason `zero_reference_power`. Do not insert zero or NaN as a stand-in. Method-total-normalized shares, when introduced, are named `method_total_fraction` and carry their own denominator. Do not force shares to sum to one by quietly rescaling an estimator.

## 4. Core interfaces

Small dataclasses and typed functions are sufficient. The interface names below form a proposed stable public surface; precise signatures can be adjusted if recorded in `docs/DECISIONS.md`.

```python
load_demo_config(path: Path) -> DemoConfig
make_tones(config: ToneSignalConfig, record: RecordConfig) -> SignalRecord
fourier_reference(record: SignalRecord, bands: Sequence[Band]) -> Measurement
write_demo_run(out: Path, config: DemoConfig, record: SignalRecord,
               measurement: Measurement, provenance: Provenance) -> RunPaths
```

`Measurement` includes method ID, target ID, powers, band names, reference power, method total, fractions with explicit denominators, validity status, reasons, and settings. It must not return an unlabelled array whose interpretation depends on calling code.

From M1, `EstimatorContract` records:

- Method and version; input mean policy and sample support.
- Target kind: `finite_record_fourier`, `population_hard_band_power`, `population_filtered_power`, `native_scale_record_power`, `native_scale_coefficient_mean_square`, or `native_scale_coefficient_variance`. Coefficient variance additionally records its centering convention. These IDs preserve the distinctions in protocol R-05 through R-07.
- Whether its result is an exact finite-record partition, an estimator of a population quantity, or a native response-group measurement.
- Taper, overlap, frame selection/weighting, FFT length, density/spectrum scaling, one/two-sided convention, and detrending where applicable.
- Wavelet name, level, extension mode, retained coefficients, boundary policy, and nominal group labels where applicable.
- Units, explicit normalization, reference ID, and known invalid/unsupported conditions.

An estimator has `measure(record, settings) -> Measurement`. A fixed linear estimator that supports operator inspection additionally has `analysis_matrix(n, fs, settings) -> AnalysisOperator`, or an equivalent checked operator-construction route. Adaptive nonlinear methods do not inherit a fixed Q representation by assertion.

For a coefficient row matrix T and nonnegative fixed weights W, Q is `T.conj().T @ W @ T` with all power normalization included. To match the protocol's `Q=Re(A* G A)/n`, use `T=A` and `W=G/n`; alternatively absorb that scaling in T, but document it once. Never divide `x.T @ Q @ x` by n again. For real input, use the corresponding real symmetric quadratic form and verify imaginary roundoff is negligible. Keep Q construction separate from direct evaluation so agreement is meaningful.

## 5. M0 configuration: exact schema

The supplied `examples/m0_tones.toml` is copied to `configs/m0_tones.toml` at bootstrap. Its schema is:

```toml
schema_version = 1
experiment_id = "m0_coherent_tones"

[record]
n_samples = 256
sampling_rate_hz = 128.0
sample_unit = "a.u."
mean_policy = "none"

[signal]
kind = "tones"
frequencies_hz = [8.0, 24.0]
amplitudes = [1.0, 0.5]
phases_rad = [0.0, 0.0]

[[bands]]
name = "low"
lower_hz = 0.0
upper_hz = 16.0
include_upper = false

[[bands]]
name = "mid"
lower_hz = 16.0
upper_hz = 32.0
include_upper = false

[[bands]]
name = "high"
lower_hz = 32.0
upper_hz = 64.0
include_upper = true

[reference]
kind = "finite_record_dft"
fft_norm = "ortho"
```

Unknown keys are errors, including apparently harmless misspellings. Require equal nonzero lengths for tone arrays, finite numbers, and `0 < frequency < fs/2` for the sine generator; DC and Nyquist tests use directly constructed arrays. Reject noninteger n, booleans masquerading as numbers, nonpositive dimensions/rates, unsupported schema versions, and unsupported methods. M0 does not accept stochastic/noise settings.

Resolve defaults before hashing. Canonical config bytes are sorted-key strict JSON with compact separators, UTF-8, and `allow_nan=False`; ordering of arrays is preserved. The config SHA-256 excludes runtime metadata and output paths.

M3 introduces study configurations without silently changing this demo schema. Add a distinct strict study schema with explicit cases/replicates/method settings. Unknown methods never degrade to the reference automatically.

## 6. CLI contract

### M0 commands

```bash
spectral-audit --help
spectral-audit --version
spectral-audit demo --config configs/m0_tones.toml --out results/m0_demo
```

The demo prints a concise summary and paths to `band_powers.csv`, `summary.json`, and `manifest.json`. It must reject an already nonempty output directory. Creating a new or empty directory is allowed; there is no automatic destructive overwrite. Invalid input/config produces a nonzero exit with a useful error, not a long internal traceback by default. Mathematical zeros may be displayed as zero while persisted values retain full precision.

Return-code convention: 0 success; 2 usage/config/input validation error; 1 operational/runtime failure. A statistical null result is a successful completed study, not a process error.

### Later commands

| Milestone | Proposed command | Contract |
| --- | --- | --- |
| M1 | `spectral-audit measure --config <file> --out <dir>` | Explicit implemented estimators, settings, and references |
| M2 | `spectral-audit inspect --config <file> --out <dir>` | Operator/response diagnostics; enforce matrix-size limits |
| M3 | `spectral-audit study --config <file> --out <dir>` | Recorded case list and deterministic development runs |
| M3 | `spectral-audit report --run <dir> --out <dir>` | Read verified result records, render tables/figures without recomputation |
| M4 | `spectral-audit verify-run <dir>` | Verify schema, configuration and result hashes, completeness, and source/protocol identity |

Only advertise commands implemented at the current milestone. Resume/parallelism are later features and require matching config/code identities before appending to an existing run.

## 7. Output contracts

### 7.1 `band_powers.csv` in M0

Columns in stable order:

`experiment_id,method_id,reference_id,band,lower_hz,upper_hz,include_upper,band_power,power_unit,record_power,record_power_fraction,status,reason`

Use method/reference ID `finite_record_dft_v1`. `power_unit` is the sample unit squared (for the starter, `(a.u.)^2`). Status is `ok`, `undefined`, or `invalid`; invalid inputs normally abort M0 before a table is written. A zero record still has valid zero powers and undefined fractions; use row status `undefined` with a precise reason for the affected ratio. Preserve separate validity fields in later wider schemas when individual quantities differ in validity.

For deterministic artifacts, write UTF-8 with LF line endings and stable row/column order. Use round-trip precision for numeric CSV cells (for example `.17g`), lowercase `true`/`false` for booleans, and empty cells only for documented nullable values. Write JSON with sorted keys, consistent indentation, a final newline, and strict finite-number handling. Presentation rounding belongs in console text or plots, not in scientific records.

### 7.2 `summary.json` in M0

Required top-level fields:

`schema_version`, `experiment_id`, `method_id`, `reference_id`, `n_samples`, `sampling_rate_hz`, `sample_unit`, `mean_policy`, `record_power`, `sum_band_power`, `power_accounting_error`, `bands`, `status`.

`bands` contains an ordered list of definitions, powers, fractions, and their reasons. `power_accounting_error = sum_band_power - record_power`; do not take absolute value and lose direction. Include all raw numbers as JSON numbers with no rounding to presentation precision. All JSON is standards-compliant: no NaN/Infinity literals.

### 7.3 `manifest.json` in M0

Record schema version, package version, canonical resolved configuration and its SHA-256, source config byte hash, signal hash, Python/NumPy versions, platform, source revision, working-tree state, command arguments with the output directory represented separately, and output file hashes for CSV/summary. Always include a `source_files` inventory of sorted relative paths and SHA-256 hashes for the actual `src/spectral_audit/**/*.py` files, `pyproject.toml`, and `requirements-lock.txt`, plus a `source_digest` over the canonical JSON inventory. Hash actual bytes; identify a genuinely missing expected file instead of inventing a hash. This is a declared source set, not a scan of unrelated workspace content.

If Git is unavailable or source is not in a repository, record `source_revision=null` with `source_state="unversioned"`. A run before the initial commit must not claim to originate from the later commit. For dirty work, record `source_state="dirty"`; the inventory above identifies the actual relevant tracked/untracked project source bytes. Clean and unversioned runs also carry that inventory. Later accepted research evidence requires a committed revision and recorded clean/dirty truth.

Signal hash: canonical little-endian float64 C-order sample bytes plus explicit shape/dtype metadata in the manifest. Execution timestamp and elapsed seconds may vary; keep them in an `invocation` object separate from deterministic scientific data. Do not promise bitwise numerical equality across differing library versions or hardware.

Hash outputs after they are finalized. The manifest does not include its own hash. A verification tool computes that externally if needed. Write temporary files in the target directory and atomically rename each final output. Write and atomically rename `manifest.json` last, with `run_status="complete"` only after the CSV and summary and their hashes are finalized. This final manifest is the completion marker; no fourth output file is required. An interrupted or failed run must not leave a manifest claiming completion.

### 7.4 M3/M4 result records

Use long-form `estimates.csv`, `diagnostics.csv`, `comparisons.csv`, and `cases.jsonl` plus summary/manifest. Minimum keys are schema/study/case IDs, split, replicate, seed, signal family, n/fs, method and settings hash, target/reference IDs, band/response-group ID, estimate/reference value, metric, validity/reason, and diagnostic version. Pair methods by case/replicate before computing differences. Method failure or an unavailable quantity is an explicit record, never silently dropped or replaced by zero.

Each family has its own reference definition. A population PSD expectation and a finite realization's DFT power are different references. Metrics must state which is used. Ratios near zero need declared handling; do not stabilize them with an unexplained epsilon.

## 8. Numerical and computational limits

Dense operator construction is for small records only. Default operator cap: `n <= 512`, with an explicit opt-in up to a documented memory budget; do not build many `n x n` matrices at n=8192 by accident. Store Hermitian/symmetric matrices in float64/complex128 and check direct-versus-quadratic agreement. At larger n, use direct measurements and finite frequency probes; any iterative norm estimate is labeled an estimate rather than a certified upper bound.

Development studies should be expressible as a short smoke subset and a bounded full configuration. Estimate case count and resource use before execution. A provisional target is a demo under several seconds and CI under a few minutes on a typical CPU, but timing is measured and reported rather than a universal pass/fail rule. Cache fixed operators keyed by complete settings/shape/version hash.

Use a local `numpy.random.Generator` for stochastic experiments. Derive case seeds from stable canonical case identifiers and a declared master seed using a documented cryptographic hash or SeedSequence scheme. Never depend on Python's randomized `hash()` or on loop order to determine the signal. Pair estimator inputs exactly and verify identical sample hashes.

## 9. Documentation and release behavior

README sections: purpose; implemented status; quick start; example interpretation; scope/limitations; research protocol; roadmap; development; citation/license. An initial README may show the closed-form fixture expectations and the actual demo output if the demo has run. It must not report unperformed cross-method experiments, invented speedups, or scientific validation.

Public documents may be copied from this package. Handoff instructions, administrative context, local execution transcripts, and unrelated private source files stay outside the committed project. Repository `AGENTS.md` should be project-scoped and should not incorporate private program instructions.

M4 release artifacts should include a concise report, selected reproducible evidence, configuration files, and a manifest identifying the source commit. Large generated runs belong in a deliberate release artifact rather than ordinary source history. Choosing a citation DOI, uploading a release, or publishing to a package index are later explicit tasks, not part of M0 bootstrap.

## 10. Change control

Scientific contracts take precedence over convenience defaults. Resolve an ambiguity by documenting the decision and adding a meaningful check. If protocol and software disagree, fix the inconsistency before accepting output. After confirmation is frozen, changing a method, threshold, target, or comparison creates a new protocol version; previously viewed confirmation results then become development evidence for that revision.

