# Observed bounded M1 comparison audit

The following run used the project CPython 3.11 environment on 2026-10-30. It was generated from clean source revision `b8f508853644037ecd8c12a4636ae1c410b929cd`; its manifest recorded source digest `fe7d9d597b281526f465f955ffd6836b95a5263d8205622dab65f3528654efad` and configuration SHA-256 `e4d8a54920f4e8bd1e4cf5021c481a29046519636273d0823deb8a8549ce7033`. The generated files are in `results/m1_comparison_clean_b8f5088/` in the local project workspace and are ignored by Git.

```powershell
.\.venv\Scripts\python.exe -m spectral_audit comparison-audit --config configs/m1_comparison_controls.toml --out results/m1_comparison_clean_b8f5088
```

The 38 declared controls produced 17 `accepted`, 14 `refused`, 3 `unavailable`, and 4 `invalid` decisions, with no unexpected outcomes. Among the predefined exact-target controls, false acceptances were 0/14 and false rejections 0/14. Three accepted comparisons were descriptive, and one accepted ratio relationship had an unavailable numerical metric. These counts only characterize this fixed control suite.

| Control | Observed decision and numerical result | Rule or reason |
| --- | --- | --- |
| Direct record power versus DFT total | Accepted, agreement; `0.62499999999999989` versus `0.62499999999999978` `(a.u.)^2` | `B_actual_record_mean_square_v1`, complete bin partition |
| Haar total versus DFT total | Accepted, agreement; signed difference `3.3306690738754696e-16` `(a.u.)^2` | Rule B, complete orthonormal groups |
| Compatible db4 periodization total versus direct power | Accepted, agreement; both `0.03125` `(V)^2` | Rule B, length 32 and all groups retained |
| Haar `A2` mean square conversion | Accepted, agreement; candidate `2.1005028016306468` times factor `0.25` gives record contribution `0.52512570040766171` `(a.u.)^2` | `C_native_mean_to_record_energy_v1` |
| Redundant db4 `periodic` group conversion | Accepted, agreement; factor `0.40625` | Rule C; no total-partition claim |
| Perturbed matched band | Target accepted, numerical disagreement; signed difference `0.099999999999999978` `(a.u.)^2` | Rule A; labeled injected value fault |
| Coincident DFT/Welch low bands requested as exact | Refused despite equal printed values `0.49999999999999978` | Different finite-record functionals |
| Edge-tone DFT/Welch low bands requested descriptively | Accepted descriptively; candidate minus reference `0.083333333333333356` `(a.u.)^2` | `D_dft_welch_band_v1` |
| Length-31 periodization impulse total versus original power | Refused despite equal values `0.032258064516129031` `(V)^2` | Rule B length precondition fails |
| Unknown method or population request | Unavailable, no difference | Missing supported mapping |
| Contradictory settings hash or impossible coefficient count | Invalid, no difference | Malformed control fixture |
| Matched zero-denominator ratio | Target accepted; numerical metric unavailable | `zero_denominator` |

The audit writes `comparison_controls.csv`, `summary.json`, and a last-written `manifest.json` containing every output hash and the full source inventory. See [COMPARISON_CONTRACT.md](COMPARISON_CONTRACT.md) for the rule preconditions and limits. The controls include deliberate malformed fixtures; they are not observed production-estimator failures.
