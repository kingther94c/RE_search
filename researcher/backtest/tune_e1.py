"""Offline calibration for E1 (researcher/backtest/ensemble_learned.py).

Fits the C1<->A1 point-estimate blend weight per evidence-state bucket on subjects
from 2023 ONLY (TRAIN), then reports how those FROZEN weights generalise on subjects
from 2024-01 onward (TEST) that were never used to pick a weight. Run:

    PYTHONIOENCODING=utf-8 python -m researcher.backtest.tune_e1

This is a one-off dev tool, NOT part of the scored leaderboard. The registered E1
method (ensemble_learned.ensemble_learned) only ever uses the frozen `_WEIGHTS`
table this script prints, plus market/ctx at valuation time -- it never reads a
subject's own psf/price/id. Reading `subj["psf"]` here is the entire point of
calibration (estimating a handful of blend weights from REALISED history), exactly
as avm.py's OLS reads `t["psf"]` on its as-of TRAIN rows to fit beta. The leakage
rule (never let a subject see its own answer) is enforced at evaluation time inside
ensemble_learned(), not in this calibration script.

Evidence-state bucketing reuses run.py's own liquidity bucket edges (n_comps 1-2 /
3-5 / 6-15 / 16+) crossed with a recency flag (newest same-project comp <=12mo old
vs older/absent) -- exactly the two signals the task calls out: "many/recent" should
lean C1, "thin/absent" should lean A1. See fit() for why this is a 2-parameter-family
(per-bucket w(recent) + one shared stale_delta) rather than 8 independently
grid-searched cells: stale rows are too rare per bucket (2-66 of them) to trust an
independent grid search per cell without freezing noise (an early prototype without
the shared delta produced a NON-monotone table on this exact data).
"""
from __future__ import annotations

import random
from collections import defaultdict
from statistics import median

from .avm import avm_hedonic
from .candidates import c1_grid_adapted
from .harness import _prev_ym
from .index import PriceIndex
from .market import MarketView
from .metrics import ape
from .store import TransactionStore, month_end, months_between

RECENCY_EDGE = 12                                    # months
W_GRID = [round(0.05 * i, 2) for i in range(21)]     # 0.00 .. 1.00 step 0.05
SAMPLE_CAP = 4000                                    # tractable pure-python cap, seed 42


def n_bucket(n: int) -> str:
    return "1-2" if n <= 2 else "3-5" if n <= 5 else "6-15" if n <= 15 else "16+"


def recency_bucket(months) -> str:
    return "recent" if months is not None and months <= RECENCY_EDGE else "stale"


def _collect(store, subjects, index, *, lag_days=56, index_pub_lag_days=35):
    """One (c1_psf, avm_psf, actual_psf, evidence-state) row per subject where BOTH
    C1 and A1 produced an estimate -- the only population the blend weight governs;
    if either declines, ensemble_learned() falls back exactly like E0 does, and no
    weight is needed."""
    by_month: dict[str, list[dict]] = defaultdict(list)
    for s in subjects:
        by_month[_prev_ym(s["contract_ym"])].append(s)
    out = []
    for asof_ym, group in by_month.items():
        t = month_end(asof_ym)
        view = store.as_of(t, lag_days)
        market = MarketView(view.txs, asof_ym)
        asof_q = index.as_of_quarter(t, index_pub_lag_days)
        ctx = {"asof_ym": asof_ym, "asof_date": t, "index": index, "asof_q": asof_q}
        for subj in group:
            c1 = c1_grid_adapted(subj, market, ctx)
            avm = avm_hedonic(subj, market, ctx)
            if c1 is None or avm is None:
                continue
            rows = market.same_project(subj["project"])
            recency = months_between(rows[0]["contract_ym"], ctx["asof_ym"]) if rows else None
            out.append({
                "c1_psf": c1["psf"], "avm_psf": avm["psf"], "actual_psf": subj["psf"],
                "n": c1["n_comps"], "nb": n_bucket(c1["n_comps"]),
                "rb": recency_bucket(recency),
            })
    return out


def _best_weight(rows) -> tuple[float, float]:
    """Grid-search the w that minimises median APE of w*c1+(1-w)*avm vs actual."""
    best_w, best_err = 1.0, float("inf")
    for w in W_GRID:
        errs = [ape(w * r["c1_psf"] + (1 - w) * r["avm_psf"], r["actual_psf"]) for r in rows]
        m = median(errs)
        if m < best_err:
            best_err, best_w = m, w
    return best_w, best_err


_NB_ORDER = ("1-2", "3-5", "6-15", "16+")
DELTA_GRID = [round(0.05 * i, 2) for i in range(9)]     # 0.00 .. 0.40 step 0.05
MIN_W = 0.50                                            # never blend BELOW 50/50


def fit(rows_train):
    """Two-parameter-family table, not 8 independently grid-searched cells:

      1. `nb_weight[nb]` -- the C1 share for the (dominant) "recent" evidence
         state, grid-searched per n_comps bucket on ALL of that bucket's TRAIN
         rows (recent rows are ~98% of the population, so this is already
         essentially the recent-state weight).
      2. A single global `stale_delta` -- how much LESS to trust C1 when the
         newest same-project comp is >12mo old -- grid-searched once on the
         POOLED stale rows across every bucket (stale rows are rare: pulling 4
         independent per-bucket stale weights from as few as 2-66 rows each is
         exactly the kind of thin-slice overfit the task warns against; one
         shared discount uses all the stale evidence there is and is monotone
         by construction: w(stale) = w(recent) - delta <= w(recent) always).

    This bakes in the task's requirement directly (lean to C1 as comps get more
    abundant AND more recent) instead of hoping an 8-cell independent grid
    search discovers it -- which it did NOT do cleanly here (see NOTE below)."""
    by_nb: dict[str, list[dict]] = defaultdict(list)
    for r in rows_train:
        by_nb[r["nb"]].append(r)
    nb_weight = {nb: _best_weight(rs)[0] for nb, rs in by_nb.items()}

    stale_rows = [r for r in rows_train if r["rb"] == "stale"]
    best_delta, best_err = 0.0, float("inf")
    for delta in DELTA_GRID:
        if not stale_rows:
            break
        errs = [ape(max(MIN_W, nb_weight[r["nb"]] - delta) * r["c1_psf"]
                    + (1 - max(MIN_W, nb_weight[r["nb"]] - delta)) * r["avm_psf"],
                    r["actual_psf"]) for r in stale_rows]
        m = median(errs)
        if m < best_err:
            best_err, best_delta = m, delta

    table = {}
    for nb in _NB_ORDER:
        w_recent = nb_weight.get(nb, 0.75)
        table[(nb, "recent")] = w_recent
        table[(nb, "stale")] = max(MIN_W, round(w_recent - best_delta, 2))
    return table, nb_weight, by_nb, stale_rows, best_delta


def _apply(rows, table, nb_weight, default=0.75):
    errs = []
    for r in rows:
        w = table.get((r["nb"], r["rb"]), nb_weight.get(r["nb"], default))
        errs.append(ape(w * r["c1_psf"] + (1 - w) * r["avm_psf"], r["actual_psf"]))
    return errs


def _e0_apply(rows):
    """E0's hand-set formula on the SAME paired rows, for a direct reference."""
    errs = []
    for r in rows:
        w = 0.5 + 0.5 * min(r["n"], 10) / 10
        errs.append(ape(w * r["c1_psf"] + (1 - w) * r["avm_psf"], r["actual_psf"]))
    return errs


def main() -> None:
    store = TransactionStore.load().exclude_bulk().psf_band(500, 6500)
    index = PriceIndex.load()

    subs_train = store.subjects(kind="condo", sale_types=("Resale",),
                                min_ym="2023-01", max_ym="2023-12")
    subs_test = store.subjects(kind="condo", sale_types=("Resale",), min_ym="2024-01")
    if len(subs_train) > SAMPLE_CAP:
        subs_train = random.Random(42).sample(subs_train, SAMPLE_CAP)
    if len(subs_test) > SAMPLE_CAP:
        subs_test = random.Random(42).sample(subs_test, SAMPLE_CAP)
    print(f"TRAIN subjects (2023 only):      {len(subs_train):,}")
    print(f"TEST  subjects (2024-01 onward):  {len(subs_test):,}")

    rows_train = _collect(store, subs_train, index)
    rows_test = _collect(store, subs_test, index)
    print(f"TRAIN dual-estimate rows (C1&A1 both answered): {len(rows_train):,}")
    print(f"TEST  dual-estimate rows (C1&A1 both answered): {len(rows_test):,}")

    table, nb_weight, by_nb, stale_rows, best_delta = fit(rows_train)

    print("\n-- w(recent) per n_comps bucket, grid-searched on TRAIN --")
    for nb in _NB_ORDER:
        rs = by_nb.get(nb, [])
        print(f"  {nb:<6} w_c1={nb_weight.get(nb, float('nan')):.2f}  n={len(rs)}")

    print(f"\n-- global stale_delta grid-searched on {len(stale_rows)} pooled stale TRAIN"
          f" rows: {best_delta:.2f} --")
    by_nb_stale = defaultdict(int)
    for r in stale_rows:
        by_nb_stale[r["nb"]] += 1
    for nb in _NB_ORDER:
        print(f"  stale rows in {nb:<6}: {by_nb_stale.get(nb, 0)}")

    print("\n-- final (n_bucket, recency) -> w_c1 table --")
    for cell in sorted(table):
        print(f"  {cell!s:<22} w_c1={table[cell]:.2f}")

    err_train_e1 = _apply(rows_train, table, nb_weight)
    err_test_e1 = _apply(rows_test, table, nb_weight)
    err_train_e0 = _e0_apply(rows_train)
    err_test_e0 = _e0_apply(rows_test)

    def pct_over(errs, t=0.10):
        return sum(1 for e in errs if e > t) / len(errs)

    print("\n-- median APE on the dual-estimate (C1&A1-answered) population --")
    print(f"  TRAIN (2023)   E1(learned)={median(err_train_e1):.4f}  "
          f"E0(hand-set)={median(err_train_e0):.4f}  n={len(err_train_e1)}")
    print(f"  TEST  (2024+)  E1(learned)={median(err_test_e1):.4f}  "
          f"E0(hand-set)={median(err_test_e0):.4f}  n={len(err_test_e1)}")
    print(f"  TRAIN pct>10%  E1={pct_over(err_train_e1):.4f}  E0={pct_over(err_train_e0):.4f}")
    print(f"  TEST  pct>10%  E1={pct_over(err_test_e1):.4f}  E0={pct_over(err_test_e0):.4f}")
    print("\n(train-vs-test gap should be small: a big jump would mean the table is")
    print(" overfit to 2023 quirks rather than a real evidence-state pattern.)")

    print("\n-- paste-ready _WEIGHTS table for ensemble_learned.py --")
    print("_WEIGHTS = {")
    for cell in sorted(table):
        print(f"    {cell!r}: {table[cell]:.2f},")
    print("}")


if __name__ == "__main__":
    main()
