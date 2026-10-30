# First Welch comparison example

This is the bounded first Welch increment of M1. The table below is rounded from
the **observed** `comparisons.csv` files in ignored local runs
`results/m1-tones-1248c1b/` and `results/m1-edge-1248c1b/`. Both manifests
record clean source revision `1248c1b0870fc82458cf9cc9885ada43b69eb288`,
source digest `1c41ea2d4fa6a2c9992fcd9fbd887b153dc660168a80adc2c982691034e7a52e`,
Python 3.11.9, NumPy 2.4.6, and SciPy 1.17.1 on Windows. Generated runs are
ignored and are not part of the commit. The sample arrays are identical between
methods within each case; manifests contain their record hashes. The table is an
implementation observation, not a population-spectrum result.

| Case | Band (Hz) | DFT power | Welch power | Welch minus DFT |
| --- | --- | ---: | ---: | ---: |
| Two tones | [0,16) | 0.5 | 0.5 | ~0 |
| Two tones | [16,32) | 0.125 | 0.125 | ~0 |
| Two tones | [32,64] | ~0 | ~0 | ~0 |
| 16 Hz edge tone | [0,16) | ~0 | 0.08333333333333336 | +0.08333333333333336 |
| 16 Hz edge tone | [16,32) | 0.5 | 0.4166666666666665 | -0.08333333333333326 |
| 16 Hz edge tone | [32,64] | ~0 | ~0 | ~0 |

All powers and differences have units `(a.u.)^2`. `~0` denotes floating-point
residue in these deterministic tones, not a newly inferred physical component.
Both method totals are about 0.625 in the two-tone case and 0.5 in the edge-tone
case. The analytical fixture expectations were respectively
`[0.5, 0.125, 0]` for both methods and DFT `[0, 0.5, 0]` versus Welch
`[1/12, 5/12, 0]` for the edge tone; the observed outputs match within the
declared `1e-12` unit-scale tolerance. Equal total powers in the edge case do
not imply equal band measurements: the 64-sample periodic Hann spreads power
across the 16 Hz boundary. The DFT is an identified finite-record comparison
reference; `difference_from_dft` is descriptive and is not population bias.

Reproduce in a project Python 3.11 environment with the lock installed:

```sh
python -m pip install -r requirements-lock.txt
python -m pip install --no-deps -e '.[dev]'
python -m pytest -q
python -m ruff check .
spectral-audit demo --config configs/m0_tones.toml --out results/m0_reproduction
spectral-audit measure --config configs/m1_welch_tones.toml --out results/m1_tones_reproduction
spectral-audit measure --config configs/m1_welch_edge_tone.toml --out results/m1_edge_reproduction
```

Use fresh output directories: the CLI refuses nonempty ones. See
[MEASURE_CONTRACT.md](MEASURE_CONTRACT.md) for schema, units, support, and
denominator definitions. Full M1 still requires DWT and a broader prior-work
review; operator diagnostics and population studies are later milestones.
