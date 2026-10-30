# Spectral Audit

Spectral Audit studies when classical spectral and multiresolution band-power measurements can be compared. This repository implements M0 and bounded M1 Welch, Haar, db4 boundary, and paired-record comparison increments. Schema v2 describes DFT/Welch differences; schema v3 adds separately labeled native Haar groups. A separate boundary audit compares two-level db4 modes. The comparison audit checks supported exact targets and explicit descriptive differences against positive and negative controls. Full M1 remains open. The DFT result measures the declared finite record, not an unknown continuous spectrum.

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
spectral-audit measure --config configs/m1_welch_tones.toml --out results/m1_tones
spectral-audit measure --config configs/m1_welch_edge_tone.toml --out results/m1_edge
spectral-audit measure --config configs/m1_dwt_tones.toml --out results/m1_dwt_tones
spectral-audit measure --config configs/m1_dwt_16hz_phase0.toml --out results/m1_dwt_phase0
spectral-audit measure --config configs/m1_dwt_16hz_phase90.toml --out results/m1_dwt_phase90
spectral-audit boundary-audit --config configs/m1_db4_boundaries.toml --out results/m1_db4_boundaries
spectral-audit comparison-audit --config configs/m1_comparison_controls.toml --out results/m1_comparison_controls
```

The lock records the tested CPython 3.11 Windows environment. On another platform, use compatible resolved packages if a pinned wheel is unavailable, and record that environment separately. Refresh the lock in a fresh environment with `python -m pip install -e '.[dev]'` followed by `python -m pip freeze --exclude-editable > requirements-lock.txt`, then rerun tests, lint, and the demo. The project-local editable distribution is omitted from the lock intentionally.

## Example interpretation

The supplied fixture uses 128 Hz sampling, 256 samples, no demeaning, and coherent 8 Hz and 24 Hz sine tones of amplitudes 1 and 0.5. The **analytic expectations** for bands `[0,16)`, `[16,32)`, and `[32,64]` Hz are mean-square powers `0.5`, `0.125`, and `0` in `(a.u.)^2`. Total record mean square is `0.625`; fractions of actual record power are `0.8`, `0.2`, and `0`. Binary floating-point output can contain a tiny positive value for the analytically zero band.

The command writes `band_powers.csv` with absolute powers and explicitly denominated fractions, `summary.json` with accounting, and `manifest.json` with source/configuration/signal/output hashes and truthful Git state. An existing nonempty output directory is refused. A zero-power record has zero absolute band powers and undefined fractions with `zero_reference_power` reasons.

## Development and scope

Run `python -m pytest -q` and `python -m ruff check .`. Tests include independent rFFT and explicit-DFT checks, endpoint and scaling cases, strict configuration rejection, deterministic artifacts, and manifest digests.

The [research protocol](docs/RESEARCH_PROTOCOL.md) defines the measurement targets. See the [measure contract](docs/MEASURE_CONTRACT.md), [comparison contract](docs/COMPARISON_CONTRACT.md), [Welch example](docs/M1_WELCH_EXAMPLE.md), [Haar example](docs/M1_DWT_EXAMPLE.md), [db4 boundary example](docs/M1_BOUNDARY_EXAMPLE.md), [engineering specification](docs/ENGINEERING_SPEC.md), [acceptance criteria](docs/ACCEPTANCE_CRITERIA.md), [roadmap](docs/ROADMAP.md), and [references](docs/REFERENCES.md). Other extension modes, broader offset controls, general operators, diagnostics, development studies, and confirmation remain planned.

## Citation and license

If citing this bootstrap, identify its version and source commit rather than treating it as a research result. New project code is MIT licensed; see [LICENSE](LICENSE). Referenced research and software retain their own licenses and attribution.
