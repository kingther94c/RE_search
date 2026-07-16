"""EXP-0011 / L2a: fit the landed land-size curve (psf ~ area^elasticity).

Replaces LC1's ported CRAFT_SIZE_ELASTICITY = -0.877 — derived from ONE street's two
cross-size legs in the Cardiff Grove #19 craft valuation (guardrail-#5: unvalidated
globally). L1 proved this is the dominant error axis: LC1 median APE runs 8.8% at
1.5-3k sqft -> 41.2% at 15k+ (monotone), so the curve is the highest-leverage module.

THREE estimators, so the answer does not rest on one design:
  A. WITHIN-STREET FIXED EFFECTS (primary). Demean ln(psf_adj) and ln(area) inside each
     (street, type) group, then regress demeaned-on-demeaned. This is the FE estimator:
     it identifies the size effect from CROSS-SIZE VARIATION INSIDE A STREET, so street
     location/prestige cannot contaminate it, and it uses every row (not just pairs).
  B. NEAR-SIMULTANEOUS PAIRS (cross-check). Same street+type, gap <= 6mo, size gap >= 15%:
     elasticity = ln(psf_a/psf_b) / ln(area_a/area_b). No index reliance at all.
  C. BY SIZE BUCKET (functional-form test). If a single log-log elasticity were adequate,
     the bucketed FE slopes would be flat. L1's monotone error explosion predicts they
     are NOT — this is the test that decides constant-vs-varying.

LEAKAGE DISCIPLINE: the backtest subject window starts 2023-01, so a curve fitted on the
FULL store embeds future information. Every estimate is therefore ALSO computed on
PRE-2023 data only; if the two agree, the constant is structural (not a price signal) and
the pre-2023 value is what ships. Disagreement => the curve is regime-dependent and must
be fitted as-of inside the harness.

    python research/fit_land_size_curve.py
"""
from __future__ import annotations

import math
import os
import random
import sys
from collections import defaultdict
from statistics import median

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from researcher.backtest.index import PriceIndex
from researcher.backtest.store import TransactionStore, months_between

PAIR_MAX_MONTHS = 6
PAIR_MIN_LOG_AREA = 0.14      # >=15% size gap: elasticity is ill-defined near ratio 1
PAIRS_PER_STREET = 200
MIN_GROUP = 2                 # a (street,type) group needs >=2 rows to contribute FE variation
REF_YM = "2026-01"            # common base for index-adjusting psf before the FE fit


def _adj_psf(t, idx, ref=REF_YM):
    """Index-adjust a print's land-psf to a common base so TIME doesn't load onto SIZE."""
    f = idx.factor(t["contract_ym"], ref, "landed") or 1.0
    return t["psf"] * f


def _fe_slope(rows, idx):
    """Within-(street,type) FE slope of ln(psf) on ln(area). Returns (slope, n_used, n_groups)."""
    groups = defaultdict(list)
    for t in rows:
        groups[(t["street"], t["property_type"])].append(t)
    sxx = sxy = 0.0
    n_used = n_groups = 0
    for g in groups.values():
        if len(g) < MIN_GROUP:
            continue
        la = [math.log(t["area_sqft"]) for t in g]
        lp = [math.log(_adj_psf(t, idx)) for t in g]
        ma, mp = sum(la) / len(la), sum(lp) / len(lp)
        # skip degenerate groups where every plot is the same size (no size variation)
        if max(la) - min(la) < 1e-9:
            continue
        n_groups += 1
        for a, p in zip(la, lp):
            da, dp = a - ma, p - mp
            sxx += da * da
            sxy += da * dp
            n_used += 1
    return (sxy / sxx if sxx > 1e-12 else float("nan")), n_used, n_groups


def _pair_elasticities(rows):
    """Near-simultaneous same-street same-type cross-size pairs (no index used)."""
    by_st = defaultdict(list)
    for t in rows:
        by_st[(t["street"], t["property_type"])].append(t)
    out = []
    rng = random.Random(42)
    for g in by_st.values():
        if len(g) < 2:
            continue
        pairs = [(a, b) for i, a in enumerate(g) for b in g[i + 1:]]
        if len(pairs) > PAIRS_PER_STREET:
            pairs = rng.sample(pairs, PAIRS_PER_STREET)
        for a, b in pairs:
            if abs(months_between(a["contract_ym"], b["contract_ym"])) > PAIR_MAX_MONTHS:
                continue
            la = math.log(a["area_sqft"] / b["area_sqft"])
            if abs(la) < PAIR_MIN_LOG_AREA:
                continue
            e = math.log(a["psf"] / b["psf"]) / la
            if -3.0 < e < 1.0:
                out.append(e)
    return out


def _bucket(a):
    return ("1.5-3k" if a < 3000 else "3-5k" if a < 5000 else "5-8k" if a < 8000
            else "8-15k" if a < 15000 else "15k+")


def main():
    store = TransactionStore.load()
    landed = [t for t in store.exclude_bulk().is_landed().txs
              if t["type_of_area"].lower() == "land" and t["street"]
              and 100 <= t["psf"] <= 6500]
    idx = PriceIndex.load()
    pre = [t for t in landed if t["contract_ym"] < "2023-01"]
    print(f"pure-landed rows: {len(landed):,}  (pre-2023: {len(pre):,})")

    print("\n=== A. WITHIN-STREET FE slope of ln(psf) on ln(area) ===")
    for label, rows in (("FULL store", landed), ("PRE-2023 only", pre)):
        s, n, g = _fe_slope(rows, idx)
        print(f"  {label:<14} elasticity={s:+.3f}  (n={n:,} rows in {g:,} street-type groups)")

    print("\n  by TYPE (full / pre-2023):")
    for ty in ("Terrace", "Semi-detached", "Detached"):
        f_s, f_n, _ = _fe_slope([t for t in landed if t["property_type"] == ty], idx)
        p_s, p_n, _ = _fe_slope([t for t in pre if t["property_type"] == ty], idx)
        print(f"    {ty:<14} {f_s:+.3f} (n={f_n:,})   /   {p_s:+.3f} (n={p_n:,})")

    print("\n  by TENURE (full):")
    for tn in ("freehold", "freehold_equiv", "leasehold"):
        s, n, _ = _fe_slope([t for t in landed if t["tenure_type"] == tn], idx)
        print(f"    {tn:<16} {s:+.3f} (n={n:,})")

    print("\n  by SEGMENT (full):")
    for sg in ("CCR", "RCR", "OCR"):
        s, n, _ = _fe_slope([t for t in landed if t["market_segment"] == sg], idx)
        print(f"    {sg:<4} {s:+.3f} (n={n:,})")

    print("\n=== C. FUNCTIONAL FORM: FE slope BY SIZE BUCKET (flat => one constant is enough) ===")
    for b in ("1.5-3k", "3-5k", "5-8k", "8-15k", "15k+"):
        rows = [t for t in landed if _bucket(t["area_sqft"]) == b]
        s, n, g = _fe_slope(rows, idx)
        print(f"  {b:<7} elasticity={s:+.3f}  (n={n:,} in {g:,} groups)")

    print("\n  same buckets on PRE-2023 only (the leakage-safe values that would ship):")
    for b in ("1.5-3k", "3-5k", "5-8k", "8-15k", "15k+"):
        rows = [t for t in pre if _bucket(t["area_sqft"]) == b]
        s, n, g = _fe_slope(rows, idx)
        print(f"    {b:<7} {s:+.3f}  (n={n:,} in {g:,} groups)")

    print("\n  IS TYPE STILL LIVE AFTER SIZE CONTROL? (FE slope by type WITHIN a size band)")
    for b in ("1.5-3k", "3-5k", "5-8k"):
        line = f"    {b:<7}"
        for ty in ("Terrace", "Semi-detached", "Detached"):
            rows = [t for t in landed
                    if _bucket(t["area_sqft"]) == b and t["property_type"] == ty]
            s, n, _ = _fe_slope(rows, idx)
            line += f"  {ty[:4]}={s:+.3f}(n={n:,})" if n else f"  {ty[:4]}=--"
        print(line)

    print("\n=== B. NEAR-SIMULTANEOUS PAIRS (cross-check, no index) ===")
    for label, rows in (("FULL store", landed), ("PRE-2023 only", pre)):
        es = _pair_elasticities(rows)
        if es:
            s = sorted(es)
            print(f"  {label:<14} median={median(es):+.3f}  p25={s[len(s)//4]:+.3f} "
                  f"p75={s[3*len(s)//4]:+.3f}  (n={len(es):,} pairs)")
    for ty in ("Terrace", "Semi-detached", "Detached"):
        es = _pair_elasticities([t for t in landed if t["property_type"] == ty])
        if es:
            print(f"    {ty:<14} median={median(es):+.3f} (n={len(es):,})")

    print(f"\ncurrent ported constant in landed_benchmarks.py: {-0.877}")


if __name__ == "__main__":
    main()
