"""Partial-pooling / shrinkage anchor (A2) — independent of A1's hedonic regression.

Classic empirical-Bayes hierarchical shrinkage: estimate the subject's psf as a
weighted blend of three levels, each time-adjusted to the as-of quarter via
ctx.index, pooling upward as the finer level thins out:

    project mean  <-shrunk toward-  segment mean  <-shrunk toward-  broad condo mean

Shrinkage weight w = n / (n + k): the fewer same-project (or same-segment) prints
the market has seen as-of the valuation date, the more weight falls on the coarser,
more populated level above it. With ZERO same-project comps the project term drops
out entirely and the estimate is just the (already-pooled) segment anchor -- so,
unlike C1, A2 never declines for a thin/new project: coverage ~100%.

This is deliberately simpler than A1 (no regression, no floor/size/lease features):
it tests a different hypothesis than the hedonic anchor -- does POOLING same-project
psf toward a market prior, rather than REGRESSING on hedonic attributes, make a good
anchor for thin-comp subjects? A2 and A1 are independent candidates for a later
ensemble to choose between (or blend), not a replacement for either.

Leakage discipline (same firewall as avm.py):
  - every input comes from market.same_project / market.segment_recent / market.condo(),
    all as-of filtered by the harness;
  - every comp psf is time-adjusted with ctx.index.factor(comp_ym, ctx.asof_q, ...) --
    never the subject's own (future) contract_ym;
  - the subject's own psf/price/id are never read -- only its project/segment/area,
    and the subject is evaluated at the as-of time coordinate (comps are moved to
    ctx.asof_q; the subject itself contributes no comp row of its own).
"""
from __future__ import annotations

from .store import months_between

K_PROJECT = 1.0          # shrinkage k at the project level. Tuned by sweeping k in
                         # {0, 0.1, 0.25, 0.5, 0.75, 1, 1.5, 2, 3, 4, 5, 8, 12, 20} on the
                         # 4,000-subject sample (see researcher/backtest/avm_pooled.py notes
                         # in the registry write-up): error is MONOTONICALLY increasing in k
                         # over the whole grid (median APE 5.34% @ k=0 -> 5.46% @ k=1 -> 5.60%
                         # @ k=2 -> 6.79% @ k=12), i.e. there is no interior minimum -- any
                         # same-project print, even n=1, out-predicts shrinking toward the
                         # segment mean. k=1 (not the corner-optimal k=0) is chosen anyway: at
                         # k=0 the formula degenerates to a plain project mean with NO pooling
                         # for n>=1 (defeats the point of a shrinkage anchor and re-derives
                         # B2/B3 in a fancier hat); k=1 keeps genuine partial pooling (w=0.5 at
                         # n=1, 0.75 at n=3) for a median-APE cost of only +0.12pp versus the
                         # corner optimum -- cheap insurance against a single unrepresentative
                         # print, for a documented, small, honest price.
K_SEGMENT = 50.0         # segment pools are large (1000s); this k keeps w_seg ~= 1 in practice,
                         # only mattering in the (near-never-seen) case of a near-empty segment
SEGMENT_WINDOW_MONTHS = 24
BROAD_WINDOW_MONTHS = 24


def _time_adj_mean(rows: list[dict], asof_q, index) -> tuple[int, float | None]:
    """(n, mean time-adjusted psf) for a list of comps, or (0, None) if empty."""
    if not rows:
        return 0, None
    if index is not None and asof_q:
        vals = [r["psf"] * index.factor(r["contract_ym"], asof_q, "non-landed") for r in rows]
    else:
        vals = [r["psf"] for r in rows]
    return len(vals), sum(vals) / len(vals)


def _broad_stats(market, ctx) -> tuple[int, float | None]:
    """Whole as-of condo-pool mean psf, time-adjusted; cached once per valuation month."""
    key = ("a2_broad", BROAD_WINDOW_MONTHS)
    if key not in market.cache:
        pool = [t for t in market.condo()
                if 0 <= months_between(t["contract_ym"], ctx["asof_ym"]) < BROAD_WINDOW_MONTHS]
        market.cache[key] = _time_adj_mean(pool, ctx["asof_q"], ctx["index"])
    return market.cache[key]


def _segment_anchor(market, ctx, seg: str | None) -> tuple[int, float | None]:
    """Segment mean shrunk toward the broad mean; cached once per (month, segment)."""
    key = ("a2_seg", seg)
    if key not in market.cache:
        n_broad, mean_broad = _broad_stats(market, ctx)
        pool = market.segment_recent(seg, SEGMENT_WINDOW_MONTHS) if seg else []
        n_seg, mean_seg = _time_adj_mean(pool, ctx["asof_q"], ctx["index"])
        if n_seg == 0:
            anchor = mean_broad
        elif mean_broad is None:
            anchor = mean_seg
        else:
            w = n_seg / (n_seg + K_SEGMENT)
            anchor = w * mean_seg + (1 - w) * mean_broad
        market.cache[key] = (n_seg, anchor)
    return market.cache[key]


def avm_pooled(subject, market, ctx):
    """A2: project mean, shrunk toward the segment mean, shrunk toward the broad condo
    mean. w = n_project / (n_project + K_PROJECT). Falls back to the segment anchor with
    no same-project comp at all, so this anchor answers on (almost) every subject."""
    seg = subject.get("market_segment")
    n_seg, seg_anchor = _segment_anchor(market, ctx, seg)
    if seg_anchor is None:
        return None   # only if the as-of market has literally zero condo history

    proj_rows = market.same_project(subject["project"])
    n_proj, proj_mean = _time_adj_mean(proj_rows, ctx["asof_q"], ctx["index"])

    if n_proj == 0:
        psf = seg_anchor
        note = f"no same-project comp -> segment anchor (n_seg={n_seg})"
    else:
        w = n_proj / (n_proj + K_PROJECT)
        psf = w * proj_mean + (1 - w) * seg_anchor
        note = f"pooled n_proj={n_proj} w={w:.2f} seg_anchor={seg_anchor:.0f}"

    if not (300 <= psf <= 7000):
        return None
    area = subject["area_sqft"]
    # informal band, tightening as project evidence accrues (0 comps -> +/-20%,
    # 20+ comps -> +/-12%); not conformal -- that calibration is a later R3 step.
    # Width picked by a small sweep against interval_coverage (0.12-0.06 half-width gave
    # only 58% coverage -- far too tight; 0.20-0.08 gives 85%, comfortably past the 80%
    # target E0 uses as its bar, at a still-modest ~27% relative width).
    half = 0.20 - 0.08 * min(n_proj, 20) / 20
    lo = round(psf * (1 - half) * area, 0)
    hi = round(psf * (1 + half) * area, 0)
    return {"method": "A2_avm_pooled", "psf": round(psf, 1), "price": round(psf * area, 0),
            "low": lo, "high": hi, "n_comps": n_proj, "note": note}


ANCHORS_POOLED = {"A2_avm_pooled": avm_pooled}
