# Spectral Audit

Spectral Audit studies when classical spectral and multiresolution band-power measurements can be compared. This repository currently implements **M0 only**: a strict synthetic two-tone configuration, a unitary finite-record DFT band reference, a deterministic CLI run, and numerical/provenance checks. The DFT result is a measurement of the declared finite record, not an estimate of an unknown continuous spectrum or a cross-method research finding.

## Quick start

Requires Python 3.11 or newer. In a project virtual environment:

```sh
python -m venv .venv
# Activate .venv for your shell, then:
python -m pip install -r requirements-lock.txt
python -m pip install --no-deps -e '.[dev]'
spectral-audit --help
spectral-audit --version
spectral-audit demo --config configs/m0_tones.toml --out results/m0_demo
```

The lock records the tested CPython 3.11 Windows environment. On another platform, use compatible resolved packages if a pinned wheel is unavailable, and record that environment separately. Refresh the lock in a fresh environment with `python -m pip install -e '.[dev]'` followed by `python -m pip freeze --exclude-editable > requirements-lock.txt`, then rerun tests, lint, and the demo. The project-local editable distribution is omitted from the lock intentionally.

## Example interpretation

The supplied fixture uses 128 Hz sampling, 256 samples, no demeaning, and coherent 8 Hz and 24 Hz sine tones of amplitudes 1 and 0.5. The **analytic expectations** for bands `[0,16)`, `[16,32)`, and `[32,64]` Hz are mean-square powers `0.5`, `0.125`, and `0` in `(a.u.)^2`. Total record mean square is `0.625`; fractions of actual record power are `0.8`, `0.2`, and `0`. Binary floating-point output can contain a tiny positive value for the analytically zero band.

The command writes `band_powers.csv` with absolute powers and explicitly denominated fractions, `summary.json` with accounting, and `manifest.json` with source/configuration/signal/output hashes and truthful Git state. An existing nonempty output directory is refused. A zero-power record has zero absolute band powers and undefined fractions with `zero_reference_power` reasons.

## Development and scope

Run `python -m pytest -q` and `python -m ruff check .`. Tests include independent rFFT and explicit-DFT checks, endpoint and scaling cases, strict configuration rejection, deterministic artifacts, and manifest digests.

The [research protocol](docs/RESEARCH_PROTOCOL.md) defines the measurement targets. See the [engineering specification](docs/ENGINEERING_SPEC.md), [acceptance criteria](docs/ACCEPTANCE_CRITERIA.md), [roadmap](docs/ROADMAP.md), and [references](docs/REFERENCES.md). M1 plans estimator contracts and Welch/STFT/DWT measurements; M2 plans finite operators and diagnostics; M3 plans development studies; M4 plans frozen confirmation and a report. These later methods and results are **not implemented**.

## Citation and license

If citing this bootstrap, identify its version and source commit rather than treating it as a research result. New project code is MIT licensed; see [LICENSE](LICENSE). Referenced research and software retain their own licenses and attribution.
