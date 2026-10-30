# Bounded M1 Welch measure contract

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
