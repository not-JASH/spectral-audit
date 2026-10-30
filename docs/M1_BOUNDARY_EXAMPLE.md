# Bounded db4 boundary audit

Run in the project Python 3.11 environment from the repository root. Use fresh
output directories:

```sh
spectral-audit boundary-audit --config configs/m1_db4_boundaries.toml --out results/db4_a
spectral-audit boundary-audit --config configs/m1_db4_boundaries.toml --out results/db4_b
python -m pytest -q
python -m ruff check .
python -m pip check
```

The configuration resolves 128 Hz, 30/31/32 samples, six exact constructions
per length (ones, first/middle/final unit impulses, `j/(n-1)`, and
`(-1)^j*(j+1)/n`), and both modes on identical records. A separate 64-sample
panel uses unit-amplitude cosine and sine at all coherent bins `k=0..32`.
`summary.json` records constructions, per-level ledgers and accounting;
`native_groups.csv`, `mode_comparisons.csv`, and `responses.csv` expose the
numerical results. `manifest.json` is written last and hashes every output,
input record, source file inventory, configuration and dependency identity.

## Independent expectations and development observations

The table gives analytical coefficient-count expectations, confirmed by a
local development run on 2026-10-30 in `results/m1_boundary_verified_a/`.
That precommit manifest identifies `source_state=dirty`, base revision
`ca710be7e117732807c5d59f9c05d29df926c766`, and source digest
`ea48c923325ceb7f23d0f3f4b241126ee41d8bff9c5a7fbb46b010687bd409f3`.
The totals in the final column are
observed **ones-record** sums of squared coefficients divided by original `n`,
rounded to 12 digits. They are not claimed for arbitrary records.

| n | mode | A2, D2, D1 counts | total count | ones normalized total |
| ---: | --- | --- | ---: | ---: |
| 30 | periodization | 8, 8, 15 | 31 | 1.066666666667 |
| 30 | periodic | 12, 12, 18 | 42 | 1.6 |
| 31 | periodization | 8, 8, 16 | 32 | 1.032258064516 |
| 31 | periodic | 13, 13, 19 | 45 | 1.677419354839 |
| 32 | periodization | 8, 8, 16 | 32 | 1 |
| 32 | periodic | 13, 13, 19 | 45 | 1.625 |
| 64 | periodization | 16, 16, 32 | 64 | 1 (analytical) |
| 64 | periodic | 21, 21, 35 | 77 | 1.3125 (analytical) |

For `ones(32)`, periodization has eight A2 values of 2 and total coefficient
energy 32. Periodic has thirteen A2 values of 2 and total energy 52; detail
values are approximately zero. The periodic normalized total is 13/8. Dividing
52 by the coefficient-count ratio 45/32 gives 52/45, not one. For
periodization, `ones(31)` gives 32/31 and `ones(30)` gives 32/30. The latter
duplicates the final *level-one approximation* at level two; it does not pad
the original 30-sample record to 32 samples. A 31-sample final unit impulse
gives 2/31; an interior unit impulse gives 1/31.

For periodization, independent accounting is
`sum_g sum(c_g²) = sum(x²) + (n odd)*x[-1]² + (len(a1) odd)*a1[-1]²`.
The direct reference supplies `a1` independently of production PyWavelets
coefficients. Periodic accounting uses the direct finite filter-bank output.
Observed local development residuals for the ones cases were at most
`2.3e-16` in record-power units. Across all 198 response rows, the maximum
absolute observed residual was `1.3e-15` (rounded upward). Circular cascade
formulas apply only to compatible periodization; periodic rows use the finite
reference and mark the circular formula unavailable. The response is the
**sum**, not the average, of cosine and sine group energies divided by unit
amplitude squared. The three periodization responses sum to one.

The checked-in taps and high-pass construction are attributed to the
[PyWavelets v1.9.0 filter table](https://github.com/PyWavelets/pywt/blob/v1.9.0/pywt/_extensions/c/wavelets_coeffs.template.h)
and [wavelet construction](https://github.com/PyWavelets/pywt/blob/v1.9.0/pywt/_extensions/c/wavelets.c).
The source table lists the db4 low-pass taps in the reverse order of the
runtime decomposition filter; the construction supplies that orientation.
The direct reference's offset conventions follow its
[convolution implementation](https://github.com/PyWavelets/pywt/blob/v1.9.0/pywt/_extensions/c/convolution.template.c).
Tests compare signed arrays and verify the checked-in taps against the runtime
filter bank separately. In the project environment, the installed distribution
reported 1.9.0 while `pywt.__version__` reported 1.8.0; the imported module
resolved inside `.venv`. The tagged upstream
[project metadata](https://github.com/PyWavelets/pywt/blob/v1.9.0/pyproject.toml)
declares 1.9.0 while its
[runtime-version generator](https://github.com/PyWavelets/pywt/blob/v1.9.0/util/version_utils.py)
still declares 1.8.0. That upstream metadata is a plausible explanation, not
independent identification of the installed files. Both actual version strings
are preserved in the manifest.

Mode differences compare declared finite measurements. Periodization is a
comparison baseline, not a universally correct continuation. Structural
extension dependencies indicate support, not error. No hard Fourier-band
equivalence, population target, numerical correction by redundancy ratio, or
research conclusion follows from these fixtures. Other extension modes,
broader offset controls and matched-target comparison controls remain open.
