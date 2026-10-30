# Bounded Haar DWT implementation example

These tables are rounded from **observed** clean-revision runs in ignored
directories `results/m1_dwt_tones_a233175/`, `results/m1_dwt_phase0_a233175/`,
and `results/m1_dwt_phase90_a233175/`. Their manifests record source revision
`a233175615ace9a00b19280bd069d0644d830887`, source digest
`d79bcdaeb8b1ab58ab82d75c1be9296d037511704d4b025faa1d0a8f5649f086`,
and clean source state. The environment was Windows, Python 3.11.9, NumPy 2.4.6,
SciPy 1.17.1, with installed PyWavelets distribution 1.9.0. The import reports
`pywt.__version__ = 1.8.0`; both values are in each v3 manifest. This is an
implementation example, with no asserted population target or novelty finding.

Run from the repository root in the installed project Python 3.11 environment.
Use fresh output directories:

```sh
spectral-audit measure --config configs/m1_dwt_tones.toml --out results/repro_dwt_tones
spectral-audit measure --config configs/m1_dwt_16hz_phase0.toml --out results/repro_dwt_phase0
spectral-audit measure --config configs/m1_dwt_16hz_phase90.toml --out results/repro_dwt_phase90
```

## Exact Fourier-band outputs

These are DFT/Welch powers from `comparisons.csv`, in `(a.u.)^2`. The intervals
retain the exact Fourier-bin endpoint convention. Values written `~0` were
floating-point residues, below `1e-28` in these runs.

| Record | Fourier band (Hz) | DFT | Welch |
| --- | --- | ---: | ---: |
| 8 + 24 Hz tones | [0,16) | 0.5 | 0.5 |
| 8 + 24 Hz tones | [16,32) | 0.125 | 0.125 |
| 8 + 24 Hz tones | [32,64] | ~0 | ~0 |
| 16 Hz, phase 0 | [0,16) | ~0 | 0.08333333333333336 |
| 16 Hz, phase 0 | [16,32) | 0.5 | 0.4166666666666665 |
| 16 Hz, phase 0 | [32,64] | ~0 | ~0 |
| 16 Hz, phase π/2 | [0,16) | ~0 | 0.08333333333333355 |
| 16 Hz, phase π/2 | [16,32) | 0.5 | 0.4166666666666672 |
| 16 Hz, phase π/2 | [32,64] | ~0 | ~0 |

## Native Haar groups

These are from `native_scales.csv` and have **nominal** frequency annotations,
not exact Fourier passbands. Both numerical columns have `(a.u.)^2` units.
Counts are 64, 64, and 128 for `A2`, `D2`, and `D1`, respectively, in every case.

| Record | Native group (nominal Hz) | Record-power contribution `sum(c²)/256` | Coefficient mean square `sum(c²)/count` |
| --- | --- | ---: | ---: |
| 8 + 24 Hz tones | A2 (~0–16) | 0.5251257004076617 | 2.1005028016306468 |
| 8 + 24 Hz tones | D2 (~16–32) | 0.04226189724297804 | 0.16904758897191216 |
| 8 + 24 Hz tones | D1 (~32–64) | 0.05761240234936034 | 0.11522480469872068 |
| 16 Hz, phase 0 | A2 (~0–16) | 0.3642766952966355 | 1.457106781186542 |
| 16 Hz, phase 0 | D2 (~16–32) | 0.06250000000000125 | 0.250000000000005 |
| 16 Hz, phase 0 | D1 (~32–64) | 0.07322330470336315 | 0.1464466094067263 |
| 16 Hz, phase π/2 | A2 (~0–16) | 0.06250000000000222 | 0.2500000000000089 |
| 16 Hz, phase π/2 | D2 (~16–32) | 0.3642766952966350 | 1.4571067811865401 |
| 16 Hz, phase π/2 | D1 (~32–64) | 0.07322330470336315 | 0.1464466094067263 |

The native contributions sum to the actual record mean square: about `0.625`
for the two-tone record and `0.5` for either 16 Hz phase. Coefficient mean
squares use a different denominator and do not have this sum identity. The
hand fixture `[1,2,3,4,5,6,7,8]` independently checks contributions
`[24.25,1,0.25]` and coefficient mean squares `[97,4,0.5]`; its constant
`D2` coefficients have centered variance zero, despite mean square four.

For the 16 Hz phase-zero sine, the tested analytical native contributions are
`[(3+2√2)/16, 1/16, (2−√2)/8]`. At phase π/2, `A2` and `D2` swap and `D1`
stays the same. The DFT measurement assigns about `0.5` to `[16,32)` in both
records. This is phase/alignment sensitivity of the declared finite decimated
transform. It does not, by itself, imply a library defect, population bias, or
boundary artifact. Native rows leave `difference_from_dft` unavailable with
reason `native_scale_not_exact_fourier_band`.

The supplied 64-sample periodic-Hann Welch preset is unchanged. Each manifest
hashes its `comparisons.csv`, `native_scales.csv`, and `summary.json`, as well as
the resolved configuration, input record, and source inventory. See
[MEASURE_CONTRACT.md](MEASURE_CONTRACT.md) for exact normalization and status
fields. Full M1 still needs longer-filter boundary comparisons and response
checks; this example supports only the bounded Haar configuration.
