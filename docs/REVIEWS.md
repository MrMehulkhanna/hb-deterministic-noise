# Academic reviews (control-stage report, 2026-10-08)

> Both reviews must be repeated after Group E results exist.

## Review A: evidence consistency
**Method:** a script extracted every decimal number with 3 or more decimal places from `report/report.md` (75 numbers) and matched each against all numeric values in `outputs/*.csv`, group means of the suites, and `outputs/results_summary.json`.

**Result:** 75/75 traced. The script initially flagged 4 numbers, all false alarms:
- three were DOI or arXiv identifiers;
- one, 0.006592, appears in the report with a Unicode minus sign (−0.006592) and matches the data.

| File / location | Issue | Correction | Evidence |
|---|---|---|---|
| Report v2 §6 | 8-bit secret printed for n=10; family not named | `x = 0000101101`; keyed control named; random family added | `canonical_n10_curves.csv` |
| Report v2 §5 table | k99 values from the biased estimator | Replaced with tie-aware values; "not reached" made explicit | `control_suite_B_*.csv` |
| Report v2 §6 / app demo tab | k99 = 25 | 51 | A1, `canonical_n10_curves.csv` |
| CSV `secret_bits` | Leading zeros lost on re-read | `b` prefix | `group_D_toy_controls.csv` |
| Keyed control suite | 5 repetitions identical (A8) | Distinct keys; per-row truth-table hash | `audits/pre_A8_outputs/` vs `outputs/` |
| §8 bound | Constant differs from the tight Hoeffding derivation | Documented as sufficient (larger), kept | `docs/METHOD_AND_DERIVATIONS.md` §4 |

Integer claims checked by hand against `results_summary.json`:
- 80/80 positive (B);
- 4 non-positive keyed tables (2 negative, 2 tie);
- 15/15 tests;
- 432 and 429 bounds;
- k99 = 51.

## Review B: research communication
| Check | Finding | Action |
|---|---|---|
| Undefined terms | Q2 is defined in §5; Δ in §8; k99 and the estimator in §9; "exact / MC / bound" labels in §9 | None needed |
| "Majority vote" wording | Absent from the report | Kept as "categorical mode estimation" |
| Overclaiming | Banned-word scan (novel, first, state of the art, outperforms, breaks) finds only negated uses | None |
| Keyed-control labelling | Called "not a PRF" at every occurrence in report, packet and figures | None |
| Observation vs interpretation | The n=8, τ=0.4 family difference is explicitly *not* interpreted as systematic | Kept |
| Relation to known theory | Report states the mechanism is an instance of quantum Goldreich–Levin-type Fourier sampling | Kept prominent (§16, §18) |
| Figure captions | Fig. 1 notes coinciding markers; Fig. 2 shows the tie rate; Fig. 3 states the Δ values; Fig. 4 is labelled "sufficient, not tight" | Updated in `reproduce.py` |
| Repetition | The abstract and §15 overlap slightly | Acceptable for a technical report |

