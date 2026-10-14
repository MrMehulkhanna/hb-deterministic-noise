import sys, types, math
sys.modules['gradio'] = types.ModuleType('gradio')          # UI only; not needed for the maths
import numpy as np
import research_app as R
R.OUTPUT_DIR = __import__('pathlib').Path('.')
RF = "Random deterministic (fixed weight)"; KD = "Keyed deterministic (PRF-like control, NOT a PRF claim)"

print("=== 1. Spectrum example: n=10, x=00101101 (int 45), tau=0.25, seed=43")
for fam in (RF, KD):
    bits, rt, _ = R.make_noise(10, fam, 0.25, 43)
    m = R.spectral_metrics(10, 45, bits)
    print(f"  {fam[:28]:28s} realised={rt:.6f} P(x)={m['p_key']:.8f} comp={m['p_competitor']:.8f} gap={m['spectral_gap']:.8f} parseval={m['parseval']:.12f}")
print("  report claims: P(x)=0.25, competitor=0.01196289, Delta=0.23803711")

print("=== 2. Repeated-query attack via app's run_attack (trials=300)")
for fam in (RF, KD):
    txt, curve, _ = R.run_attack(10, "00101101", fam, 0.25, 43, 2, 1, 12345, 300, 1001)
    print("  ", fam[:28], "|", [l for l in txt.splitlines() if 'k99' in l or 'competitor' in l])

print("=== 3. AND-2 failure")
for n in (6, 10):
    bits, tau = R.and_k_noise(n, 2); x = 3 % 2**n
    p = R.bv_distribution(n, x, bits); m = R.spectral_metrics(n, x, bits)
    top = np.argsort(p)[::-1][:5]
    print(f"  n={n} tau={tau} P(x)={m['p_key']:.4f} comp={m['p_competitor']:.4f} gap={m['spectral_gap']:.4f} top outputs={[(int(j), round(float(p[j]),4)) for j in top]}")
    rng = np.random.default_rng(0)
    modes = [R.sample_mode(p, 51, rng) for _ in range(2000)]
    vals, cnt = np.unique(modes, return_counts=True)
    print(f"    argmax-mode (k=51, 2000 trials) returns: {dict(zip(vals.tolist(), (cnt/2000).round(3).tolist()))}  <- tie-break check, secret x={x}")

print("=== 4. Depolarising extension (5%, n=10 example)")
bits, rt, _ = R.make_noise(10, RF, 0.25, 43)
p = R.bv_distribution(10, 45, bits); eps = 0.05
pd_ = (1-eps)*p + eps/p.size
print(f"  P(x): {p[45]:.8f} -> {pd_[45]:.8f}; gap after = {pd_[45]-np.max(np.delete(pd_,45)):.8f}  (report: 0.25 -> 0.23754883)")
print("  bound check: sufficient k for Delta=0.23803711, n=10, delta=0.01 =", math.ceil(R.sufficient_query_bound(0.23803711, 10, 0.01)), "(report: 432)")

print("=== 5. Finite control suite (app's own function)")
summary, df, _, _ = R.run_experiment_suite("8,10,12,14", "0.05,0.125,0.25,0.4", 5, RF, 2, 1, 12345)
print(summary)
df.to_csv('outputs/experiment_suite_reproduced.csv', index=False)
g = df.groupby(['n','target_tau']).agg(realised=('realised_tau','mean'), pkey=('p_key','mean'), comp=('p_competitor','mean'), gap=('spectral_gap','mean'), k99=('k99_empirical','median')).reset_index()
print(g.to_string(index=False))
print("  report claims: 80 rows, mean P(key)=0.415548, min gap=0.006104, 100.0% positive")
