"""Production condo valuation — value ONE unit with engine v2 (the R5 skill's engine room).

    from researcher.engine.value_unit import value, SubjectSpec
    v = value(SubjectSpec(project="TREASURE AT TAMPINES", area_sqft=936, floor=12))

Wraps the VALIDATED engine (EXP-0006: C1 point + anchor fallback + conformal band) with:
  - inference of the project's static attributes (segment / district / coords / tenure) from
    its URA caveats, so the caller only supplies unit-specific facts;
  - a confidence score tied to the empirical error curve (same-project comp depth);
  - the independent anchor reads (A1/A2/A3) surfaced for transparency;
  - buyer and seller price guidance DERIVED FROM — and kept separate from — fair value.

Fair value = engine v2 point. The range = the conformal band, which is the empirical
spread within which ~82% of comparable transactions actually printed (EXP-0006) — so buyer
"attractive"/"walk-away" and seller "ask"/"quick-sale" are read off that band, not invented.
"""
from __future__ import annotations

import datetime as _dt
import math as _math
from dataclasses import dataclass
from statistics import median

from researcher.backtest.avm import avm_hedonic
from researcher.backtest.avm_knn import avm_knn
from researcher.backtest.avm_pooled import avm_pooled
from researcher.backtest.candidates import c1_grid_adapted
from .engine_v2 import engine_v2
from researcher.backtest.index import PriceIndex
from researcher.backtest.market import MarketView
from researcher.backtest.store import TransactionStore, months_between


@dataclass
class SubjectSpec:
    project: str
    area_sqft: float
    floor: int | None = None
    asof: str | None = None          # 'YYYY-MM-DD'; defaults to today
    lease_start: int | None = None   # optional override


def _infer(spec, store) -> dict | None:
    """Build a URA-transaction-shaped subject dict, inferring static attrs from the
    project's caveats. Returns None if the project has no caveats to anchor on."""
    rows = store.same_project(spec.project).txs
    if not rows:
        return None
    def _mode(key):
        vals = [r[key] for r in rows if r.get(key)]
        return max(set(vals), key=vals.count) if vals else ""
    xs = [r["x"] for r in rows if r.get("x") is not None]
    ys = [r["y"] for r in rows if r.get("y") is not None]
    ls = [r["lease_start"] for r in rows if r.get("lease_start")]
    fl = spec.floor if spec.floor is not None else 8
    asof = spec.asof or _dt.date.today().isoformat()
    asof_ym = asof[:7]
    return {
        "id": "SUBJECT", "project": spec.project, "street": _mode("street"),
        "market_segment": _mode("market_segment"), "district": _mode("district"),
        "property_type": _mode("property_type") or "Condominium",
        "type_of_area": "Strata", "type_of_sale": "Resale",
        "tenure_type": _mode("tenure_type"),
        "lease_start": spec.lease_start or (median(ls) if ls else None),
        "contract_ym": asof_ym, "area_sqft": float(spec.area_sqft),
        "psf": None, "price": None, "floor_lo": fl, "floor_hi": fl,
        "x": (sum(xs) / len(xs)) if xs else None,
        "y": (sum(ys) / len(ys)) if ys else None, "no_of_units": 1,
    }


def _confidence(n_comps, used_fallback, band_rel, anchor_spread) -> tuple[int, str]:
    # SMOOTH base from same-project comp depth (no 7-vs-8-comp jump): 90 - 45*exp(-n/6)
    # tracks the empirical error curve (n=1 ~52, n=6 ~73, n=12 ~84, n>=30 ~90).
    if used_fallback:
        c, label = 45, "low — no same-project resale; statistical fallback (~5-10% typical error)"
    else:
        c = 90 - 45 * _math.exp(-n_comps / 6)
        label = ("moderate-low — thin same-project evidence" if n_comps <= 2 else
                 "moderate" if n_comps <= 7 else
                 "good — deep same-project evidence" if n_comps <= 19 else
                 "high — very deep same-project evidence")
    # SMOOTH anchor-disagreement penalty (no cliff): 0 below 5% spread, growing to -35.
    if anchor_spread:
        c -= min(35.0, max(0.0, (anchor_spread - 0.05) * 160))
        if anchor_spread > 0.15:
            label += f"; hard case: anchors disagree {anchor_spread*100:.0f}% — corroborate"
        elif anchor_spread > 0.07:                      # label must agree with the docked score
            label += f"; some method divergence ({anchor_spread*100:.0f}%)"
    if band_rel and band_rel > 0.30:
        c = min(c, 65)
        label += "; wide dispersion in this cell"
    c = max(20, round(c))
    return c, label


def _relevant_comps(subject, market, n=8):
    """Same-project prints most SIMILAR to the subject (size proximity, then recency) —
    the evidence a reader should weigh, not just the most recent (which may be a tiny unit)."""
    area = subject["area_sqft"]
    rows = market.same_project(subject["project"])
    ranked = sorted(rows, key=lambda r: (abs(_math.log(r["area_sqft"] / area)),
                                         -months_between("2000-01", r["contract_ym"])))
    return [{"contract_ym": r["contract_ym"], "area_sqft": r["area_sqft"],
             "floor_range": r["floor_range"], "psf": r["psf"], "price": r["price"]}
            for r in ranked[:n]]


def _recent_ref(subject, market, ctx):
    """The freshest same-project print within ~+/-25% size, adjusted to the subject for BOTH
    time (capped) AND size — so the directional check compares apples to apples — the single
    most credible evidence point. On a hard case the model point can drift above it
    (stale-comp inflation); surfacing it keeps the report honest."""
    from researcher.backtest.candidates import SEG_ELASTICITY, DEFAULT_ELASTICITY
    area = subject["area_sqft"]
    sim = [r for r in market.same_project(subject["project"])
           if abs(_math.log(r["area_sqft"] / area)) <= 0.22]
    if not sim:
        return None
    fresh = max(sim, key=lambda r: r["contract_ym"])
    to_q = ctx.get("asof_q")
    tf = ctx["index"].factor(fresh["contract_ym"], to_q, "non-landed") if to_q else 1.0
    tf = min(max(tf, 0.80), 1.25)
    elas = SEG_ELASTICITY.get(subject.get("market_segment"), DEFAULT_ELASTICITY)
    size_adj = (area / fresh["area_sqft"]) ** elas
    return {"contract_ym": fresh["contract_ym"], "area_sqft": fresh["area_sqft"],
            "raw_psf": fresh["psf"], "adj_psf": round(fresh["psf"] * tf * size_adj, 1)}


def value(spec: SubjectSpec, store: TransactionStore | None = None,
          lag_days: int | None = None) -> dict:
    """Value one unit. As-of semantics (deliberate, two modes):

    - LIVE (no `asof`, or asof >= today): the freshly pulled store IS the information set —
      anything lodged is knowable, INCLUDING the current partial month's prints. Only
      future-dated months (data errors) are gated. Applying the backtest's month-end +
      56-day visibility here would discard the freshest ~2 months of prints, exactly the
      evidence that matters most.
    - RECONSTRUCTION (explicit past `asof`): rebuild what was knowable THEN — lag_days
      defaults to 56 (the backtest's caveat-visibility buffer), day-granular.
    Override with lag_days if you know better (e.g. you know when the store was pulled).
    """
    store = store or TransactionStore.load().exclude_bulk().psf_band(500, 6500)
    subject = _infer(spec, store)   # static attrs only (never price) — full store is fine
    if subject is None:
        return {"error": "project_not_found",
                "message": f"No URA caveats for project {spec.project!r}. Provide a known "
                           "project name, or (v1 scope) this unit is out of scope — escalate "
                           "to an Investment-Suite comp pull."}
    today = _dt.date.today()
    asof = spec.asof or today.isoformat()
    t = _dt.date.fromisoformat(asof)
    live = t >= today
    if lag_days is None:
        lag_days = 0 if live else 56
    if live and lag_days == 0:
        # The pulled store IS the info set. as_of's month-END convention (a backtest
        # leakage guard) would hide the current partial month's prints — the freshest
        # evidence. Gate at month granularity only (drops future-dated data errors).
        view = store.where(lambda x: x["contract_ym"] <= asof[:7])
    else:
        view = store.as_of(t, lag_days=lag_days)
    market = MarketView(view.txs, asof[:7])
    idx = PriceIndex.load()
    ctx = {"asof_ym": asof[:7], "asof_date": t, "index": idx,
           "asof_q": idx.as_of_quarter(t)}

    est = engine_v2(subject, market, ctx)
    if est is None:
        return {"error": "no_estimate",
                "message": "Neither same-project comps nor a statistical anchor could value "
                           "this unit as-of the date — escalate."}
    c1 = c1_grid_adapted(subject, market, ctx)
    used_fallback = c1 is None
    anchors = {"C1_same_project": c1["psf"] if c1 else None}
    for tag, fn in (("A1_hedonic", avm_hedonic), ("A2_pooled", avm_pooled),
                    ("A3_knn", avm_knn)):
        a = fn(subject, market, ctx)
        anchors[tag] = a["psf"] if a else None

    area = subject["area_sqft"]
    reads = [v for v in anchors.values() if v]
    anchor_spread = (max(reads) - min(reads)) / est["psf"] if len(reads) >= 2 else None
    hard = bool(anchor_spread and anchor_spread > 0.15)

    # Recent same-size (time+size-adjusted) reference + directional honesty.
    ref = _recent_ref(subject, market, ctx)
    point_psf, directional = est["psf"], None
    if ref and est["psf"] > ref["adj_psf"] * 1.05:
        gap = est["psf"] / ref["adj_psf"] - 1
        directional = (f"point was {gap*100:.0f}% above the freshest same-size print "
                       f"({ref['adj_psf']:.0f} psf adj, {ref['contract_ym']}) — stale-comp "
                       f"risk; corroborate before offering")
        if hard:
            # pull the point toward the fresh same-size evidence (conservative on hard cases)
            point_psf = round((est["psf"] + ref["adj_psf"]) / 2, 1)
            directional += f"; point pulled to {point_psf:.0f} psf (blended toward fresh print)"
    price = round(point_psf * area, 0)
    scale = price / est["price"] if est["price"] else 1.0
    lo, hi = round(est["low"] * scale, 0), round(est["high"] * scale, 0)
    if directional and hard:
        lo = min(lo, round(ref["adj_psf"] * area, 0))   # band must include the fresh evidence
    band_rel = (hi - lo) / price if price else None
    conf, conf_label = _confidence(est["n_comps"], used_fallback, band_rel, anchor_spread)

    return {
        "subject": {k: subject[k] for k in ("project", "area_sqft", "market_segment",
                    "district", "tenure_type", "lease_start")} | {"floor": spec.floor,
                    "asof": asof},
        "fair_value": {"psf": point_psf, "price": price, "low": lo, "high": hi,
                       "confidence": conf, "confidence_label": conf_label,
                       "n_same_project_comps": est["n_comps"],
                       "basis": est["note"] + ("; blended toward fresh print (hard case)"
                                               if point_psf != est["psf"] else "")},
        "independent_reads_psf": anchors,   # transparency: each method's own opinion
        "anchor_disagreement": {"spread_rel": round(anchor_spread, 3) if anchor_spread else None,
                                "hard_case": hard},
        "recent_same_size_reference": ref,   # the freshest same-size print (adj to as-of)
        "directional_flag": directional,     # set when the point sits above that fresh print
        "comps": _relevant_comps(subject, market),
        # buyer/seller guidance — DERIVED FROM the fair-value band, kept separate from it
        "buyer_guidance": {"attractive_below": lo, "fair_range": [lo, hi],
                           "walk_away_above": hi,
                           "note": "attractive = low end of where comparable units actually "
                                   "print; walk-away = above the observed range"},
        "seller_guidance": {"ask": hi, "expected_clear": price, "quick_sale": lo,
                            "note": "ask at the top of the observed range; expected clear at "
                                    "fair value; quick sale at the low end"},
        "verify_before_offer": [
            "exact remaining lease / tenure for THIS unit (URA tenure is project-level)",
            "actual floor, stack and facing/view (not in the model — URA has no unit id)",
            "unit condition & renovation (no condition adjustment applied)",
            "en-bloc / redevelopment status and any outstanding levies or encumbrances",
        ] + (["thin evidence / hard case — pull twin-unit + AVM comps from Investment "
              "Suite before offering (the engine does not call IS automatically)"]
             if est["n_comps"] < 3 or hard or directional else [])
          + (["FALLBACK used (no same-project comp): remaining-lease decay is only partially "
              "modelled — confirm the exact lease and haircut a short-lease unit manually"]
             if used_fallback and subject.get("tenure_type") == "leasehold" else [])
          + ([directional] if directional else []),
        "limitations": [
            "URA data: month-granular dates, floor BANDS (not exact), no unit id -> no stack/"
            "view/condition/renovation adjustment; note these qualitatively.",
            "Point is same-project-driven; the range is the conformal band (empirical ~82% "
            "held-out coverage, 85% nominal, EXP-0006/0007), not a guarantee.",
        ],
    }
