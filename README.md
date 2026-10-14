# Spectral Leakage and Repeated Bernstein–Vazirani Key Recovery under Deterministic, Input-Dependent Noise

**Status: INCOMPLETE.** The control framework is verified. The published deterministic-LPN construction experiment is pending. See [PROJECT_STATUS.md](PROJECT_STATUS.md).

## Question
When does deterministic, input-dependent noise suppress or preserve Bernstein–Vazirani key recovery against LPN-based (HB-family) authentication under Q2 superposition access?

Operationally: which properties of the noise function's Walsh spectrum keep the secret as the unique most probable BV output?

## Core result (exact, ideal Q2 phase oracle)
`P(j) = ĥ(x⊕j)²` with `h = (−1)^e`. For an exact fixed-weight table, `P(x) = (1−2τ)²`. Recovery by repeated queries is governed by `Δ = P(x) − max_{u≠0} ĥ(u)²`.

## Main measurements (controls only)
- **Random fixed-weight noise:** Δ > 0 in 80/80 tables (n = 8–14).
- **Canonical example** (n = 10, x = 0000101101, τ = 0.25): tie-aware k99 = 51 queries.
- **Keyed control** (not a PRF), n = 8, τ = 0.4: Δ ≤ 0 in 4/5 tables.
- **AND-2 noise:** exact tie (Δ = 0) that repeated queries do not resolve.

Full report: [report/report.pdf](report/report.pdf).

## Reproduce
```bash
pip install -r requirements.txt
python tests/test_core.py && python reproduce.py     # about 35 s, writes outputs/
```

## Layout
| Path | Content |
|---|---|
| `research_app.py` | Core maths, controls, estimator, analysis; optional Gradio UI (`python research_app.py`) |
| `reproduce.py` | Groups A–D and F, figures, manifest |
| `analyse_construction.py` | Group E analysis for a verified construction truth table (needs a prediction file) |
| `tests/` | 15 regression and correctness tests |
| `outputs/` | Raw CSVs, figures, environment, SHA-256 manifest |
| `docs/` | Derivations, literature and novelty, search log, claim ledger, reproducibility, reviews |
| `audits/` | Audit log A1–A8, first-audit reproduction, pre-audit test evidence |
| `constructions/`, `notes/predictions/` | Group E specification rules and prediction template |
| `professor_packet/`, `submission/`, `public_site/` | Reader packet, release metadata, landing page |

## Source paper
C. Cid, D. Elkouss, M. Goulão, *Superposition Attacks Against LPN-Based Authentication Protocols*, IACR Communications in Cryptology 3(1), 2026. doi:10.62056/abhey7n4e

## Citation and license
MIT License (see [LICENSE](LICENSE)). To cite this work, use [CITATION.cff](CITATION.cff).
