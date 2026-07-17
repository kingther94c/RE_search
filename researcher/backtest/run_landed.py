"""Run the pure-landed walk-forward backtest against the L1 benchmarks (EXP-0010).

    python -m researcher.backtest.run_landed                     # all eligible subjects
    python -m researcher.backtest.run_landed --lag-days 42       # lag sensitivity
    python -m researcher.backtest.run_landed --slices            # GL1 slice panel
    python -m researcher.backtest.run_landed --dump rows.json    # per-subject rows

Store slice: pure-landed only (Land + Terrace/Semi-D/Detached), bulk excluded, landed
psf band (L0 hygiene R1-R3) — the landed methods never consume condo rows, so the condo
universe is dropped up front for speed. Subjects: resale pure-landed from --min-ym
(default 2023-01 = >=18 months of history, L0 rule R5).
"""
from __future__ import annotations

import argparse
import json
import os

from .harness import walk_forward
from .landed_benchmarks import LANDED_BENCHMARKS
from .landed_candidates import LANDED_CANDIDATES
from .landed_engine import LANDED_ENGINE, shipped_time_ctx
from .store import LANDED_PSF_BAND, TransactionStore

_OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "results_landed.json")

# crude GCB flag (roadmap L1): detached AND plot >= 15,070 sqft AND a GCBA-bearing
# prime district. Case-tier work, not a model input — a SLICE to watch error mass on.
GCB_MIN_SQFT = 15070
GCB_DISTRICTS = {"10", "11", "20", "21", "23"}


def _is_gcb(r) -> bool:
    return (r.get("property_type") == "Detached"
            and (r.get("area_sqft") or 0) >= GCB_MIN_SQFT
            and str(r.get("district")) in GCB_DISTRICTS)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--max", type=int, default=None, help="cap #subjects (quick run)")
    ap.add_argument("--sample", type=int, default=None, help="random subject sample (seed 42)")
    ap.add_argument("--min-ym", default="2023-01",
                    help="earliest subject month (>=18mo history; YYYY-MM)")
    ap.add_argument("--max-ym", default=None)
    ap.add_argument("--lag-days", type=int, default=56, help="caveat visibility buffer")
    ap.add_argument("--slice", default=None, help="single dimension to break down by")
    ap.add_argument("--slices", action="store_true", help="standard GL1 slice panel")
    ap.add_argument("--dump", default=None, help="save all per-subject rows to JSON path")
    ap.add_argument("--method", default="LB2_street_district_pooled")
    ap.add_argument("--no-ltrend", action="store_true",
                    help="ablation: drop the shipped L2b local-trend bridge (EXP-0017)")
    args = ap.parse_args()

    store = (TransactionStore.load().is_pure_landed().exclude_bulk()
             .psf_band(*LANDED_PSF_BAND))
    subjects = store.subjects(kind="pure-landed", sale_types=("Resale",),
                              min_ym=args.min_ym, max_ym=args.max_ym)
    if args.sample and args.sample < len(subjects):
        import random
        subjects = random.Random(42).sample(subjects, args.sample)
    print(f"store: {len(store):,} pure-landed caveats (cleaned); subjects: "
          f"{len(subjects):,} resale (>= {args.min_ym})")
    if not subjects:
        print("no subjects — is the store populated and the date window sane?")
        return

    # DEFAULT = the SHIPPED configuration (EXP-0017 lt_tail). The harness must backtest
    # what production runs — a default that silently diverges from `value_landed` is the
    # EXP-0015 "shipped point was not the backtested point" failure at the harness level.
    hook = (None if args.no_ltrend else
            (lambda view, ctx: shipped_time_ctx(view.txs, ctx["asof_ym"])))
    res = walk_forward(store, subjects,
                       {**LANDED_BENCHMARKS, **LANDED_CANDIDATES, **LANDED_ENGINE},
                       lag_days=args.lag_days, max_subjects=args.max, ctx_hook=hook)
    print("\n=== landed benchmark leaderboard (sorted by median APE) ===")
    print(res.table())

    def _liq(r):
        n = r["n_comps"]
        return "0" if n == 0 else "1-2" if n <= 2 else "3-5" if n <= 5 \
            else "6-15" if n <= 15 else "16+"

    def _size(r):
        a = r["area_sqft"]
        return "<1.5k" if a < 1500 else "1.5-3k" if a < 3000 else "3-5k" \
            if a < 5000 else "5-8k" if a < 8000 else "8-15k" if a < 15000 else "15k+"

    def _quantum(r):
        p = r["actual"]
        return "<2M" if p < 2e6 else "2-3M" if p < 3e6 else "3-5M" \
            if p < 5e6 else "5-8M" if p < 8e6 else ">8M"

    def _show(title, d):
        # The SIGN TEST belongs in every slice. A regime slice that reports only APE hid a
        # +-15pp swing in directional bias for two whole review rounds: median APE was flat
        # (10.1-10.8%) across regimes while the engine ran ~50% in stable periods and ~66%
        # low in the accelerating one. Flat APE is not flat bias.
        print(f"\n=== {args.method} by {title} ===")
        for b, m in d.items():
            print(f"  {b:<10} n={m.get('n', 0):<6} medAPE={m.get('median_ape', ''):<8}"
                  f"p90={m.get('p90_ape', ''):<8} >10%={m.get('pct_over_10', ''):<8}"
                  f"sign={m.get('pct_actual_above', ''):<8}"
                  f"medSigned={m.get('median_signed', ''):<9}"
                  f"cover={m.get('coverage_rate', '')}")

    if args.slices:
        _show("type", res.slice("property_type", args.method))
        _show("tenure", res.slice("tenure_type", args.method))
        _show("segment", res.slice("market_segment", args.method))
        _show("land size", res.slice_by(_size, args.method))
        _show("street-liquidity(#comps)", res.slice_by(_liq, args.method))
        # half-years: the directional bias moves within a year (2025H1 vs H2), so an
        # annual bucket averages the very signal the sign test is there to expose
        _show("regime(half-year)", res.slice_by(
            lambda r: f"{r['contract_ym'][:4]}H{1 if int(r['contract_ym'][5:7]) <= 6 else 2}",
            args.method))
        _show("quantum", res.slice_by(_quantum, args.method))
        _show("GCB flag (crude)", res.slice_by(_is_gcb, args.method))

    elif args.slice:
        _show(args.slice, res.slice(args.slice, args.method))

    with open(_OUT, "w", encoding="utf-8", newline="\n") as f:
        json.dump({"summary": res.summary(), "n_subjects": len(subjects),
                   "lag_days": args.lag_days, "min_ym": args.min_ym}, f,
                  ensure_ascii=False, indent=1)
    print(f"\n-> {_OUT}")

    if args.dump:
        keep = ("method", "street", "market_segment", "district", "property_type",
                "tenure_type", "contract_ym", "area_sqft", "n_comps",
                "actual", "pred", "lo", "hi")
        with open(args.dump, "w", encoding="utf-8", newline="\n") as f:
            json.dump([{k: r.get(k) for k in keep} for r in res.rows], f,
                      ensure_ascii=False)
        print(f"-> dumped {len(res.rows)} rows to {args.dump}")


if __name__ == "__main__":
    main()
