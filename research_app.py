from __future__ import annotations

import hashlib
import io
import json
import math
import os
import tempfile
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Iterable

try:  # UI dependency is optional: the research core runs without it
    import gradio as gr
except ImportError:  # pragma: no cover
    gr = None
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from PIL import Image
try:  # PDF export dependency is optional
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import cm
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image as RLImage
except ImportError:  # pragma: no cover
    colors = None

APP_DIR = Path(__file__).resolve().parent
OUTPUT_DIR = APP_DIR / "outputs"
OUTPUT_DIR.mkdir(exist_ok=True)

PROJECT_TITLE = "Spectral Leakage and Repeated Bernstein–Vazirani Key Recovery in Deterministic-LPN-Style Noise"
SOURCE_PAPER = (
    "C. Cid, D. Elkouss, M. Goulão, “Superposition Attacks Against LPN-Based Authentication Protocols,” "
    "IACR Communications in Cryptology 3(1), 2026, doi:10.62056/abhey7n4e"
)

# -----------------------------
# Core math
# -----------------------------

def bit_strings(n: int) -> np.ndarray:
    """Return all n-bit integers in lexicographic integer order."""
    return np.arange(2 ** n, dtype=np.uint32)


def dot_mod2(a: np.ndarray, s: int) -> np.ndarray:
    """Vectorised mod-2 inner product for integer-encoded bit strings."""
    # Python int.bit_count is not vectorised, so use a parity lookup in uint8 blocks.
    x = np.asarray(a, dtype=np.uint32) & np.uint32(s)
    # XOR-fold parity using bit operations.
    x ^= x >> np.uint32(16)
    x ^= x >> np.uint32(8)
    x ^= x >> np.uint32(4)
    x ^= x >> np.uint32(2)
    x ^= x >> np.uint32(1)
    return (x & np.uint32(1)).astype(np.uint8)


def walsh_hadamard_unitary(v: np.ndarray) -> np.ndarray:
    """Unitary Walsh-Hadamard transform H^{⊗n}."""
    a = np.asarray(v, dtype=np.float64).copy()
    n = a.size
    if n == 0 or (n & (n - 1)) != 0:
        raise ValueError("Transform length must be a positive power of two.")
    h = 1
    inv_sqrt2 = 1.0 / math.sqrt(2.0)
    while h < n:
        step = 2 * h
        for start in range(0, n, step):
            x = a[start:start + h].copy()
            y = a[start + h:start + step].copy()
            a[start:start + h] = (x + y) * inv_sqrt2
            a[start + h:start + step] = (x - y) * inv_sqrt2
        h = step
    return a


def boolean_walsh_coeffs(bits: np.ndarray) -> np.ndarray:
    """Normalised Walsh spectrum of h(a)=(-1)^{bits(a)}."""
    h = 1.0 - 2.0 * np.asarray(bits, dtype=np.float64)
    return walsh_hadamard_unitary(h) / math.sqrt(h.size)


def phases_for_oracle(n: int, secret_x: int, noise_bits: np.ndarray) -> np.ndarray:
    a = bit_strings(n)
    linear = dot_mod2(a, secret_x)
    exponent = linear ^ np.asarray(noise_bits, dtype=np.uint8)
    return 1.0 - 2.0 * exponent.astype(np.float64)


def bv_distribution(n: int, secret_x: int, noise_bits: np.ndarray) -> np.ndarray:
    """Exact Q2 BV output distribution under a phase oracle."""
    phases = phases_for_oracle(n, secret_x, noise_bits)
    # Initial uniform state contributes 1/sqrt(N); second H^{⊗n} is unitary.
    amplitudes = walsh_hadamard_unitary(phases) / math.sqrt(2 ** n)
    probs = amplitudes ** 2
    # Numerical hygiene.
    probs = np.clip(probs, 0.0, None)
    probs /= probs.sum()
    return probs


def spectral_metrics(n: int, secret_x: int, noise_bits: np.ndarray) -> dict:
    h_hat = boolean_walsh_coeffs(noise_bits)
    key_u = 0
    key_prob = float(h_hat[key_u] ** 2)
    spectrum_sq = h_hat ** 2
    competitors = spectrum_sq.copy()
    competitors[key_u] = -1.0
    best_u = int(np.argmax(competitors)) if n > 0 else 0
    best_comp = float(competitors[best_u])
    gap = key_prob - best_comp
    return {
        "target_tau": None,
        "realised_tau": float(np.mean(noise_bits)),
        "p_key": key_prob,
        "p_competitor": best_comp,
        "spectral_gap": gap,
        "best_offset": best_u,
        "best_competitor_output": int(secret_x ^ best_u),
        "parseval": float(np.sum(h_hat ** 2)),
    }

# -----------------------------
# Deterministic noise families
# -----------------------------

def exact_fixed_weight_noise(n: int, tau: float, seed: int) -> tuple[np.ndarray, float]:
    """Deterministic-after-seeding noise with exactly rounded target weight."""
    N = 2 ** n
    w = int(round(float(tau) * N))
    w = min(max(w, 0), N)
    rng = np.random.default_rng(seed)
    idx = rng.choice(N, size=w, replace=False)
    bits = np.zeros(N, dtype=np.uint8)
    bits[idx] = 1
    return bits, w / N


def bernoulli_global_noise(n: int, error_bit: int) -> tuple[np.ndarray, float]:
    return np.full(2 ** n, int(error_bit) & 1, dtype=np.uint8), float(int(error_bit) & 1)


def and_k_noise(n: int, k: int, input_mask: int = 0) -> tuple[np.ndarray, float]:
    """Toy low-depth Boolean function e(a)=AND of k selected bits."""
    k = max(1, min(k, n))
    # Use the lowest k input positions, optionally shifted by a circular mask for experimentation.
    mask = (1 << k) - 1
    if input_mask:
        mask ^= (input_mask & ((1 << n) - 1))
    a = bit_strings(n)
    bits = ((a & np.uint32(mask)) == np.uint32(mask)).astype(np.uint8)
    return bits, float(bits.mean())


def linear_noise(n: int, u: int) -> tuple[np.ndarray, float]:
    a = bit_strings(n)
    u &= (1 << n) - 1
    bits = dot_mod2(a, u)
    return bits, float(bits.mean())


def keyed_deterministic_noise(n: int, tau: float, noise_key: int) -> tuple[np.ndarray, float]:
    """Research control: a secret-keyed deterministic fixed-weight function.

    This is intentionally NOT claimed to be a cryptographic PRF. It is a reproducible
    pseudorandom-looking keyed control for studying the spectral mechanism.
    """
    N = 2 ** n
    w = int(round(float(tau) * N))
    w = min(max(w, 0), N)
    mask64 = np.uint64(0xFFFFFFFFFFFFFFFF)
    a = np.arange(N, dtype=np.uint64)
    z = (a + np.uint64(int(noise_key) & 0xFFFFFFFFFFFFFFFF) + np.uint64(0x9E3779B97F4A7C15)) & mask64
    z = (z ^ (z >> np.uint64(30))) * np.uint64(0xBF58476D1CE4E5B) & mask64
    z = (z ^ (z >> np.uint64(27))) * np.uint64(0x94D049BB133111EB) & mask64
    scores = (z ^ (z >> np.uint64(31))) & mask64
    chosen = np.argpartition(scores, w - 1)[:w] if w > 0 else np.empty(0, dtype=np.int64)
    bits = np.zeros(N, dtype=np.uint8)
    bits[chosen] = 1
    return bits, w / N

def make_noise(
    n: int,
    family: str,
    tau: float,
    seed: int,
    and_k: int = 2,
    linear_u: int = 1,
    noise_key: int = 12345,
) -> tuple[np.ndarray, float, str]:
    if family == "Bernoulli (global phase control)":
        # Fixed per-query error bit, as required by the global-phase observation.
        bit = seed & 1
        bits, realised = bernoulli_global_noise(n, bit)
        return bits, realised, "one error bit copied to every input"
    if family == "Random deterministic (fixed weight)":
        bits, realised = exact_fixed_weight_noise(n, tau, seed)
        return bits, realised, "random placement, exact fixed realised weight"
    if family == "AND-k (toy low-depth)":
        bits, realised = and_k_noise(n, and_k)
        return bits, realised, f"e(a)=AND of {and_k} low-order input bits"
    if family == "Linear (toy failure/control)":
        bits, realised = linear_noise(n, linear_u)
        return bits, realised, f"e(a)=a·u mod 2 with u={linear_u}"
    if family == "Keyed deterministic (PRF-like control, NOT a PRF claim)":
        bits, realised = keyed_deterministic_noise(n, tau, noise_key)
        return bits, realised, "secret-keyed deterministic fixed-weight control"
    raise ValueError(f"Unknown noise family: {family}")

# -----------------------------
# Sampling and bounds
# -----------------------------

def sample_mode(probabilities: np.ndarray, k: int, rng: np.random.Generator) -> int | None:
    """Categorical mode estimator. Returns None when the empirical mode is tied.

    Ties are reported as failures instead of being broken toward the smallest index:
    np.argmax would silently favour low-numbered outputs (audit finding A1).
    """
    outcomes = rng.choice(probabilities.size, size=int(k), replace=True, p=probabilities)
    counts = np.bincount(outcomes, minlength=probabilities.size)
    top = np.flatnonzero(counts == counts.max())
    return int(top[0]) if top.size == 1 else None


K_GRID = (1, 3, 5, 9, 15, 25, 51, 101, 201, 401, 801, 1001)  # checked query counts (audit A5)


def repeated_success_curve(probabilities: np.ndarray, key: int, ks: Iterable[int], trials: int, seed: int) -> pd.DataFrame:
    """Monte Carlo estimate of P[unique empirical mode = secret] and P[empirical tie] per query count."""
    rng = np.random.default_rng(seed)
    rows = []
    for k in ks:
        successes = ties = 0
        for _ in range(int(trials)):
            mode = sample_mode(probabilities, int(k), rng)
            if mode is None:
                ties += 1
            elif mode == key:
                successes += 1
        t = max(1, int(trials))
        rows.append({"queries": int(k), "success_probability": successes / t, "tie_rate": ties / t, "trials": int(trials)})
    return pd.DataFrame(rows)


def k99_empirical(probabilities: np.ndarray, key: int, trials: int, seed: int, max_k: int = 1001) -> tuple[int | None, pd.DataFrame]:
    ks = [k for k in K_GRID if k <= max_k]
    curve = repeated_success_curve(probabilities, key, ks, trials, seed)
    hit = curve[curve["success_probability"] >= 0.99]
    return (int(hit.iloc[0]["queries"]) if not hit.empty else None), curve


def k99_status(k99: int | None, max_k: int) -> str:
    """Human-readable k99 including the explicit not-reached case (audit A5)."""
    checked = [k for k in K_GRID if k <= max_k]
    return str(k99) if k99 is not None else f"not reached within checked grid (max k={checked[-1] if checked else 0})"


def sufficient_query_bound(delta: float, n: int, failure_prob: float = 0.01) -> float:
    if delta <= 0:
        return math.inf
    N = 2 ** n
    return (2.0 / (delta ** 2)) * math.log((2.0 * max(1, N - 1)) / failure_prob)


def bernoulli_hb_reference(n: int, p_key: float) -> float:
    """n / P(key). NOTE (audit A3): this equals the classical active-attack cost for
    *Bernoulli* HB, n/(1-2tau)^2. It is NOT a valid classical cost for deterministic
    noise, where repeating a query returns the same error. Do not present it as a
    classical-vs-quantum comparison for deterministic-LPN."""
    if p_key <= 0:
        return math.inf
    return n / p_key

# -----------------------------
# Concrete-construction analysis (truth table supplied from a separate, verified module)
# -----------------------------

def load_truth_table(path: str | os.PathLike) -> tuple[np.ndarray, int]:
    """Load a 0/1 truth table in input order a = 0 .. 2^n - 1.

    Accepts whitespace/comma-separated digits or one long 0/1 string. Rejects anything
    that is not binary or whose length is not a power of two.
    """
    raw = Path(path).read_text()
    digits = [c for c in raw if c in "01"]
    junk = [c for c in raw if not (c in "01" or c.isspace() or c == ",")]
    if junk:
        raise ValueError(f"Truth table contains non-binary characters, e.g. {junk[:5]!r}")
    size = len(digits)
    if size == 0 or (size & (size - 1)) != 0:
        raise ValueError(f"Truth table length {size} is not a positive power of two")
    return np.array(digits, dtype=np.uint8), size.bit_length() - 1


def analyse_truth_table(
    bits: np.ndarray,
    secret_x: int,
    label: str,
    trials: int = 300,
    seed: int = 0,
    max_k: int = 1001,
    failure_prob: float = 0.01,
) -> tuple[dict, pd.DataFrame, pd.DataFrame]:
    """Exact spectrum + tie-aware repeated-query recovery for a supplied noise truth table."""
    bits = np.asarray(bits, dtype=np.uint8)
    n = int(bits.size).bit_length() - 1
    if bits.size != 2 ** n:
        raise ValueError("Truth table length must be 2^n")
    if not 0 <= secret_x < 2 ** n:
        raise ValueError("Secret outside {0,1}^n")
    probs = bv_distribution(n, secret_x, bits)
    m = spectral_metrics(n, secret_x, bits)
    k99, curve = k99_empirical(probs, secret_x, trials, seed, max_k)
    coeff_sq = boolean_walsh_coeffs(bits) ** 2
    order = np.argsort(coeff_sq)[::-1][:16]
    top = pd.DataFrame({
        "offset_u": [format(int(u), f"0{n}b") for u in order],
        "output_j": [format(int(secret_x ^ int(u)), f"0{n}b") for u in order],
        "probability": [float(coeff_sq[u]) for u in order],
        "is_secret": [int(u) == 0 for u in order],
    })
    summary = {
        "label": label, "n": n, "secret_bits": format(secret_x, f"0{n}b"),
        "realised_tau": m["realised_tau"], "p_key": m["p_key"],
        "formula_key_fixed_weight": float((1 - 2 * m["realised_tau"]) ** 2),
        "p_competitor": m["p_competitor"], "spectral_gap": m["spectral_gap"],
        "best_offset": format(m["best_offset"], f"0{n}b"), "parseval": m["parseval"],
        "trials": trials, "seed": seed, "query_grid": "|".join(str(k) for k in K_GRID if k <= max_k),
        "k99": k99_status(k99, max_k),
        "sufficient_bound": sufficient_query_bound(m["spectral_gap"], n, failure_prob),
        "truth_table_sha256": hashlib.sha256(bits.tobytes()).hexdigest(),
    }
    return summary, top, curve


def run_concrete(table_file, key_text: str, label: str, trials: int, seed: int, max_k: int):
    try:
        path = table_file if isinstance(table_file, str) else getattr(table_file, "name", None)
        if not path:
            raise ValueError("Upload a truth-table file generated by your verified construction module.")
        bits, n = load_truth_table(path)
        secret_x = int(key_text, 2) if key_text.strip() else 0
        summary, top, curve = analyse_truth_table(bits, secret_x, label or "unlabelled construction", int(trials), int(seed), int(max_k))
        txt = "\n".join(f"{k}: {v}" for k, v in summary.items())
        return txt, top, png_array(success_plot(curve, f"Concrete construction: {summary['label']} (n={n})"))
    except Exception as exc:
        return f"ERROR: {exc}", pd.DataFrame(), b""

# -----------------------------
# Figure helpers
# -----------------------------

def fig_bytes(fig) -> bytes:
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=160, bbox_inches="tight")
    plt.close(fig)
    return buf.getvalue()


def png_array(png: bytes) -> np.ndarray:
    return np.array(Image.open(io.BytesIO(png)).convert("RGB"))


def spectrum_plot(n: int, secret_x: int, noise_bits: np.ndarray) -> bytes:
    coeff = boolean_walsh_coeffs(noise_bits)
    p = coeff ** 2
    order = np.argsort(p)[::-1][: min(32, p.size)]
    fig, ax = plt.subplots(figsize=(9, 4.8))
    ax.bar(np.arange(len(order)), p[order])
    labels = [format(int(secret_x ^ int(u)), f"0{n}b") for u in order]
    ax.set_xticks(np.arange(len(order)), labels, rotation=60, ha="right", fontsize=8)
    ax.set_ylabel("BV output probability")
    ax.set_xlabel("Output j (top probabilities)")
    ax.set_title("BV output spectrum")
    ax.grid(axis="y", alpha=0.25)
    return fig_bytes(fig)


def success_plot(curve: pd.DataFrame, title: str) -> bytes:
    fig, ax = plt.subplots(figsize=(8.5, 4.8))
    ax.plot(curve["queries"], curve["success_probability"], marker="o")
    ax.axhline(0.99, linestyle="--")
    ax.set_xlabel("Queries")
    ax.set_ylabel("P[unique empirical mode = secret]")
    ax.set_ylim(-0.02, 1.02)
    ax.set_title(title)
    ax.grid(alpha=0.25)
    return fig_bytes(fig)


def tau_plot(df: pd.DataFrame) -> bytes:
    fig, ax = plt.subplots(figsize=(8.5, 4.8))
    for family in df["family"].unique():
        sub = df[df["family"] == family].sort_values("realised_tau")
        ax.plot(sub["realised_tau"], sub["p_key"], marker="o", label=family)
    xs = np.linspace(0, 0.5, 200)
    ax.plot(xs, (1 - 2 * xs) ** 2, linestyle="--", label="(1 − 2τ)^2")
    ax.set_xlabel("Realised noise rate τ")
    ax.set_ylabel("P(secret output)")
    ax.set_title("Key probability vs realised deterministic noise rate")
    ax.legend(fontsize=8)
    ax.grid(alpha=0.25)
    return fig_bytes(fig)


def bound_plot(df: pd.DataFrame) -> bytes:
    fig, ax = plt.subplots(figsize=(8.5, 4.8))
    d = df.sort_values("n")
    ax.plot(d["n"], d["k99_bound"], marker="o", label="spectral-gap sufficient bound")
    ax.plot(d["n"], d["bernoulli_hb_reference"], marker="o", linestyle="--", label="n/P(key): Bernoulli-HB reference only (NOT a deterministic-noise baseline)")
    ax.set_yscale("log")
    ax.set_xlabel("n")
    ax.set_ylabel("Queries (log scale)")
    ax.set_title("Query-cost scaling")
    ax.legend(fontsize=8)
    ax.grid(alpha=0.25, which="both")
    return fig_bytes(fig)

# -----------------------------
# Research workflow functions
# -----------------------------

def run_spectrum(
    n: int,
    key_text: str,
    family: str,
    tau: float,
    seed: int,
    and_k: int,
    linear_u: int,
    noise_key: int,
) -> tuple[str, pd.DataFrame, bytes]:
    try:
        n = int(n)
        if not 2 <= n <= 18:
            raise ValueError("Use 2 ≤ n ≤ 18 for exact interactive spectrum calculations.")
        secret_x = int(key_text, 2) if isinstance(key_text, str) and key_text.strip() else (seed % (2 ** n))
        if not 0 <= secret_x < 2 ** n:
            raise ValueError("Secret key binary string is outside the selected n.")
        bits, realised_tau, description = make_noise(n, family, float(tau), int(seed), int(and_k), int(linear_u), int(noise_key))
        probs = bv_distribution(n, secret_x, bits)
        metrics = spectral_metrics(n, secret_x, bits)
        metrics["target_tau"] = float(tau)
        metrics["noise_description"] = description
        metrics["formula_key"] = float((1 - 2 * realised_tau) ** 2)
        top = np.argsort(probs)[::-1][: min(10, probs.size)]
        rows = []
        for j in top:
            rows.append({
                "output": format(int(j), f"0{n}b"),
                "probability": float(probs[j]),
                "offset u=j⊕x": format(int(j ^ secret_x), f"0{n}b"),
                "is_secret": bool(j == secret_x),
            })
        table = pd.DataFrame(rows)
        text = (
            f"Exact analysis completed.\n\n"
            f"n={n}, secret x={format(secret_x, f'0{n}b')}, family={family}\n"
            f"Target τ={tau:.6f}, realised τ={realised_tau:.6f}\n"
            f"P(secret)={metrics['p_key']:.8f}; best competitor={metrics['p_competitor']:.8f}\n"
            f"Spectral gap Δ={metrics['spectral_gap']:.8f}\n"
            f"Best competing offset u={format(metrics['best_offset'], f'0{n}b')}\n"
            f"Parseval check Σ ĝ(u)^2={metrics['parseval']:.12f}\n"
            f"The exact key-probability formula from the realised weight is (1−2τ_realised)^2="
            f"{metrics['formula_key']:.8f}."
        )
        return text, table, png_array(spectrum_plot(n, secret_x, bits))
    except Exception as exc:
        return f"ERROR: {exc}", pd.DataFrame(), b""


def run_attack(
    n: int,
    key_text: str,
    family: str,
    tau: float,
    seed: int,
    and_k: int,
    linear_u: int,
    noise_key: int,
    trials: int,
    max_k: int,
) -> tuple[str, pd.DataFrame, bytes]:
    try:
        n = int(n)
        if not 2 <= n <= 16:
            raise ValueError("Use 2 ≤ n ≤ 16 for repeated-query Monte Carlo.")
        secret_x = int(key_text, 2) if key_text.strip() else (seed % (2 ** n))
        bits, realised_tau, _ = make_noise(n, family, float(tau), int(seed), int(and_k), int(linear_u), int(noise_key))
        probs = bv_distribution(n, secret_x, bits)
        metrics = spectral_metrics(n, secret_x, bits)
        metrics["target_tau"] = tau
        k99, curve = k99_empirical(probs, secret_x, int(trials), int(seed) + 101, int(max_k))
        theoretical = sufficient_query_bound(metrics["spectral_gap"], n, 0.01)
        txt = (
            f"Repeated BV attack completed.\n\n"
            f"n={n}, x={format(secret_x, f'0{n}b')}, family={family}, seed={seed}, realised τ={realised_tau:.6f}\n"
            f"P(x)={metrics['p_key']:.8f}, competitor={metrics['p_competitor']:.8f}, Δ={metrics['spectral_gap']:.8f}\n"
            f"Empirical k99 (P[unique mode = secret] ≥ 0.99 in {trials} trials, grid {list(k for k in K_GRID if k <= int(max_k))}): {k99_status(k99, int(max_k))}\n"
            f"Sufficient Hoeffding/union-bound k99-style guarantee: "
            f"{math.ceil(theoretical) if math.isfinite(theoretical) else 'infinite'}\n"
            f"Note: the analytic bound is a sufficient concentration bound, not an observed optimum."
        )
        return txt, curve, png_array(success_plot(curve, f"Repeated BV recovery (n={n})"))
    except Exception as exc:
        return f"ERROR: {exc}", pd.DataFrame(), b""


def run_experiment_suite(
    n_values_text: str,
    tau_values_text: str,
    seeds_per_point: int,
    family: str,
    and_k: int,
    linear_u: int,
    noise_key: int,
) -> tuple[str, pd.DataFrame, bytes, bytes]:
    try:
        ns = [int(x.strip()) for x in n_values_text.split(",") if x.strip()]
        taus = [float(x.strip()) for x in tau_values_text.split(",") if x.strip()]
        if any(n < 2 or n > 16 for n in ns):
            raise ValueError("n must be between 2 and 16 for the suite.")
        rows = []
        for n in ns:
            x = (7 * n + 3) % (2 ** n)
            for tau in taus:
                for rep in range(int(seeds_per_point)):
                    seed = 1000 + rep + 31 * n
                    bits, realised_tau, _ = make_noise(n, family, tau, seed, and_k, linear_u, noise_key)
                    p = bv_distribution(n, x, bits)
                    m = spectral_metrics(n, x, bits)
                    k99, _ = k99_empirical(p, x, max(150, min(500, 20 * n)), seed + 77, 501) if n <= 14 else (None, pd.DataFrame())
                    rows.append({
                        "n": n,
                        "target_tau": tau,
                        "realised_tau": realised_tau,
                        "seed": seed,
                        "family": family,
                        "p_key": m["p_key"],
                        "p_competitor": m["p_competitor"],
                        "spectral_gap": m["spectral_gap"],
                        "k99_empirical": k99 if k99 is not None else np.nan,
                        "k99_bound": sufficient_query_bound(m["spectral_gap"], n, 0.01),
                        "bernoulli_hb_reference": bernoulli_hb_reference(n, m["p_key"]),
                        "k99_status": k99_status(k99, 501),
                        "mc_trials": max(150, min(500, 20 * n)) if n <= 14 else 0,
                        "query_grid": "|".join(str(k) for k in K_GRID if k <= 501),
                        "secret_bits": format(x, f"0{n}b"),
                        "secret_rule": "x=(7n+3) mod 2^n",
                        "seed_rule": "seed=1000+rep+31n",
                    })
        df = pd.DataFrame(rows)
        csv_path = OUTPUT_DIR / "experiment_suite.csv"
        df.to_csv(csv_path, index=False)
        plot1 = tau_plot(df)
        (OUTPUT_DIR / "fig_tau_vs_pkey.png").write_bytes(plot1)
        grouped = (
            df.groupby("n", as_index=False)
            .agg(k99_bound=("k99_bound", "median"), bernoulli_hb_reference=("bernoulli_hb_reference", "median"))
        )
        plot2 = bound_plot(grouped)
        (OUTPUT_DIR / "fig_query_scaling.png").write_bytes(plot2)
        summary = (
            f"Suite completed: {len(df)} measured rows.\n"
            f"Raw data: {csv_path}\n"
            f"Mean P(key): {df['p_key'].mean():.6f}\n"
            f"Minimum spectral gap: {df['spectral_gap'].min():.6f}\n"
            f"Rows with positive gap: {(df['spectral_gap'] > 0).mean() * 100:.1f}%\n"
            f"Every row records realised τ; no requested τ is silently substituted."
        )
        return summary, df, png_array(plot1), png_array(plot2)
    except Exception as exc:
        return f"ERROR: {exc}", pd.DataFrame(), b"", b""


def run_failure(n: int, max_k: int) -> tuple[str, pd.DataFrame, bytes]:
    try:
        n = int(n)
        k = min(2, n)
        x = 3 % (2 ** n)
        bits, tau = and_k_noise(n, k)
        p = bv_distribution(n, x, bits)
        m = spectral_metrics(n, x, bits)
        k99, curve = k99_empirical(p, x, 300, 9090, int(max_k))
        top = np.argsort(p)[::-1][: 8]
        table = pd.DataFrame({
            "output": [format(int(j), f"0{n}b") for j in top],
            "probability": [float(p[j]) for j in top],
            "output_offset_u": [format(int(j ^ x), f"0{n}b") for j in top],
        })
        txt = (
            f"AND-{k} failure/control case.\n\n"
            f"n={n}, secret={format(x, f'0{n}b')}, realised τ={tau:.6f}\n"
            f"P(secret)={m['p_key']:.6f}, best competitor={m['p_competitor']:.6f}, Δ={m['spectral_gap']:.6f}\n"
            f"Empirical k99 (tie-aware, 300 trials): {k99_status(k99, int(max_k))}\n"
            f"Tie rate at the largest checked k: {float(curve['tie_rate'].iloc[-1]):.3f}\n\n"
            f"Interpretation: this is a spectral ambiguity example. A tie is not evidence that the noise is merely 'strong'; it means the noise function has multiple equally large Walsh coefficients."
        )
        # Plot the probability curve as an optional failure figure.
        fig = plt.figure(figsize=(8.5, 4.8))
        ax = fig.add_subplot(111)
        ax.bar(np.arange(len(top)), p[top])
        ax.set_xticks(np.arange(len(top)), [format(int(j), f"0{n}b") for j in top], rotation=60, ha="right")
        ax.set_ylabel("Probability")
        ax.set_title(f"Failure/control case: AND-{k} noise, n={n}")
        ax.grid(axis="y", alpha=0.25)
        png = fig_bytes(fig)
        return txt, table, png_array(png)
    except Exception as exc:
        return f"ERROR: {exc}", pd.DataFrame(), b""


def run_extension_depolarising(
    n: int,
    key_text: str,
    family: str,
    tau: float,
    seed: int,
    p_depol: float,
    and_k: int,
    linear_u: int,
    noise_key: int,
) -> tuple[str, pd.DataFrame, bytes]:
    try:
        n = int(n)
        secret_x = int(key_text, 2) if key_text.strip() else 5 % (2 ** n)
        bits, realised_tau, _ = make_noise(n, family, tau, seed, and_k, linear_u, noise_key)
        ideal = bv_distribution(n, secret_x, bits)
        N = ideal.size
        noisy = (1 - p_depol) * ideal + p_depol * np.full(N, 1.0 / N)
        m_ideal = spectral_metrics(n, secret_x, bits)
        # Spectral probability gap after classicalised depolarising readout noise.
        p_key = float(noisy[secret_x])
        competitor = float(np.max(np.delete(noisy, secret_x)))
        gap = p_key - competitor
        rows = pd.DataFrame({
            "quantity": ["realised_tau", "ideal_P(key)", "noisy_P(key)", "noisy_best_competitor", "noisy_gap"],
            "value": [realised_tau, m_ideal["p_key"], p_key, competitor, gap],
        })
        txt = (
            f"Extension completed: output-depolarising readout model.\n\n"
            f"n={n}, p_depol={p_depol:.4f}, realised τ={realised_tau:.6f}\n"
            f"Ideal P(key)={m_ideal['p_key']:.8f}\n"
            f"Noisy P(key)={p_key:.8f}; noisy best competitor={competitor:.8f}; Δ_noisy={gap:.8f}\n"
            f"This extension is deliberately a device/readout robustness experiment, not a full physical noise model."
        )
        fig = plt.figure(figsize=(8.5, 4.8))
        ax = fig.add_subplot(111)
        ax.bar([0, 1], [m_ideal["p_key"], p_key], tick_label=["ideal", "depolarised"])
        ax.set_ylabel("P(key)")
        ax.set_title("Extension: readout depolarising noise")
        ax.grid(axis="y", alpha=0.25)
        return txt, rows, png_array(fig_bytes(fig))
    except Exception as exc:
        return f"ERROR: {exc}", pd.DataFrame(), b""

# -----------------------------
# Export bundle
# -----------------------------

def make_report_and_bundle(
    summary: str,
    results_csv: str | None,
    spectrum_text: str,
    attack_text: str,
    failure_text: str,
    extension_text: str,
) -> tuple[str, str | None, str | None]:
    report_md = OUTPUT_DIR / "research_report.md"
    report_pdf = OUTPUT_DIR / "research_report.pdf"
    bundle = OUTPUT_DIR / "hb_research_app_bundle.zip"

    md = f"""# {PROJECT_TITLE}\n\n## Research basis\n{SOURCE_PAPER}\n\n## Research question\nWhen does deterministic, input-dependent noise suppress or preserve Bernstein–Vazirani key recovery under Q2 access?\n\n## Exact characterization\nFor noise bits e(a), define h(a)=(-1)^e(a). The BV output probabilities satisfy:\n\n$$P(j)=|\\widehat h(x\\oplus j)|^2.$$\n\nThe key probability is $$P(x)=|\\widehat h(0)|^2=(1-2\\tau_{{realised}})^2$$ when the realised noise function has exactly weight \\tau_realised 2^n.\n\nDefine the spectral gap $$\\Delta=P(x)-\\max_{{u\\ne0}}|\\widehat h(u)|^2.$$ A unique positive gap is a sufficient structural condition for the secret to be the unique modal output.\n\n## Measured suite\n{summary}\n\n## Interactive spectrum output\n{spectrum_text}\n\n## Repeated-query output\n{attack_text}\n\n## Failure/control case\n{failure_text}\n\n## Extension\n{extension_text}\n\n## Interpretation and limitations\n- Exact simulation assumes an ideal Q2 phase oracle and perfect quantum gates.\n- The keyed deterministic family in this app is a reproducible research control and is **not claimed to be a cryptographic PRF**.\n- Small/medium n does not establish asymptotic security or insecurity.\n- Empirical k99 is a Monte Carlo estimate; the concentration bound is sufficient rather than necessarily tight.\n- Novelty must be established by a complete literature review; this app does not make a “first/novel” claim.\n\n## Reproducibility\nAll numerical experiments record the seed and realised noise rate where applicable.\n\n## Authorship\nState author contributions accurately.\n"""
    report_md.write_text(md, encoding="utf-8")

    styles = getSampleStyleSheet()
    body = ParagraphStyle("body", parent=styles["BodyText"], fontSize=8.5, leading=11)
    heading = ParagraphStyle("heading", parent=styles["Heading2"], fontSize=12, leading=14, spaceBefore=8, spaceAfter=5)
    doc = SimpleDocTemplate(str(report_pdf), pagesize=A4, leftMargin=1.5 * cm, rightMargin=1.5 * cm, topMargin=1.3 * cm, bottomMargin=1.3 * cm)
    story = [Paragraph(PROJECT_TITLE, styles["Title"]), Spacer(1, 6)]
    story.append(Paragraph("Research basis", heading))
    story.append(Paragraph(SOURCE_PAPER, body))
    story.append(Paragraph("Research question", heading))
    story.append(Paragraph("When does deterministic, input-dependent noise suppress or preserve Bernstein–Vazirani key recovery under Q2 access?", body))
    story.append(Paragraph("Core theory", heading))
    story.append(Paragraph("P(j)=|h-hat(x xor j)|², where h(a)=(-1)^e(a). When the realised noise function has exact weight τ·2^n, P(x)=(1−2τ)². The spectral gap Δ=P(x)−max_{u≠0}|h-hat(u)|² controls whether the secret is uniquely dominant.", body))
    story.append(Paragraph("Measured outputs", heading))
    for title, txt in [("Suite", summary), ("Spectrum", spectrum_text), ("Repeated attack", attack_text), ("Failure case", failure_text), ("Extension", extension_text)]:
        story.append(Paragraph(title, styles["Heading3"]))
        story.append(Paragraph(txt.replace("&", "&amp;").replace("\n", "<br/>"), body))
    story.append(Paragraph("Limitations", heading))
    story.append(Paragraph("The model is an ideal Q2 phase-oracle simulation. The keyed deterministic family is only a reproducible control, not a cryptographic PRF claim. Empirical k99 values are Monte Carlo estimates; the analytic bound is sufficient, not necessarily tight. Novelty must be established by a full literature review.", body))
    doc.build(story)

    files_to_zip = [Path(__file__), report_md, report_pdf]
    if results_csv and Path(results_csv).exists():
        files_to_zip.append(Path(results_csv))
    for p in OUTPUT_DIR.glob("fig_*.png"):
        files_to_zip.append(p)
    with zipfile.ZipFile(bundle, "w", compression=zipfile.ZIP_DEFLATED) as z:
        for p in files_to_zip:
            z.write(p, arcname=p.name)

    return f"Created research report and bundle in {OUTPUT_DIR}.", str(report_pdf), str(bundle)

# -----------------------------
# UI
# -----------------------------

def app():
    if gr is None:
        raise SystemExit("The interactive app needs gradio: pip install gradio")
    theme = gr.themes.Soft(primary_hue="indigo", secondary_hue="slate")
    with gr.Blocks(theme=theme, title="HB Deterministic Noise Research Lab") as demo:
        gr.Markdown(f"# {PROJECT_TITLE}")
        gr.Markdown(
            "A single research lab for the mathematical characterization, exact simulation, repeated-query attack, "
            "failure analysis, experiment suite, and extension. **The app distinguishes research controls from cryptographic construction claims.**"
        )

        with gr.Tab("Demo output"):
            gr.Markdown("### Precomputed run included with this package")
            gr.Markdown(
                """**Suite:** 80 rows; mean P(key)=0.415548; minimum spectral gap=0.006104; 100% of measured rows had a positive gap in this particular random fixed-weight control suite.

**Repeated attack example:** n=10, x=0000101101, keyed deterministic research control (not a PRF), seed 43, τ=0.25: P(key)=0.25, best competitor=0.01196289, Δ=0.23803711, empirical k99=51 under the tie-aware estimator (300 trials per checked k; the pre-audit value 25 came from argmax tie-breaking). The sufficient concentration bound was 432 queries and is deliberately labelled a conservative bound rather than an optimum.

**Failure example:** AND-2 at n=10 gives P(key)=0.25, best competitor=0.25, Δ=0; empirical k99 was not reached.

**Extension:** with 5% output-depolarising noise, P(key) fell from 0.25 to 0.23754883 in the same example."""
            )
            demo_csv = gr.File(value=str(OUTPUT_DIR / "experiment_suite.csv"), label="Measured CSV", interactive=False)
            demo_fig = gr.Image(value=str(OUTPUT_DIR / "fig_tau_vs_pkey.png"), label="Suite figure", type="filepath", interactive=False)

        with gr.Tab("Research brief"):
            gr.Markdown(
                """
### Core question
When does deterministic, input-dependent noise suppress or preserve Bernstein–Vazirani key recovery under Q2 access?

### Exact identity used by the app
For `h(a)=(-1)^e(a)`:

`P(j) = |Walsh(h)(x XOR j)|²`.

If the realised noise function has exactly `τ·2^n` ones, then:

`P(x) = (1 − 2τ)²`.

The main structural quantity is:

`Δ = P(x) − max_{u != 0} |Walsh(h)(u)|²`.

A positive gap means the secret is uniquely dominant in the ideal BV distribution. A zero gap gives a tie; a negative gap means another output is more likely.

### Important boundary
The **keyed deterministic** family in this app is a reproducible control, not a cryptographic PRF claim and not a substitute for a concrete published deterministic-LPN construction. Use concrete published constructions separately when making cryptographic claims.

### Source
""" + SOURCE_PAPER)

        with gr.Tab("Spectrum lab"):
            with gr.Row():
                n = gr.Slider(2, 18, value=8, step=1, label="n")
                key = gr.Textbox(value="0000101101", label="Secret x (binary)")
            with gr.Row():
                family = gr.Dropdown([
                    "Bernoulli (global phase control)",
                    "Random deterministic (fixed weight)",
                    "AND-k (toy low-depth)",
                    "Linear (toy failure/control)",
                    "Keyed deterministic (PRF-like control, NOT a PRF claim)",
                ], value="Random deterministic (fixed weight)", label="Noise family")
                tau = gr.Slider(0.0, 0.5, value=0.25, step=0.001, label="Target τ")
            with gr.Row():
                seed = gr.Number(value=42, precision=0, label="Seed")
                and_k = gr.Slider(1, 8, value=2, step=1, label="AND k")
                linear_u = gr.Number(value=1, precision=0, label="Linear u (integer)")
                noise_key = gr.Number(value=12345, precision=0, label="Noise key")
            run_btn = gr.Button("Run exact spectrum", variant="primary")
            spectrum_text = gr.Textbox(label="Analysis", lines=10)
            spectrum_table = gr.Dataframe(label="Top BV outcomes", interactive=False)
            spectrum_image = gr.Image(label="Spectrum figure", type="numpy")
            run_btn.click(
                run_spectrum,
                [n, key, family, tau, seed, and_k, linear_u, noise_key],
                [spectrum_text, spectrum_table, spectrum_image],
            )

        with gr.Tab("Repeated BV attack"):
            with gr.Row():
                rn = gr.Slider(2, 16, value=10, step=1, label="n")
                rkey = gr.Textbox(value="0000101101", label="Secret x (binary)")
            with gr.Row():
                rfamily = gr.Dropdown([
                    "Bernoulli (global phase control)",
                    "Random deterministic (fixed weight)",
                    "AND-k (toy low-depth)",
                    "Linear (toy failure/control)",
                    "Keyed deterministic (PRF-like control, NOT a PRF claim)",
                ], value="Keyed deterministic (PRF-like control, NOT a PRF claim)", label="Noise family")
                rtau = gr.Slider(0.0, 0.5, value=0.25, step=0.001, label="Target τ")
            with gr.Row():
                rseed = gr.Number(value=43, precision=0, label="Seed")
                trials = gr.Slider(50, 1000, value=300, step=50, label="Monte Carlo trials per k")
                max_k = gr.Slider(101, 1001, value=501, step=50, label="Maximum k checked")
            with gr.Row():
                randk = gr.Slider(1, 8, value=2, step=1, label="AND k")
                rlinearu = gr.Number(value=1, precision=0, label="Linear u")
                rnoise_key = gr.Number(value=12345, precision=0, label="Noise key")
            attack_btn = gr.Button("Run repeated-query attack", variant="primary")
            attack_text = gr.Textbox(label="Attack analysis", lines=10)
            attack_table = gr.Dataframe(label="Success curve", interactive=False)
            attack_image = gr.Image(label="Success plot", type="numpy")
            attack_btn.click(
                run_attack,
                [rn, rkey, rfamily, rtau, rseed, randk, rlinearu, rnoise_key, trials, max_k],
                [attack_text, attack_table, attack_image],
            )

        with gr.Tab("Experiment suite"):
            gr.Markdown("Runs a controlled grid and saves raw measurements to CSV. For each row, the app records **realised τ**.")
            n_values = gr.Textbox(value="8,10,12,14", label="n values")
            tau_values = gr.Textbox(value="0.05,0.125,0.25,0.4", label="target τ values")
            seeds_per = gr.Slider(1, 20, value=5, step=1, label="Seeds per point")
            suite_family = gr.Dropdown([
                "Random deterministic (fixed weight)",
                "Keyed deterministic (PRF-like control, NOT a PRF claim)",
            ], value="Random deterministic (fixed weight)", label="Main noise family")
            with gr.Row():
                suite_andk = gr.Slider(1, 8, value=2, step=1, label="AND k (control only)")
                suite_linearu = gr.Number(value=1, precision=0, label="Linear u (control only)")
                suite_noise_key = gr.Number(value=12345, precision=0, label="Noise key")
            suite_btn = gr.Button("Run research suite", variant="primary")
            suite_text = gr.Textbox(label="Suite summary", lines=10)
            suite_table = gr.Dataframe(label="Raw measurements", interactive=False)
            suite_tau_fig = gr.Image(label="Figure 1 — P(key) vs realised τ", type="numpy")
            suite_bound_fig = gr.Image(label="Figure 2 — query-cost scaling", type="numpy")
            suite_btn.click(
                run_experiment_suite,
                [n_values, tau_values, seeds_per, suite_family, suite_andk, suite_linearu, suite_noise_key],
                [suite_text, suite_table, suite_tau_fig, suite_bound_fig],
            )

        with gr.Tab("Failure / spectral ambiguity"):
            gr.Markdown(
                "The AND-2 construction is a deliberately simple failure/control case. Its value is diagnostic: it shows that repeated measurements do not solve a spectral tie merely by increasing the query count."
            )
            fn = gr.Slider(3, 14, value=10, step=1, label="n")
            fmaxk = gr.Slider(101, 1001, value=501, step=50, label="Maximum queries checked")
            fbtn = gr.Button("Run failure case", variant="primary")
            ftext = gr.Textbox(label="Failure analysis", lines=10)
            ftable = gr.Dataframe(label="Top outputs", interactive=False)
            fimage = gr.Image(label="Failure spectrum", type="numpy")
            fbtn.click(run_failure, [fn, fmaxk], [ftext, ftable, fimage])

        with gr.Tab("Concrete construction"):
            gr.Markdown(
                "Upload the 2^n truth table produced by a **published deterministic-LPN construction** implemented and verified in "
                "`constructions/`. Do not upload the keyed research control here. Write your dated prediction in `notes/predictions/` first."
            )
            with gr.Row():
                cfile = gr.File(label="Truth table (0/1, input order a=0..2^n-1)")
                ckey = gr.Textbox(value="", label="Secret x (binary, n bits)")
                clabel = gr.Textbox(value="", label="Construction id / version / parameters")
            with gr.Row():
                ctrials = gr.Number(value=300, precision=0, label="Monte Carlo trials per k")
                cseed = gr.Number(value=0, precision=0, label="Seed")
                cmaxk = gr.Number(value=1001, precision=0, label="Max k")
            cbtn = gr.Button("Analyse construction", variant="primary")
            ctext = gr.Textbox(label="Exact + empirical analysis", lines=16)
            ctable = gr.Dataframe(label="Largest spectral components", interactive=False)
            cimage = gr.Image(label="Recovery curve", type="numpy")
            cbtn.click(run_concrete, [cfile, ckey, clabel, ctrials, cseed, cmaxk], [ctext, ctable, cimage])

        with gr.Tab("Original extension"):
            gr.Markdown(
                "This app's built-in extension adds a simple output-depolarising/readout-noise model after the ideal BV distribution. It is intentionally labelled as a robustness experiment, not as a full physical noise model."
            )
            with gr.Row():
                en = gr.Slider(2, 16, value=10, step=1, label="n")
                ekey = gr.Textbox(value="0000101101", label="Secret x (binary)")
                etau = gr.Slider(0.0, 0.5, value=0.25, step=0.001, label="Target τ")
            with gr.Row():
                efamily = gr.Dropdown([
                    "Random deterministic (fixed weight)",
                    "Keyed deterministic (PRF-like control, NOT a PRF claim)",
                    "AND-k (toy low-depth)",
                ], value="Keyed deterministic (PRF-like control, NOT a PRF claim)", label="Noise family")
                ep = gr.Slider(0.0, 1.0, value=0.05, step=0.005, label="Depolarising probability")
                eseed = gr.Number(value=44, precision=0, label="Seed")
            with gr.Row():
                eandk = gr.Slider(1, 8, value=2, step=1, label="AND k")
                elinearu = gr.Number(value=1, precision=0, label="Linear u")
                enoise_key = gr.Number(value=12345, precision=0, label="Noise key")
            ebtn = gr.Button("Run extension", variant="primary")
            etext = gr.Textbox(label="Extension analysis", lines=10)
            etable = gr.Dataframe(label="Extension metrics", interactive=False)
            eimage = gr.Image(label="Extension figure", type="numpy")
            ebtn.click(
                run_extension_depolarising,
                [en, ekey, efamily, etau, eseed, ep, eandk, elinearu, enoise_key],
                [etext, etable, eimage],
            )

        with gr.Tab("Export"):
            gr.Markdown("Run the suite first, then package the app, raw CSV (when present), figures, and a compact research report.")
            summary_in = gr.Textbox(label="Paste suite summary", lines=6)
            csv_in = gr.Textbox(value=str(OUTPUT_DIR / "experiment_suite.csv"), label="CSV path (optional)")
            spec_in = gr.Textbox(label="Spectrum output", lines=6)
            attack_in = gr.Textbox(label="Attack output", lines=6)
            failure_in = gr.Textbox(label="Failure output", lines=6)
            extension_in = gr.Textbox(label="Extension output", lines=6)
            export_btn = gr.Button("Create research report + ZIP bundle", variant="primary")
            export_status = gr.Textbox(label="Export status", lines=4)
            pdf_file = gr.File(label="Research PDF")
            zip_file = gr.File(label="Complete ZIP bundle")
            export_btn.click(
                make_report_and_bundle,
                [summary_in, csv_in, spec_in, attack_in, failure_in, extension_in],
                [export_status, pdf_file, zip_file],
            )

        gr.Markdown(
            "**Research integrity:** use the app to measure and debug, but write your derivations, predictions, interpretation, and authorship statement truthfully. Do not report unmeasured numbers or claim novelty without a literature review."
        )
    return demo


if __name__ == "__main__":
    app().launch()
