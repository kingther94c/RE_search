"""A transparent comparable-adjustment valuation engine.

Method (standard sales-comparison appraisal, codified):
  1. For each comparable, adjust its transacted PSF to the subject by:
       - time      : normalise to the as-of date at an annual trend
       - floor     : per-floor premium for the level difference
       - size      : quantum effect (smaller units carry higher PSF), psf ∝ size^e
       - unit type : compact-3BR layout discount vs efficient small units
  2. Weight each comparable by similarity to the subject (size / floor / recency /
     same-bedroom), so the closest comps dominate.
  3. Optionally blend in a *same-line anchor* — the subject's own last sale,
     time-adjusted — which is the single most like-for-like data point.
  4. Reconcile to a point PSF + price and a defensible low/high range.

Generalises to any unit: pass a Subject, a list of Comp, and Params.
Pure stdlib so it can ship as the backing of a reusable skill.
"""
from __future__ import annotations

import math
import statistics
from dataclasses import dataclass, field
from datetime import date


def _d(s: str) -> date:
    y, m, dd = (s.split("-") + ["01", "01"])[:3]
    return date(int(y), int(m), int(dd))


def _years_between(a: date, b: date) -> float:
    return (b - a).days / 365.25


@dataclass
class Subject:
    name: str
    size_sqft: float
    floor: int
    bedrooms: int
    tenure: str = "Freehold"


@dataclass
class Comp:
    label: str
    date: str
    floor: int
    bedrooms: int
    size_sqft: float
    psf: float
    price: float | None = None


@dataclass
class Params:
    asof: str = "2026-06-30"
    time_trend_pa: float = 0.018       # annual PSF appreciation for this segment
    floor_premium_pp: float = 0.003    # +0.3% PSF per floor higher
    size_elasticity: float = -0.08     # psf ∝ size^e  (quantum effect)
    compact3br_discount: float = 0.03  # layout discount for a <=800 sqft 3BR
    compact3br_max_sqft: float = 800


def _is_compact3(beds: int, sqft: float, p: Params) -> bool:
    return beds >= 3 and sqft <= p.compact3br_max_sqft


@dataclass
class AdjustedComp:
    label: str
    raw_psf: float
    time_adj: float
    floor_adj: float
    size_adj: float
    type_adj: float
    adj_psf: float
    weight: float


def adjust(comp: Comp, subject: Subject, p: Params) -> AdjustedComp:
    asof = _d(p.asof)
    # 1) time: bring comp PSF forward to as-of date
    yrs = _years_between(_d(comp.date), asof)
    time_factor = (1 + p.time_trend_pa) ** yrs
    # 2) floor: subject higher than comp -> add premium
    floor_factor = (1 + p.floor_premium_pp) ** (subject.floor - comp.floor)
    # 3) size/quantum: psf scales with size^elasticity
    size_factor = (subject.size_sqft / comp.size_sqft) ** p.size_elasticity
    # 4) unit-type: apply/remove the compact-3BR discount so comp matches subject
    subj_disc = p.compact3br_discount if _is_compact3(subject.bedrooms, subject.size_sqft, p) else 0.0
    comp_disc = p.compact3br_discount if _is_compact3(comp.bedrooms, comp.size_sqft, p) else 0.0
    type_factor = (1 - subj_disc) / (1 - comp_disc)

    adj_psf = comp.psf * time_factor * floor_factor * size_factor * type_factor

    # similarity weight: closer in size / floor / time / same-bed = heavier
    size_pen = abs(math.log(subject.size_sqft / comp.size_sqft)) * 3.0
    floor_pen = abs(subject.floor - comp.floor) / 25.0
    time_pen = abs(yrs) / 2.0
    bed_pen = 0.0 if comp.bedrooms == subject.bedrooms else 0.6
    weight = 1.0 / (1.0 + size_pen + floor_pen + time_pen + bed_pen)

    return AdjustedComp(
        label=comp.label,
        raw_psf=comp.psf,
        time_adj=time_factor,
        floor_adj=floor_factor,
        size_adj=size_factor,
        type_adj=type_factor,
        adj_psf=adj_psf,
        weight=weight,
    )


@dataclass
class Valuation:
    subject: Subject
    estimate_psf: float
    estimate_price: float
    low_psf: float
    high_psf: float
    low_price: float
    high_price: float
    grid: list[AdjustedComp]
    anchor_psf: float | None
    method_notes: list[str] = field(default_factory=list)

    @property
    def estimate_price_rounded(self) -> int:
        return int(round(self.estimate_price, -3))


def value(
    subject: Subject,
    comps: list[Comp],
    p: Params | None = None,
    same_line_anchor: Comp | None = None,
    anchor_weight: float = 2.0,
) -> Valuation:
    p = p or Params()
    grid = [adjust(c, subject, p) for c in comps]

    rows = list(grid)
    anchor_psf = None
    if same_line_anchor is not None:
        a = adjust(same_line_anchor, subject, p)
        a.weight = anchor_weight  # the most like-for-like point gets extra pull
        anchor_psf = a.adj_psf
        rows.append(a)

    total_w = sum(r.weight for r in rows)
    est_psf = sum(r.adj_psf * r.weight for r in rows) / total_w

    # range: weighted-IQR-ish — use the spread of adjusted comps
    adj = sorted(r.adj_psf for r in rows)
    low_psf = statistics.quantiles(adj, n=4)[0] if len(adj) >= 4 else min(adj)
    high_psf = statistics.quantiles(adj, n=4)[2] if len(adj) >= 4 else max(adj)
    # keep the point estimate inside the band
    low_psf = min(low_psf, est_psf * 0.985)
    high_psf = max(high_psf, est_psf * 1.015)

    return Valuation(
        subject=subject,
        estimate_psf=est_psf,
        estimate_price=est_psf * subject.size_sqft,
        low_psf=low_psf,
        high_psf=high_psf,
        low_price=low_psf * subject.size_sqft,
        high_price=high_psf * subject.size_sqft,
        grid=grid,
        anchor_psf=anchor_psf,
    )


def format_grid(v: Valuation) -> str:
    lines = [
        f"{'comp':<26}{'raw':>7}{'×time':>7}{'×flr':>7}{'×size':>7}{'×type':>7}{'adj psf':>9}{'wt':>6}",
        "-" * 76,
    ]
    for r in v.grid:
        lines.append(
            f"{r.label:<26}{r.raw_psf:>7.0f}{r.time_adj:>7.3f}{r.floor_adj:>7.3f}"
            f"{r.size_adj:>7.3f}{r.type_adj:>7.3f}{r.adj_psf:>9.0f}{r.weight:>6.2f}"
        )
    return "\n".join(lines)
