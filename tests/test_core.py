"""Regression and correctness tests. Run: python tests/test_core.py   (exit code 0 = all pass)

Set HB_APP_MODULE=<module> to run the same tests against another implementation
(used in audits/ to show that the A1 test fails on the pre-audit argmax estimator).
"""
import importlib
import math
import os
import sys
import tempfile

import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "audits"))
R = importlib.import_module(os.environ.get("HB_APP_MODULE", "research_app"))

RESULTS = []


def check(name):
    def wrap(fn):
        try:
            fn()
            RESULTS.append((name, "PASS", ""))
        except AssertionError as exc:
            RESULTS.append((name, "FAIL", str(exc)))
        except Exception as exc:  # noqa: BLE001
            RESULTS.append((name, "ERROR", f"{type(exc).__name__}: {exc}"))
        return fn
    return wrap


@check("WHT equals slow Kronecker H^n (n=1,3,6)")
def _():
    rng = np.random.default_rng(0)
    for n in (1, 3, 6):
        v = rng.normal(size=2 ** n)
        h1 = np.array([[1, 1], [1, -1]]) / math.sqrt(2)
        H = h1
        for _ in range(n - 1):
            H = np.kron(H, h1)
        assert np.allclose(R.walsh_hadamard_unitary(v), H @ v)


@check("WHT is an involution")
def _():
    v = np.random.default_rng(1).normal(size=256)
    assert np.allclose(R.walsh_hadamard_unitary(R.walsh_hadamard_unitary(v)), v)


@check("Bernoulli (global phase) noise gives P(x)=1 exactly")
def _():
    for n in (4, 8, 10):
        for bit in (0, 1):
            bits, _ = R.bernoulli_global_noise(n, bit)
            p = R.bv_distribution(n, 5, bits)
            assert abs(p[5] - 1) < 1e-12


@check("probabilities normalised; Parseval = 1")
def _():
    bits, _ = R.exact_fixed_weight_noise(10, 0.3, 3)
    assert abs(R.bv_distribution(10, 77, bits).sum() - 1) < 1e-12
    assert abs(R.spectral_metrics(10, 77, bits)["parseval"] - 1) < 1e-12


@check("fixed-weight identity P(x) = (1-2 tau_realised)^2")
def _():
    for n, tau, seed in [(8, 0.05, 1), (10, 0.25, 2), (12, 0.4, 3)]:
        bits, rt = R.exact_fixed_weight_noise(n, tau, seed)
        assert abs(R.bv_distribution(n, 9, bits)[9] - (1 - 2 * rt) ** 2) < 1e-12


@check("BV distribution equals secret-shifted squared Walsh spectrum")
def _():
    n, x = 8, 0b10110010
    bits, _ = R.exact_fixed_weight_noise(n, 0.2, 9)
    p = R.bv_distribution(n, x, bits)
    w2 = R.boolean_walsh_coeffs(bits) ** 2
    assert np.allclose(p, w2[np.arange(2 ** n) ^ x])


@check("AND-2 is an exact spectral tie (Delta = 0)")
def _():
    bits, tau = R.and_k_noise(10, 2)
    m = R.spectral_metrics(10, 3, bits)
    assert tau == 0.25 and abs(m["p_key"] - 0.25) < 1e-12 and abs(m["spectral_gap"]) < 1e-12


class _FixedRNG:
    """Returns predetermined outcomes so the estimator sees an exact empirical tie."""

    def __init__(self, outcomes):
        self.outcomes = np.array(outcomes)

    def choice(self, *args, **kwargs):  # noqa: ARG002
        return self.outcomes


@check("A1: an exact empirical tie is NOT resolved toward the smallest output")
def _():
    p = np.array([0.5, 0.5, 0.0, 0.0])
    mode = R.sample_mode(p, 2, _FixedRNG([1, 0]))
    assert mode is None, f"tie silently resolved to {mode}; must be reported as a tie (None)"


@check("A1: AND-2 tie produces no systematic preference for output 0")
def _():
    bits, _ = R.and_k_noise(6, 2)
    p = R.bv_distribution(6, 3, bits)  # outputs 0,1,2,3 tied at 0.25
    rng = np.random.default_rng(0)
    modes = [R.sample_mode(p, 51, rng) for _ in range(3000)]
    f0 = np.mean([m == 0 for m in modes])
    f3 = np.mean([m == 3 for m in modes])
    assert abs(f0 - f3) < 0.04, f"output 0 chosen {f0:.3f} vs secret {f3:.3f}: tie-break bias"


@check("A2: secrets are reported with exactly n bits")
def _():
    txt, _, _ = R.run_attack(10, "0000101101", "Keyed deterministic (PRF-like control, NOT a PRF claim)",
                             0.25, 43, 2, 1, 12345, 30, 15)
    assert "x=0000101101" in txt and "family=" in txt, txt


@check("A4: competitor field is not called most_likely_output")
def _():
    m = R.spectral_metrics(6, 3, R.and_k_noise(6, 2)[0])
    assert "most_likely_output" not in m and "best_competitor_output" in m


@check("A5: not-reached k99 is reported explicitly")
def _():
    assert R.k99_status(None, 501).startswith("not reached within checked grid (max k=401)")
    assert R.k99_status(51, 1001) == "51"


@check("A7: sufficient bound reproduces 432 for Delta=0.23803711, n=10, delta=0.01")
def _():
    assert math.ceil(R.sufficient_query_bound(0.23803711, 10, 0.01)) == 432
    assert math.isinf(R.sufficient_query_bound(0.0, 10, 0.01))


@check("truth-table loader rejects bad input and round-trips good input")
def _():
    with tempfile.TemporaryDirectory() as d:
        good = os.path.join(d, "t.txt")
        with open(good, "w") as f:
            f.write("0110 1001\n0000 1111\n")
        bits, n = R.load_truth_table(good)
        assert n == 4 and bits.tolist() == [0, 1, 1, 0, 1, 0, 0, 1, 0, 0, 0, 0, 1, 1, 1, 1]
        for bad in ("0102", "011"):
            path = os.path.join(d, "b.txt")
            with open(path, "w") as f:
                f.write(bad)
            try:
                R.load_truth_table(path)
                raise AssertionError(f"accepted bad table {bad!r}")
            except ValueError:
                pass


@check("analyse_truth_table on AND-2 reports zero gap and a hash")
def _():
    s, top, curve = R.analyse_truth_table(R.and_k_noise(6, 2)[0], 3, "AND-2 control", trials=50, seed=1, max_k=25)
    assert abs(s["spectral_gap"]) < 1e-12 and len(s["truth_table_sha256"]) == 64
    assert "tie_rate" in curve.columns


if __name__ == "__main__":
    for name, status, msg in RESULTS:
        print(f"[{status:5}] {name}" + (f"\n         {msg}" if msg else ""))
    passed = sum(r[1] == "PASS" for r in RESULTS)
    print(f"\n{passed}/{len(RESULTS)} passed  (module: {R.__name__})")
    sys.exit(0 if passed == len(RESULTS) else 1)
