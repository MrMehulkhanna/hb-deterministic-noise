"""Group E: analyse a truth table produced by a verified published deterministic-LPN construction.

Usage (after the dated prediction file exists in notes/predictions/):

    python analyse_construction.py --table constructions/output/<name>.txt \
        --secret <n-bit binary> --label "<construction id, version, parameters>" \
        --prediction notes/predictions/concrete_construction_<date>.md \
        [--trials 300 --seed 0 --max-k 1001]

Writes outputs/construction_<slug>_{summary.json,spectrum_top.csv,recovery_curve.csv,recovery.png}.
Refuses to run without an existing prediction file, so the prediction provably predates the result
(its SHA-256 is recorded in the summary).
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import research_app as R  # noqa: E402


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--table", required=True)
    ap.add_argument("--secret", required=True, help="n-bit binary string")
    ap.add_argument("--label", required=True)
    ap.add_argument("--prediction", required=True)
    ap.add_argument("--trials", type=int, default=300)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--max-k", type=int, default=1001)
    a = ap.parse_args()

    pred = Path(a.prediction)
    if not pred.exists():
        raise SystemExit(f"Prediction file {pred} not found: write and commit it BEFORE running the analysis.")
    bits, n = R.load_truth_table(a.table)
    if len(a.secret) != n or set(a.secret) - {"0", "1"}:
        raise SystemExit(f"--secret must be exactly {n} binary digits")
    summary, top, curve = R.analyse_truth_table(bits, int(a.secret, 2), a.label, a.trials, a.seed, a.max_k)
    summary["prediction_file"] = str(pred)
    summary["prediction_sha256"] = hashlib.sha256(pred.read_bytes()).hexdigest()
    summary["table_file"] = a.table

    slug = re.sub(r"[^A-Za-z0-9]+", "_", a.label).strip("_")[:60] or "construction"
    out = Path(__file__).parent / "outputs"
    out.mkdir(exist_ok=True)
    (out / f"construction_{slug}_summary.json").write_text(json.dumps(summary, indent=2, default=float))
    top.to_csv(out / f"construction_{slug}_spectrum_top.csv", index=False)
    curve.to_csv(out / f"construction_{slug}_recovery_curve.csv", index=False)
    (out / f"construction_{slug}_recovery.png").write_bytes(R.success_plot(curve, f"{a.label} (n={n})"))
    print(json.dumps(summary, indent=2, default=float))


if __name__ == "__main__":
    main()
