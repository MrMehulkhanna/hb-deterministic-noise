# One-page summary

**Question.** Cid, Elkouss and Goulão (2026) broke HB, HB+ and HB# under Q2 access, because once-per-query Bernoulli noise is a global phase. They noted the attack fails if the noise depends on the input (deterministic LPN). Does input-dependent noise actually suppress Bernstein–Vazirani key recovery, and what decides it?

**Answer under the ideal Q2 phase-oracle model (exact).** The BV output distribution is the secret-shifted squared Walsh spectrum of the noise sign function: `P(j) = ĥ(x⊕j)²` and `P(x) = (1−2τ)²`. A repeated-query mode estimator succeeds when `Δ = P(x) − max_{u≠0} ĥ(u)² > 0`.

**Measured on controls (n = 8–14).**
- **Random fixed-weight noise:** Δ > 0 in 80/80 tables. Tens of queries suffice; k99 = 51 at n = 10, τ = 0.25.
- **Structured noise:** two-bit AND gives an exact tie that more queries cannot resolve. Linear noise gives a wrong output with certainty.
- **Keyed control** (not a PRF), n = 8, τ = 0.4: Δ ≤ 0 in 4/5 tables.

**Open.** Evaluate a published deterministic-LPN construction (Cid–Davidson–Phanse, ACNS 2026). The full text is not yet accessed. Complete the novelty search. The mechanism is an instance of known quantum Goldreich–Levin-type Fourier sampling; the question is its consequence for deterministic-noise LPN authentication.
