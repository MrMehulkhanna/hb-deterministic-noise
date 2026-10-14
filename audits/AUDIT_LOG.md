# Audit log: completion pass (2026-10-08)

## 0. What was received
- The handoff referred to `hb_research_final` / its ZIP. **It was not received.** Only loose files were present in `~/Downloads`:
  - `00_START_HERE`, `FINAL_PACKAGE_MAP`, `PUBLISHING_COMMANDS`, `MASTER_COMPLETION_PROMPT`;
  - `research_report` v2 (pdf, md) and v3 (pdf), `CLAIM_EVIDENCE_LEDGER` and planning notes;
  - `research_app.py` (sha256 `9a354f1b…25af`).
- **Missing**, so not inspected: the package's original `tests/test_core.py`, `outputs/experiment_suite*.csv`, `docs/LITERATURE_AND_NOVELTY.md`, the original `docs/novelty_search_log.md`, `PROJECT_STATUS.md`, other `audits/*`, and the "Concrete construction" tab code mentioned in the handoff.
- This directory was therefore **rebuilt** from `research_app.py` and the first audit.

## 1. Discrepancies found (none silently fixed)

| ID | Item | Evidence | Resolution |
|---|---|---|---|
| A1 | `sample_mode` broke empirical ties toward the smallest index | `tests_against_pre_audit_app.txt`: both A1 tests FAIL on the pre-audit app | Ties now return `None` and count as failure. Two regression tests added. |
| A1-consequence | Report v2 said canonical n=10 k99 = 25; tie-aware value is **51** (0.970 at k=25) | `outputs/canonical_n10_curves.csv` | 25 is superseded. Report v3 already stated 51; confirmed independently. |
| A1-consequence | **All** per-cell k99 values in report v2's §5 table are superseded | Compare `audits/first_audit_2026-10-08/reproduced_experiment_suite.csv` (argmax) with `outputs/control_suite_B_*.csv` | e.g. n=10, τ=0.05: 3 → 5; n=10, τ=0.4: 401 → "401 or not reached". Exact columns (P(key), Δ, realised τ) are unchanged. |
| A1-new | Small-k artefact: P[unique mode = secret] is 0.27 at k=1 but 0.12 at k=3 (tie rate 0.87) | `canonical_n10_curves.csv` | Documented in METHOD §5 and the report. Not a bug: ties count as failures. |
| A2 | Report v2 §6 printed an 8-bit secret for n=10 and did not name the family | Report v2 | Secret is `x = 0000101101`. Numbers come from the **keyed research control (not a PRF)**. Both families now reported. |
| A2-CSV | Bit strings lost leading zeros when CSVs were re-read | Observed during this pass | CSV bit strings carry a `b` prefix, e.g. `b0000101101`. |
| A3 | `n/P(key)` was labelled "classical heuristic" | Code | Renamed `bernoulli_hb_reference`; labelled not a deterministic-noise baseline; excluded from conclusions. |
| A4 | `most_likely_output` named the best competitor | Code | Renamed `best_competitor_output`; test added. |
| A5 | Grid, trials and not-reached cases undocumented | Code | `K_GRID` constant; `k99_status`; CSV columns `mc_trials`, `query_grid`, `k99_status`. |
| A6 | Fixed secret and seed rules undocumented | Code | Columns `secret_rule`/`seed_rule` in app suite; rules commented in `reproduce.py`. |
| A7 | Hoeffding constant | `docs/METHOD_AND_DERIVATIONS.md` §4 | Derivation gives `(2/Δ²)ln((2ⁿ−1)/δ)`. Implementation's `ln(2(2ⁿ−1)/δ)` is larger, hence still sufficient. Retained and documented. |
| **A8 (new)** | The keyed control ignores `seed`, so its 5 "repetitions" were **one** truth table counted 5 times. The first run showed "5 negative-gap rows", which was really 1 table. | `audits/pre_A8_outputs/` | Repetitions now use `noise_key = 12345 + rep`. Each row records its truth-table SHA-256; 80/80 distinct. |
| **New result** | With distinct keys, keyed control at n=8, τ=0.4 has Δ ≤ 0 for **4 of 5** tables: 2 negative (−0.006592), 2 exact ties (one numerically −2.1e-17). The random fixed-weight family has 0 of 80 non-positive. | `outputs/control_suite_C_*.csv`, `gap_class` column | Kept and reported. A small-n, high-τ fluctuation regime (P(x) = 0.041 is comparable to typical ĥ(u)²). **Not** evidence that the keyed control differs systematically from random placement: 5 samples only. |

## 2. Literature verification
- CEG 2026 (CiC): read in full.
- ePrint 2026/2258: the eprint.iacr.org copy is behind a bot check (not bypassed); the full PDF was obtained from the official mirror eprint.iacr.asia. §8.2 verified verbatim: their model does "not use the message in superposition"; deterministic error described as giving "a strong indication" of robustness for **Dilithium**. It does **not** analyse deterministic-LPN HB.
- ACNS 2026 chapter: existence verified (Springer). **Full text not accessed** (paywall). Group E blocked.

## 3. Tests
- `tests/test_core.py`: 15/15 pass on the final app.
- The same file run against the pre-audit app: 8/15 pass; both A1 tests fail, as required (`tests_against_pre_audit_app.txt`).
