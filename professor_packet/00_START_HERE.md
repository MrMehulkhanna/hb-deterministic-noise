# Start here

**Project:** Spectral leakage and repeated Bernstein–Vazirani key recovery under deterministic, input-dependent noise.
**Status:** control framework verified. **The experiment on a published deterministic-LPN construction has not been run yet.** No security or novelty claim is made.

**Read in this order:**
1. `01_ONE_PAGE_SUMMARY.md`: question, result, what is open (2 min).
2. `02_TECHNICAL_REPORT.pdf`: full report, 7 pages.
3. `05_MAIN_RESULTS.md` and `06_FAILURES_AND_LIMITATIONS.md`: numbers and caveats.
4. `08_CODE_AND_DATA.md`: where the raw evidence is.

**Raw evidence:** `../outputs/*.csv`, with every row naming its family, seed, trials and query grid. Checksums: `../outputs/MANIFEST.sha256`. Audit trail: `../audits/AUDIT_LOG.md`.
**Reproduce:** `python tests/test_core.py && python reproduce.py` (about 35 s).
