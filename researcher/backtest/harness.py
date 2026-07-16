"""Walk-forward driver. Value each subject as of the month BEFORE its caveat month,
seeing only caveats visible by then, and score against what it actually sold for.

Valuation date choice (deliberate, leakage-free): a subject caveated in month M is
valued as of the END of month M-1. That excludes the subject's own month entirely, so
no same-month look-ahead is even possible; combined with the caveat-lag buffer in
store.as_of, the valuer's information set is strictly historical.

Subjects are grouped by valuation month so the (expensive) as-of filter runs once per
distinct month rather than once per subject.
"""
from __future__ import annotations

from collections import defaultdict

from . import metrics
from .index import PriceIndex
from .market import MarketView
from .store import TransactionStore, month_end

# rich per-row fields kept for error-slicing (mandate's 12 dimensions).
# street/type_of_area joined for the L-track: landed slices key on street liquidity.
_KEEP = ("id", "project", "street", "market_segment", "district", "property_type",
         "type_of_area", "tenure_type", "area_sqft", "floor_lo", "contract_ym")


def _prev_ym(ym: str) -> str:
    y, m = (int(x) for x in ym.split("-"))
    return f"{y - 1}-12" if m == 1 else f"{y}-{m - 1:02d}"


class WalkForwardResult:
    def __init__(self, rows: list[dict]):
        self.rows = rows

    def by_method(self) -> dict[str, list[dict]]:
        out: dict[str, list[dict]] = defaultdict(list)
        for r in self.rows:
            out[r["method"]].append(r)
        return out

    def summary(self) -> dict[str, dict]:
        return metrics.compare(self.by_method())

    def slice(self, dim: str, method: str) -> dict[str, dict]:
        """Metrics for one method grouped by a categorical subject dimension."""
        return self.slice_by(lambda r: str(r.get(dim, "?")), method)

    def slice_by(self, keyfunc, method: str) -> dict[str, dict]:
        """Metrics for one method grouped by an arbitrary bucketing function of the row."""
        buckets: dict[str, list[dict]] = defaultdict(list)
        for r in self.rows:
            if r["method"] == method:
                buckets[str(keyfunc(r))].append(r)
        return {k: metrics.summarise(v) for k, v in sorted(buckets.items())}

    def table(self) -> str:
        s = self.summary()
        cols = ("n", "coverage_rate", "median_ape", "p90_ape", "pct_over_10",
                "signed_bias", "median_signed", "pct_actual_above", "interval_coverage")
        head = f"{'method':<32}" + "".join(f"{c:>16}" for c in cols)
        lines = [head, "-" * len(head)]
        for m, mv in sorted(s.items(), key=lambda kv: kv[1].get("median_ape", 9)):
            lines.append(f"{m:<32}" + "".join(
                f"{mv.get(c, ''):>16}" if not isinstance(mv.get(c), float)
                else f"{mv[c]:>16.4f}" for c in cols))
        return "\n".join(lines)


def walk_forward(store: TransactionStore, subjects: list[dict], methods: dict,
                 *, lag_days: int = 56, index: PriceIndex | None = None,
                 index_pub_lag_days: int = 35,
                 max_subjects: int | None = None) -> WalkForwardResult:
    index = index or PriceIndex.load()
    if max_subjects:
        subjects = subjects[:max_subjects]

    by_month: dict[str, list[dict]] = defaultdict(list)
    for s in subjects:
        by_month[_prev_ym(s["contract_ym"])].append(s)

    rows: list[dict] = []
    for asof_ym, group in by_month.items():
        t = month_end(asof_ym)
        view = store.as_of(t, lag_days)
        # The subject caveats are in month M; `view` is as-of end of M-1, so the subject's
        # own row is already excluded — no per-subject filtering needed (that O(n) copy was
        # the 61k-subject bottleneck). test_as_of_excludes_future guards this.
        market = MarketView(view.txs, asof_ym)
        asof_q = index.as_of_quarter(t, index_pub_lag_days)
        ctx = {"asof_ym": asof_ym, "asof_date": t, "index": index, "asof_q": asof_q}
        for subj in group:
            base = {k: subj.get(k) for k in _KEEP}
            base["actual"] = subj["price"]
            base["actual_psf"] = subj["psf"]
            for name, fn in methods.items():
                est = fn(subj, market, ctx)
                rows.append({**base, "method": name,
                             "pred": est["price"] if est else None,
                             "pred_psf": est["psf"] if est else None,
                             "lo": est["low"] if est else None,
                             "hi": est["high"] if est else None,
                             "n_comps": est["n_comps"] if est else 0,
                             "note": est["note"] if est else "declined"})
    return WalkForwardResult(rows)
