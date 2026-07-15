"""Valuation error metrics — pure, no dependencies. The mandate's required minimum.

Everything operates on price (SGD) by default; APE is scale-free so psf/price agree.
Pass (pred, actual) pairs; optionally (lo, hi) interval bounds for coverage/width.
"""
from __future__ import annotations

from statistics import median


def ape(pred: float, actual: float) -> float:
    """Absolute percentage error. |pred-actual|/|actual|."""
    return abs(pred - actual) / abs(actual)


def _pct(sorted_vals: list[float], q: float) -> float:
    """Linear-interpolated percentile of an already-sorted list. q in [0,1]."""
    if not sorted_vals:
        return float("nan")
    if len(sorted_vals) == 1:
        return sorted_vals[0]
    pos = q * (len(sorted_vals) - 1)
    lo = int(pos)
    frac = pos - lo
    hi = min(lo + 1, len(sorted_vals) - 1)
    return sorted_vals[lo] + (sorted_vals[hi] - sorted_vals[lo]) * frac


def summarise(rows: list[dict]) -> dict:
    """Aggregate per-subject rows into the mandate's required metric set.

    Each row must have `pred` and `actual`; `lo`/`hi` are optional (interval coverage).
    Rows with a None `pred` (method declined to value) are counted as `n_declined`
    and excluded from error stats — a method that refuses to guess is not penalised
    on accuracy, only on coverage (how often it can produce a number).
    """
    scored = [r for r in rows if r.get("pred") is not None and r.get("actual")]
    n_total = len(rows)
    n = len(scored)
    if n == 0:
        return {"n": 0, "n_total": n_total, "n_declined": n_total,
                "coverage_rate": 0.0}
    apes = sorted(ape(r["pred"], r["actual"]) for r in scored)
    signed = [(r["pred"] - r["actual"]) / r["actual"] for r in scored]
    maes = [abs(r["pred"] - r["actual"]) for r in scored]
    out = {
        "n": n,
        "n_total": n_total,
        "n_declined": n_total - n,
        "coverage_rate": round(n / n_total, 4),
        "mae": round(sum(maes) / n, 0),
        "mean_ape": round(sum(apes) / n, 4),
        "median_ape": round(median(apes), 4),
        "p75_ape": round(_pct(apes, 0.75), 4),
        "p90_ape": round(_pct(apes, 0.90), 4),
        "pct_over_10": round(sum(1 for a in apes if a > 0.10) / n, 4),
        "signed_bias": round(sum(signed) / n, 4),
    }
    withint = [r for r in scored if r.get("lo") is not None and r.get("hi") is not None]
    if withint:
        inside = sum(1 for r in withint if r["lo"] <= r["actual"] <= r["hi"])
        widths = [(r["hi"] - r["lo"]) / r["actual"] for r in withint]
        out["interval_coverage"] = round(inside / len(withint), 4)
        out["interval_width_rel"] = round(sum(widths) / len(widths), 4)
        out["n_interval"] = len(withint)
    return out


def compare(by_method: dict[str, list[dict]]) -> dict[str, dict]:
    """{method: rows} -> {method: summary}. Convenience for a benchmark table."""
    return {m: summarise(rows) for m, rows in by_method.items()}
