"""L2b: fitted LOCAL landed trend from visible caveats — the observation-based
time signal the graveyard demanded ("do not resurrect [index momentum] unless you
have a fitted LOCAL trend validated by the regime sign test", GY-0003).

What it is: a month-granular ln-level curve for the landed market, fitted AS-OF from
the caveats the valuer can already see, via two-way fixed effects

    ln(land_psf)_i = a_(street,type)(i) + b_month(i) + e_i

so street/type mix is absorbed by the group effects and b_* is a pure time curve.
It reaches the newest VISIBLE caveat month — typically ~2 months fresher than the
last PUBLISHED PPI quarter (whose midpoint is 1.5-4.5 months stale at the valuation
date) — and it never extrapolates: a requested month beyond the fitted range clamps
to the newest fitted month. Forecasting is exactly what GY-0003 buried.

Fitting is alternating demeaning (pure stdlib, converges in a few dozen sweeps on
~11k rows); the month curve is smoothed with a centered 3-month median so a thin or
partial terminal month (live mode sees the current month mid-flight) cannot swing
the adjustment on its own.
"""
from __future__ import annotations

from collections import defaultdict
from math import exp, log
from statistics import median

from .store import months_between

WINDOW_MO = 72          # fit window (store is ~61mo deep — effectively "all visible")
MIN_GROUP = 2           # singleton (street,type) groups identify nothing about time
SMOOTH_MO = 3           # centered median window on the month curve
MIN_TERMINAL_N = 5      # a thinner LIVE partial terminal month is dropped from the fit:
#   the walk-forward only ever sees COMPLETE months (visibility = month-end + lag), so a
#   2-print partial month steering the bridge is outside anything the backtest validated
#   (L2b hostile review MINOR-7). Never triggers in the backtest (min complete-month n=90).
MAX_SWEEPS = 60
TOL = 1e-7


class LocalTrend:
    """Fitted month ln-levels. Only RATIOS are meaningful (level is pinned to mean 0)."""

    def __init__(self, levels: dict[str, float], n_by_month: dict[str, int]):
        self.levels = levels                    # ym -> smoothed ln level
        self.n_by_month = n_by_month
        self.months = sorted(levels)
        self.last_ym = self.months[-1] if self.months else None

    def _lvl(self, ym: str) -> float | None:
        if not self.months:
            return None
        if ym in self.levels:
            return self.levels[ym]
        # clamp into the fitted range — NEVER extrapolate beyond an observation
        if ym > self.months[-1]:
            return self.levels[self.months[-1]]
        if ym < self.months[0]:
            return self.levels[self.months[0]]
        earlier = [m for m in self.months if m <= ym]
        return self.levels[earlier[-1]]

    def factor(self, from_ym: str, to_ym: str) -> float:
        a, b = self._lvl(from_ym), self._lvl(to_ym)
        if a is None or b is None:
            return 1.0
        return exp(b - a)


def fit_landed_trend(txs, asof_ym: str, window_mo: int = WINDOW_MO) -> LocalTrend:
    """Fit on the rows of an AS-OF view (the caller guarantees visibility — inside the
    harness this is the same firewalled MarketView the methods see)."""
    rows = []
    for t in txs:
        ym = t["contract_ym"]
        if not (0 <= months_between(ym, asof_ym) < window_mo):
            continue
        rows.append(((t["street"], t["property_type"]), ym, log(t["psf"])))
    by_group = defaultdict(list)
    for g, ym, y in rows:
        by_group[g].append((ym, y))
    rows = [(g, ym, y) for g, pts in by_group.items() if len(pts) >= MIN_GROUP
            for ym, y in pts]
    # ONE-SHOT drop of a too-thin TERMINAL month (live partial-month guard — see
    # MIN_TERMINAL_N). Only the terminal month can be mid-flight; earlier thin months are
    # legitimate data in a thin market and must never be stripped.
    if rows:
        counts = defaultdict(int)
        for _, ym, _ in rows:
            counts[ym] += 1
        last = max(counts)
        if counts[last] < MIN_TERMINAL_N and len(counts) > 1:
            rows = [r for r in rows if r[1] != last]
    if not rows:
        return LocalTrend({}, {})

    a = defaultdict(float)      # group effects
    b = defaultdict(float)      # month effects
    g_rows = defaultdict(list)
    m_rows = defaultdict(list)
    for i, (g, ym, y) in enumerate(rows):
        g_rows[g].append(i)
        m_rows[ym].append(i)
    ys = [y for _, _, y in rows]

    for _ in range(MAX_SWEEPS):
        delta = 0.0
        for g, idxs in g_rows.items():
            new = sum(ys[i] - b[rows[i][1]] for i in idxs) / len(idxs)
            delta = max(delta, abs(new - a[g]))
            a[g] = new
        for ym, idxs in m_rows.items():
            new = sum(ys[i] - a[rows[i][0]] for i in idxs) / len(idxs)
            delta = max(delta, abs(new - b[ym]))
            b[ym] = new
        # pin the level: mean month effect = 0 (only ratios are used downstream)
        shift = sum(b.values()) / len(b)
        for ym in b:
            b[ym] -= shift
        for g in a:
            a[g] += shift
        if delta < TOL:
            break

    months = sorted(b)
    half = SMOOTH_MO // 2
    smoothed = {}
    for i, ym in enumerate(months):
        lo, hi = max(0, i - half), min(len(months), i + half + 1)
        smoothed[ym] = median(b[m] for m in months[lo:hi])
    return LocalTrend(smoothed, {ym: len(m_rows[ym]) for ym in months})
