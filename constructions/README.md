# Group E: published deterministic-LPN construction (NOT YET IMPLEMENTED)

**Status: blocked.** The source chapter (Cid, Davidson, Phanse, *Practice-Oriented Instances of Deterministic LPN*, ACNS 2026, LNCS 16571, pp. 382–412, doi:10.1007/978-3-032-32560-0_14) was not accessible on 2026-10-08: it is behind the Springer paywall and no open copy was found. No construction may be implemented from memory or guesswork.

## Required before any code is written here
1. Full text obtained legitimately.
2. One construction chosen. Record in `constructions/SPEC_<name>.md`:
   - exact construction name and source section, page and equation;
   - parameterisation (key size, input length n, diffusion function, folding function, target τ);
   - whether the noise rate is **exact-weight** or only **expected-weight**;
   - how the secret/key enters; domain restrictions; implementation assumptions.
3. A dated prediction in `notes/predictions/concrete_construction_<YYYY-MM-DD>.md`, from the template, committed **before** the implementation is run.

## Implementation rules
- Put the implementation in `constructions/<name>.py`, separate from the research controls in `research_app.py`.
- Add unit tests in `tests/test_construction_<name>.py` against any test vectors or hand-computable cases in the specification.
- Write the full truth table for small n to `constructions/output/<name>_n<n>_<keyid>.txt` (0/1 digits, input order a = 0 … 2ⁿ−1).
- Record the SHA-256 of the implementation source after the researcher has verified it against the specification.
- Analyse with `python analyse_construction.py …` or the app's **Concrete construction** tab.
- Never relabel the keyed research control as this construction.
