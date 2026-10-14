# Changelog

No version-control history was received with the handoff. Versions below are reconstructed from the files actually present; no dates or commits are invented.

## 0.2.0-controls (2026-10-08): audit and completion pass (this directory)
- A1 tie-aware mode estimator; regression tests that fail on the pre-audit estimator.
- A2 n-bit secret formatting and named noise families everywhere (CSV bit strings `b`-prefixed).
- A3 `n/P(key)` relabelled as a Bernoulli-HB reference, not a baseline.
- A4 `best_competitor_output` naming. A5 explicit grid, trials and not-reached reporting. A6 documented seed and secret rules.
- A7 Hoeffding/union bound constant checked (sufficient; documented).
- A8 keyed-control repetitions made distinct (key 12345+rep); truth-table SHA-256 per row.
- New: gap classification (positive/tie/negative), groups A–F reproduction script, SHA-256 manifest, construction-analysis CLI and app tab.
- Report rebuilt; old k99 values (including 25) superseded.

## 0.1 (as received): `research_app.py` sha256 9a354f1b…25af, reports v2/v3
Superseded by this version.
