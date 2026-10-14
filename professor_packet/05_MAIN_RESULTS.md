# Main results (all from ../outputs/; E = exact, MC = Monte Carlo, B = bound)

| Result | Value | Type | Source file |
|---|---|---|---|
| Bernoulli (global-phase) control | P(x) = 1 for all n, both error bits | E | group_A_bernoulli.csv |
| Fixed-weight identity error, max over 160 tables | 2.0e-15 | E | results_summary.json |
| Random fixed-weight: tables with Δ > 0 | 80 / 80; min Δ = 0.006104; mean P(x) = 0.415548 | E | control_suite_B_*.csv |
| Keyed control (not a PRF): Δ ≤ 0 | 4 / 80 tables, all at n = 8, τ = 0.4 (2 negative, 2 ties) | E | control_suite_C_*.csv |
| Canonical n = 10, x = 0000101101, τ = 0.25: Δ | 0.23803711 (keyed) / 0.23887634 (random) | E | canonical_n10_curves.csv |
| Canonical k99 | 51 for both (0.970 at k = 25), 300 trials | MC | canonical_n10_curves.csv |
| Canonical sufficient bound | 432 / 429 | B | results_summary.json |
| AND-2 P[unique mode = secret] at k = 1 / 25 / 101 / 401 | 0.250 / 0.184 / 0.237 / 0.244 (Δ = 0) | MC | group_D_toy_controls.csv |
| Depolarising ε = 0.05 / 0.5: Δ | 0.2261 / 0.1190 | E | group_F_depolarising.csv |
