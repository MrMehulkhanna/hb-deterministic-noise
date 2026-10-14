# Method and derivations

> Status: derivations checked during the 2026-10-08 audit.

## Notation
- Secret `x ∈ {0,1}^n`; adversary-controlled input `a`; deterministic noise bit `e(a)`.
- Sign function `h(a) = (-1)^{e(a)}`; normalised Walsh coefficient `ĥ(u) = 2^{-n} Σ_a h(a)(-1)^{a·u}`.
- Ideal Q2 phase oracle: `|a⟩ ↦ (-1)^{a·x ⊕ e(a)} |a⟩`.
- `τ_realised = |{a : e(a)=1}| / 2^n` (always recorded; may differ from the target τ).

## 1. Output distribution
Start from `H^{⊗n}|0⟩ = 2^{-n/2} Σ_a |a⟩`. After the oracle the state is `2^{-n/2} Σ_a h(a)(-1)^{a·x}|a⟩`. Applying `H^{⊗n}` gives the amplitude of outcome `j`:

`α_j = 2^{-n} Σ_a h(a)(-1)^{a·x}(-1)^{a·j} = 2^{-n} Σ_a h(a)(-1)^{a·(x⊕j)} = ĥ(x⊕j)`,

so **`P(j) = ĥ(x⊕j)²`**. Parseval, `Σ_u ĥ(u)² = 1`, gives normalisation.
Special case: if `e` is constant (Bernoulli bit sampled once per query), `h = ±1` and `ĥ(u) = ±δ_{u,0}`, so `P(x) = 1`. This is the global-phase observation of Cid–Elkouss–Goulão (2026).

## 2. Key probability for an exact fixed-weight truth table
`ĥ(0) = 2^{-n} Σ_a (-1)^{e(a)} = (#zeros − #ones)/2^n = 1 − 2τ_realised`, hence **`P(x) = (1 − 2τ_realised)²`**.
This holds for *any* noise function with that realised weight; it is not a statement about the target τ.

## 3. Spectral-gap criterion
`Δ = P(x) − max_{u≠0} ĥ(u)²`.
- `Δ > 0`: the secret is the unique modal output of the ideal distribution.
- `Δ = 0`: structural tie with at least one competitor `x⊕u`.
- `Δ < 0`: some other output is more likely than the secret.

## 4. Sufficient query bound (audit A7: constants checked)
Draw `k` i.i.d. outcomes `Y_1..Y_k`. The estimator returns the unique empirical mode, or *tie* (counted as failure).

Fix a competitor `u ≠ 0` and set `Z_i = 1[Y_i = x] − 1[Y_i = x⊕u] ∈ [−1, 1]`, so `E Z_i = P(x) − ĥ(u)² ≥ Δ`. The estimator fails against `u` only if `Σ Z_i ≤ 0`. Hoeffding with range 2 gives

`Pr[Σ Z_i ≤ 0] ≤ exp(−2(kΔ)² / (4k)) = exp(−kΔ²/2)`.

A union bound over the `2^n − 1` competitors gives `Pr[failure] ≤ (2^n − 1) e^{−kΔ²/2}`. It is therefore sufficient that

**`k ≥ (2/Δ²) ln((2^n − 1)/δ)`.**

The implementation uses `(2/Δ²) ln(2(2^n − 1)/δ)`. The extra factor 2 inside the logarithm is not needed, because the event is one-sided. It makes the bound slightly larger, so it is **still sufficient**. It is retained for continuity with earlier outputs and documented here. The bound is not claimed to be tight: Fig. 4 shows the empirical k99 sitting far below it. Ties are included in the failure event because `Σ Z_i = 0` is a failure.

## 5. Estimator definition (audit A1)
`k99` = the smallest `k` in the checked grid `K_GRID = (1, 3, 5, 9, 15, 25, 51, 101, 201, 401, 801, 1001)` for which the Monte Carlo estimate of `P[unique empirical mode = secret] ≥ 0.99`. If no checked `k` reaches 0.99, the result is reported as *not reached within checked grid (max k = …)*.
This is **categorical mode estimation**, not "majority voting". Ties are reported (`tie_rate`), never silently resolved.

Observed consequence: for small odd `k` (e.g. `k = 3`), all-distinct samples form an empirical tie, so `P[unique mode = secret]` can be lower at `k = 3` than at `k = 1`. This is an estimator artefact and is documented in the report.

## 6. Exact vs Monte Carlo vs bound
Every reported number is labelled as one of:
- **exact** (spectrum, `P(x)`, `Δ`, Parseval);
- **Monte Carlo estimate** (success and tie rates, `k99`, with trials and seeds);
- **sufficient bound** (§4).
