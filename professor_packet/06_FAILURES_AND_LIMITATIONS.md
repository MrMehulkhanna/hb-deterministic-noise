# Failures and limitations

## Failures (kept deliberately)
- **AND-2:** exact four-way spectral tie. The mode estimator cannot resolve it with more queries.
- **AND-1 and linear noise:** Δ = −1. The attack returns a wrong output with certainty.
- **Keyed control, n = 8, τ = 0.4:** Δ ≤ 0 in 4 of 5 tables. Not evidence of a systematic family difference (5 samples).
- **n = 8–10, τ = 0.4:** k99 often not reached within 401 queries.
- **Estimator artefact:** success at k = 3 (0.12) is below k = 1 (0.27), because three samples usually form a tie.
- **Audit corrections:** the original estimator was tie-biased (A1), so all earlier k99 values are superseded. The keyed control's repetitions were not distinct until A8.

## Limitations
- Ideal Q2 oracle; no device, compiler or protocol modelling.
- Exact enumeration for n ≤ 14 only, so no asymptotic claim.
- Controls only; no published construction tested.
- The keyed control is not a PRF.
- 5 tables per point.
- Fixed secret rule.
- HB+ second key and HB# not simulated.
- Novelty search incomplete.
