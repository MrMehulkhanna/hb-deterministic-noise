"""One-command reproduction of every control result in the report.

    python tests/test_core.py && python reproduce.py

Writes raw CSVs, figures, environment record and a SHA-256 manifest to outputs/.
Group E (published deterministic-LPN construction) is run separately with
analyse_construction.py once a verified truth table exists.
"""
from __future__ import annotations

import hashlib
import json
import math
import platform
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

import research_app as R  # noqa: E402

OUT = Path(__file__).parent / "outputs"
OUT.mkdir(exist_ok=True)
RF, KD = "Random deterministic (fixed weight)", "Keyed deterministic (PRF-like control, NOT a PRF claim)"
NS, TAUS, REPS = (8, 10, 12, 14), (0.05, 0.125, 0.25, 0.4), 5
MAX_K = 501
GAP_TOL = 1e-12  # |Δ| below this is classified as an exact (structural) tie


def gap_class(d: float) -> str:
    return "tie" if abs(d) < GAP_TOL else ("positive" if d > 0 else "negative")


def suite(family: str, tag: str) -> pd.DataFrame:
    rows = []
    for n in NS:
        x = (7 * n + 3) % (2 ** n)                      # documented secret rule (audit A6)
        trials = max(150, min(500, 20 * n))            # documented trial rule (audit A5)
        for tau in TAUS:
            for rep in range(REPS):
                seed = 1000 + rep + 31 * n              # documented seed rule (audit A6)
                # audit A8: the keyed control ignores `seed`; vary its key per repetition so
                # repetitions are distinct truth tables (key rule documented in the CSV).
                noise_key = 12345 + rep
                bits, rt, _ = R.make_noise(n, family, tau, seed, 2, 1, noise_key)
                p = R.bv_distribution(n, x, bits)
                m = R.spectral_metrics(n, x, bits)
                k99, curve = R.k99_empirical(p, x, trials, seed + 77, MAX_K)
                rows.append({
                    "group": tag, "family": family, "n": n, "secret_bits": "b" + format(x, f"0{n}b"),
                    "target_tau": tau, "realised_tau": rt, "seed": seed,
                    "noise_key": noise_key if family == KD else "",
                    "truth_table_sha256": hashlib.sha256(bits.tobytes()).hexdigest(), "mc_trials": trials,
                    "query_grid": "|".join(str(k) for k in R.K_GRID if k <= MAX_K),
                    "p_key": m["p_key"], "p_competitor": m["p_competitor"], "spectral_gap": m["spectral_gap"],
                    "gap_class": gap_class(m["spectral_gap"]),
                    "k99_empirical": k99 if k99 is not None else np.nan, "k99_status": R.k99_status(k99, MAX_K),
                    "tie_rate_at_k99_or_max": float(curve.loc[curve["queries"] == (k99 or curve["queries"].max()), "tie_rate"].iloc[0]),
                    "k99_sufficient_bound": R.sufficient_query_bound(m["spectral_gap"], n, 0.01),
                })
    df = pd.DataFrame(rows)
    df.to_csv(OUT / f"control_suite_{tag}.csv", index=False)
    return df


def summarise(df: pd.DataFrame) -> dict:
    return {"rows": len(df), "mean_p_key": round(float(df.p_key.mean()), 6),
            "min_gap": round(float(df.spectral_gap.min()), 6),
            "positive_gap_pct": round(100 * float((df.spectral_gap > 0).mean()), 1),
            "max_abs_identity_error": float(np.max(np.abs(df.p_key - (1 - 2 * df.realised_tau) ** 2))),
            "k99_not_reached_rows": int(df.k99_empirical.isna().sum()),
            "distinct_truth_tables": int(df.truth_table_sha256.nunique()),
            "gap_class_counts": df.gap_class.value_counts().to_dict(),
            "non_positive_cells": df[df.gap_class != "positive"].groupby(["n", "target_tau"]).size().rename("rows").reset_index().to_dict("records")}


def main() -> None:
    results: dict = {}

    # Group A: Bernoulli / global-phase control (exact)
    a = [{"n": n, "error_bit": b, "p_key": float(R.bv_distribution(n, 5, R.bernoulli_global_noise(n, b)[0])[5])}
         for n in NS for b in (0, 1)]
    pd.DataFrame(a).to_csv(OUT / "group_A_bernoulli.csv", index=False)
    results["A_bernoulli_min_p_key"] = min(r["p_key"] for r in a)

    # Groups B and C: deterministic fixed-weight controls
    b = suite(RF, "B_random_fixed_weight")
    c = suite(KD, "C_keyed_research_control_NOT_PRF")
    results["B"] = summarise(b)
    results["C"] = summarise(c)

    # Canonical n=10 example (both families named; audit A2)
    canon = []
    for fam, tag in ((KD, "C_keyed_research_control_NOT_PRF"), (RF, "B_random_fixed_weight")):
        bits, rt, _ = R.make_noise(10, fam, 0.25, 43)
        x = int("0000101101", 2)
        s, top, curve = R.analyse_truth_table(bits, x, tag, trials=300, seed=43 + 101, max_k=1001)
        curve.insert(0, "family", tag)
        canon.append(curve)
        results[f"canonical_n10_{tag}"] = {k: s[k] for k in ("secret_bits", "realised_tau", "p_key", "p_competitor",
                                                            "spectral_gap", "k99", "sufficient_bound", "trials", "seed")}
    pd.concat(canon).to_csv(OUT / "canonical_n10_curves.csv", index=False)

    # Group D: AND-k and linear toy controls, tie-aware
    d_rows = []
    for k in (1, 2, 3, 4):
        bits, tau = R.and_k_noise(10, k)
        m = R.spectral_metrics(10, 3, bits)
        curve = R.repeated_success_curve(R.bv_distribution(10, 3, bits), 3, (1, 25, 101, 401), 2000, 9090 + k)
        for _, row in curve.iterrows():
            d_rows.append({"family": f"AND-{k}", "n": 10, "secret_bits": "b" + format(3, "010b"), "realised_tau": tau,
                           "p_key": m["p_key"], "p_competitor": m["p_competitor"], "spectral_gap": m["spectral_gap"],
                           "queries": int(row.queries), "p_unique_mode_secret": row.success_probability,
                           "p_tie": row.tie_rate, "trials": int(row.trials)})
    bits, tau = R.linear_noise(10, 0b0000000110)
    m = R.spectral_metrics(10, 3, bits)
    d_rows.append({"family": "linear u=0000000110", "n": 10, "secret_bits": "b" + format(3, "010b"), "realised_tau": tau,
                   "p_key": m["p_key"], "p_competitor": m["p_competitor"], "spectral_gap": m["spectral_gap"],
                   "queries": 0, "p_unique_mode_secret": float("nan"), "p_tie": float("nan"), "trials": 0})
    dd = pd.DataFrame(d_rows)
    dd.to_csv(OUT / "group_D_toy_controls.csv", index=False)
    results["D_AND2_success_by_k"] = dd[dd.family == "AND-2"][["queries", "p_unique_mode_secret", "p_tie"]].round(4).to_dict("records")

    # Group F: output-depolarising robustness (keyed control canonical example)
    bits, rt, _ = R.make_noise(10, KD, 0.25, 43)
    ideal = R.bv_distribution(10, 45, bits)
    f_rows = []
    for eps in (0.0, 0.05, 0.1, 0.25, 0.5):
        q = (1 - eps) * ideal + eps / ideal.size
        f_rows.append({"family": "C_keyed_research_control_NOT_PRF", "n": 10, "epsilon": eps, "p_key": float(q[45]),
                       "p_competitor": float(np.max(np.delete(q, 45))), "gap": float(q[45] - np.max(np.delete(q, 45)))})
    pd.DataFrame(f_rows).to_csv(OUT / "group_F_depolarising.csv", index=False)
    results["F_depolarising"] = f_rows

    # Figures
    fig, ax = plt.subplots(figsize=(7, 4.2))
    for df, lab, mk in ((b, "B random fixed-weight", dict(marker="o", ms=11, mfc="none")), (c, "C keyed control (not a PRF)", dict(marker="x", ms=8))):
        g = df.groupby("target_tau").agg(rt=("realised_tau", "mean"), pk=("p_key", "mean"))
        ax.plot(g.rt, g.pk, ls="none", label=lab + " (markers coincide: same realised τ)", **mk)
    t = np.linspace(0, 0.5, 200)
    ax.plot(t, (1 - 2 * t) ** 2, "k--", lw=1, label="(1-2τ)² (exact identity)")
    ax.set(xlabel="realised τ", ylabel="P(secret) per query", title="Fig 1. Key probability vs realised noise rate")
    ax.legend(fontsize=8); ax.grid(alpha=.25); fig.tight_layout(); fig.savefig(OUT / "fig1_pkey_vs_tau.png", dpi=180)

    fig, ax = plt.subplots(figsize=(7, 4.2))
    for curve in canon:
        fam = curve.family.iloc[0]; key = fam.startswith("C")
        ax.plot(curve.queries, curve.success_probability, "x-" if key else "o--", mfc="none", ms=8, label=f"{fam[:2]}: P[unique mode = secret]")
        ax.plot(curve.queries, curve.tie_rate, ":" if key else "-.", label=f"{fam[:2]}: P[tie]")
    ax.axhline(.99, ls="--", c="gray", lw=1); ax.set_xscale("log")
    ax.set(xlabel="queries k (checked grid)", ylabel="probability (300 trials)", title="Fig 2. Canonical n=10, τ=0.25 recovery (tie-aware)")
    ax.legend(fontsize=7); ax.grid(alpha=.25); fig.tight_layout(); fig.savefig(OUT / "fig2_canonical_recovery.png", dpi=180)

    fig, ax = plt.subplots(figsize=(7, 4.2))
    for k in (2, 3, 4):
        s = dd[dd.family == f"AND-{k}"]
        ax.plot(s.queries, s.p_unique_mode_secret, "o-", label=f"AND-{k}: Δ={s.spectral_gap.iloc[0]:.3f}")
    s = dd[dd.family == "AND-2"]; ax.plot(s.queries, s.p_tie, "x:", label="AND-2: P[tie]")
    ax.set_xscale("log"); ax.set(xlabel="queries k", ylabel="probability (2000 trials)", title="Fig 3. Zero gap (AND-2) is not resolved by more queries")
    ax.legend(fontsize=8); ax.grid(alpha=.25); fig.tight_layout(); fig.savefig(OUT / "fig3_and_k_ambiguity.png", dpi=180)

    fig, ax = plt.subplots(figsize=(7, 4.2))
    for df, lab in ((b, "B random fixed-weight"), (c, "C keyed control")):
        ok = df.dropna(subset=["k99_empirical"])
        ax.scatter(ok.k99_sufficient_bound, ok.k99_empirical, s=14, label=lab)
    ax.set_xscale("log"); ax.set_yscale("log"); lim = [1, 1e7]; ax.plot(lim, lim, "k--", lw=1, label="y = x")
    ax.set(xlabel="sufficient Hoeffding/union bound", ylabel="empirical k99 (grid value)", title="Fig 4. Bound is conservative (sufficient, not tight)")
    ax.legend(fontsize=8); ax.grid(alpha=.25, which="both"); fig.tight_layout(); fig.savefig(OUT / "fig4_bound_vs_empirical.png", dpi=180)
    plt.close("all")

    # Environment + manifest
    env = {"python": sys.version.split()[0], "platform": platform.platform(), "machine": platform.machine(),
           "numpy": np.__version__, "pandas": pd.__version__, "matplotlib": matplotlib.__version__}
    (OUT / "environment.json").write_text(json.dumps(env, indent=2))
    (OUT / "results_summary.json").write_text(json.dumps(results, indent=2, default=float))
    root = Path(__file__).parent
    files = sorted([*root.glob("*.py"), *root.glob("tests/*.py"), *root.glob("constructions/*.py"),
                    *OUT.glob("*.csv"), *OUT.glob("*.png"), *OUT.glob("*.json")])
    lines = [f"{hashlib.sha256(p.read_bytes()).hexdigest()}  {p.relative_to(root)}" for p in files if p.name != "MANIFEST.sha256"]
    (OUT / "MANIFEST.sha256").write_text("\n".join(lines) + "\n")
    print(json.dumps(results, indent=1, default=float)[:3000])


if __name__ == "__main__":
    main()
