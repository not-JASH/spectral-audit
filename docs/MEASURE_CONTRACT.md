# Bounded M1 measurement contract

`spectral-audit measure --config <file> --out <new-or-empty-dir>` accepts strict TOML
schema version 2. It retains schema-v1 `record`, `signal`, `bands`, and `reference`
sections and their validation, and requires a `[welch]` table. Unknown top-level,
section, or method keys are errors. The command generates one deterministic tone
record, then passes that same record to the finite-record DFT reference and Welch.
Schema v1 remains the `demo` interface.

The `[welch]` table requires `method_id = "welch_mean_density_v1"`, integer
`segment_length`, and integer `noverlap`. Optional fields, resolved before hashing,
are `nfft = segment_length`, `taper = "hann_periodic"`, `detrend = false`,
`sidedness = "onesided"`, `scaling = "density"`, `average = "mean"`,
`boundary = "none"`, and `padding = "none"`. Any other value is rejected.
Require `2 <= segment_length <= n`, `0 <= noverlap < segment_length`, and
`nfft = segment_length`; booleans do not count as integers. The 64/32 preset uses
seven starts `[0,32,64,96,128,160,192]` for the 256-sample record.

The Welch measurement kind is `finite_record_windowed_band_power`, with no
asserted population target. For complete frames starting at zero, periodic Hann
`w = scipy.signal.windows.hann(L, sym=False)`, `U = sum(w**2)`, and unnormalized
frame DFT `Z`, the mean one-sided density is
`S[k] = sum_r d[k]|Z[r,k]|**2 / (K fs U)`. Multiplicity `d` is one at DC and an
existing even-length Nyquist bin, two at interior positive bins. A band power is
`(fs/L) * sum(S[k] for k in band)`. Internal upper edges are excluded; the final
Nyquist upper edge is included. A band without estimator bins is rejected, never
reported as measured zero. Density units are sample-unit squared per Hz; integrated
band and total powers are sample-unit squared. There is no padding, boundary
extension, global demeaning, or frame detrending.

`method_total_power` is independently evaluated as
`sum_r,t(w[t]**2 * x[start_r+t]**2)/(K U)` and checked against the spectral bin
sum. `record_power` is `sum_j(x[j]**2)/n`; their signed difference is descriptive.
`record_power_fraction` divides by the latter. `method_total_fraction` divides
by the former. A zero denominator gives JSON `null` or blank CSV with a specific
reason, while absolute zero power remains valid. Support metadata separates
omitted samples from covered samples with zero taper weight.

The output schema is version 2: `comparisons.csv` has one row per method and band,
with record and settings hashes, measurement kind, bounds, power/unit and status,
both totals and fractions with separate status/reason, reference ID, and signed
`difference_from_dft`. `summary.json` records complete method settings, support,
units, and comparison labels. The comparison is **descriptive**: matching band
names or equal totals do not establish equivalent operators or a population bias.
`manifest.json` is written atomically last; it contains the resolved configuration
and hash, source/configuration/signal/output hashes, environment versions, and
truthful Git state. Its declared source inventory covers package Python files,
`pyproject.toml`, and `requirements-lock.txt`. Numerical files are deterministic
within an unchanged environment; generated run directories are ignored.

## Strict schema v3: finite Haar native scales

Schema v3 retains all schema-v2 sections and requires `[dwt]` with exactly
`method_id = "dwt_haar_periodization_level2_v1"`, `wavelet = "haar"`,
`level = 2`, and `mode = "periodization"`. Unknown or unsupported keys and
values are errors; v1 and v2 do not accept `[dwt]`. The complete resolved
settings are hashed. The record must be a finite real vector with at least four
samples and length divisible by four; powers of two are unnecessary. The
adapter calls `pywt.wavedec` with these settings explicitly. It does not demean,
detrend, pad, trim, threshold, or discard coefficients. The supported
`periodization` family has no length extension for these compatible records;
`periodic` is a distinct, unsupported mode.

The result has native groups `A2`, `D2`, `D1` in that order, with counts
`n/4`, `n/4`, `n/2`. Its support kind is `native_scale_group`, never an exact
Fourier `Band`. For each coefficient group `g`, `native_scale_record_power`
is `sum(c_g**2)/n` and `native_scale_coefficient_mean_square` is
`sum(c_g**2)/count(g)`. The relationship is
`record contribution = count(g)/n * coefficient mean square`. Both have
sample-unit-squared units. Neither is a centered coefficient variance. The
orthonormal transform preserves the record mean square when all groups are
retained, as checked independently for this finite configuration.

`record_power_fraction` divides by actual record mean square, and
`method_total_fraction` divides by the sum of native record contributions.
Zero absolute quantities are valid. A zero denominator produces an undefined
fraction with `zero_record_power` or `zero_method_total_power`. Nonfinite
calculation stops with a numerical-range error. At `fs = 128` Hz, nominal
annotations are `A2: 0–16`, `D2: 16–32`, and `D1: 32–64` Hz; these are
approximate associations and have no exact Fourier endpoint rule.

Schema-v3 `comparisons.csv` keeps the exact-band DFT/Welch rows and their
descriptive differences. `native_scales.csv` has the native group counts,
quantities, totals, fractions, units, and per-quantity validity. Its
`difference_from_dft` is blank with unavailable reason
`native_scale_not_exact_fourier_band`. `summary.json` contains all three
methods with distinct measurement and support kinds; only Welch carries a
density unit. `manifest.json` is written atomically last and hashes every
scientific output. It records both PyWavelets' runtime-reported version and
installed distribution version, as well as the DWT source module in the source
inventory. The same generated record is passed to each method, and identity,
rate, length, units, and preprocessing are checked before writing.
