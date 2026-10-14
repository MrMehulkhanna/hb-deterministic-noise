# Code and data

- `research_app.py`: Walsh–Hadamard transform, BV distribution, spectral metrics, noise families (A–D), tie-aware mode estimator, k99 grid, sufficient bound, truth-table analysis, optional Gradio UI.
- `tests/test_core.py`: 15 tests, including A1 regression tests that fail on the pre-audit estimator (`audits/tests_against_pre_audit_app.txt`).
- `reproduce.py`: writes all CSVs and figures in `outputs/`, plus `environment.json` and `MANIFEST.sha256`.
- `analyse_construction.py`: Group E analysis; refuses to run without a prediction file.
- Raw data columns are self-describing: family, n, secret_bits (`b`-prefixed), target and realised τ, seed or noise_key, truth_table_sha256, mc_trials, query_grid, exact metrics, gap_class, k99_status.
