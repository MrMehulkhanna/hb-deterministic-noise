import sys, types
sys.modules['gradio'] = types.ModuleType('gradio')
import numpy as np, research_app as OLD, research_app_fixed as NEW
for n in (6, 10):
    bits, _ = NEW.and_k_noise(n, 2); x = 3
    p = NEW.bv_distribution(n, x, bits)
    for k in (51, 201):
        rng = np.random.default_rng(0); r = [NEW.sample_mode(p, k, rng) for _ in range(4000)]
        tie = np.mean([v is None for v in r]); hit = np.mean([v == x for v in r])
        rng = np.random.default_rng(0); o = [OLD.sample_mode(p, k, rng) for _ in range(4000)]
        print(f"n={n} k={k}: FIXED -> P(return secret)={hit:.3f}, P(tie reported)={tie:.3f} | OLD argmax -> P(return secret)={np.mean(np.array(o)==x):.3f}, P(return 0)={np.mean(np.array(o)==0):.3f}")
