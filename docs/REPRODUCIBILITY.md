# Reproducibility

## One command
```bash
pip install -r requirements.txt          # numpy, pandas, matplotlib (gradio/reportlab optional, UI/export only)
python tests/test_core.py && python reproduce.py
```
Runtime: about 35 s on the reference machine below. It writes everything to `outputs/`:

| File | Content |
|---|---|
| `group_A_bernoulli.csv` | Global-phase control (exact) |
| `control_suite_B_random_fixed_weight.csv` | 80 rows; secret rule x = (7n+3) mod 2ⁿ; seed rule 1000+rep+31n |
| `control_suite_C_keyed_research_control_NOT_PRF.csv` | 80 rows; key rule 12345+rep (audit A8) |
| `canonical_n10_curves.csv` | n=10, x=0000101101, τ=0.25, seed 43, 300 trials per k, both families |
| `group_D_toy_controls.csv` | AND-1..4 and linear, n=10, 2000 trials per k |
| `group_F_depolarising.csv` | Output depolarising ε ∈ {0, 0.05, 0.1, 0.25, 0.5} |
| `fig1..fig4*.png` | Figures in the report |
| `results_summary.json` | Aggregates quoted in the report |
| `environment.json` | Python and package versions, OS |
| `MANIFEST.sha256` | SHA-256 of sources, CSVs, figures and JSON |

## Concrete construction (Group E, once unblocked)
```bash
python analyse_construction.py --table constructions/output/<file>.txt --secret <n bits> \
  --label "<id/version/params>" --prediction notes/predictions/concrete_construction_<date>.md
```

## Reference environment (this run)
See `outputs/environment.json`: Python 3.14.7, numpy 2.5.3, pandas 3.0.6, matplotlib 3.11.2, Linux x86_64.
No performance claims are made, so CPU details are not needed.

## Determinism
All randomness comes from `numpy.random.default_rng(seed)` with seeds recorded in each CSV. Re-running produces byte-identical CSVs on the same library versions. Verify with `sha256sum -c outputs/MANIFEST.sha256`.

## Second-environment check
Pending (open item 5).
