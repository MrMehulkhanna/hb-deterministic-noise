# Claim / evidence ledger (updated 2026-10-08)

| Claim | Status | Evidence | Safe wording |
|---|---|---|---|
| BV output distribution = secret-shifted squared Walsh spectrum | **Verified** | METHOD §1; test "BV distribution equals…" | "Under the ideal Q2 phase-oracle model, P(j) = ĥ(x⊕j)²." |
| P(x) = (1−2τ_realised)² for an exact fixed-weight table | **Verified** | METHOD §2; max identity error 2.0e-15 over 160 rows | "For an exact fixed-weight truth table…" |
| Bernoulli (constant) error gives P(x) = 1 | **Verified** | `group_A_bernoulli.csv` (min 1.0) | Reproduces CEG 2026 §7.1 in simulation |
| Random fixed-weight controls (B): positive gap at all tested points | **Measured** | `control_suite_B_*.csv`: 80/80 positive, min Δ 0.006104 | "In this finite control suite (n = 8–14, 5 tables per point)…" |
| Keyed control (C, not a PRF): Δ ≤ 0 for 4/5 tables at n=8, τ=0.4 | **Measured** | `control_suite_C_*.csv`, `gap_class` | "At n=8, τ=0.4 the secret was not uniquely modal in 4 of 5 keyed control tables." Do **not** generalise. |
| Canonical n=10, τ=0.25: tie-aware k99 = 51 (both B and C) | **Measured** | `canonical_n10_curves.csv`; 300 trials; grid K_GRID | "Empirical k99 = 51 on the checked grid (0.970 at k = 25)." |
| Pre-audit k99 values (incl. 25) | **Superseded** | A1 | Do not use |
| AND-2: exact zero gap; repeated queries do not raise P[unique mode = secret] above about 0.25 | **Verified + measured** | `group_D_toy_controls.csv`: 0.250 / 0.184 / 0.237 / 0.244 at k = 1 / 25 / 101 / 401 | "Structural spectral tie" |
| Sufficient bound is conservative | **Verified + measured** | METHOD §4; Fig. 4 | "Sufficient, not tight" |
| 5% output depolarising keeps Δ > 0 in the canonical keyed example | **Measured** | `group_F_depolarising.csv` (Δ 0.2380 → 0.2261) | "Robustness check only; not a physical noise model" |
| ePrint 2026/2258 §8.2 suggests deterministic error is more robust (Dilithium) | **Verified quote** | literature file | "…a heuristic remark about Dilithium" |
| Keyed control is a PRF | **Unsupported** | — | **Do not claim** |
| Real deterministic-LPN is broken or secure | **Unsupported** | Group E not run | **Do not claim** |
| Results refute CEG ePrint 2026/2258 §8.2 | **Unsupported** | Different scheme and oracle | **Do not claim** |
| Novel / first | **Open** | Search incomplete (open item 4) | **Do not claim** |
| Asymptotic statements | **Unsupported** | n ≤ 14 exact enumeration | **Do not claim** |
