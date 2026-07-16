"""L4: production landed valuation — value ONE landed house with the LV1 engine.

    from researcher.backtest.value_landed import value_landed, LandedSpec
    v = value_landed(LandedSpec(street="CARDIFF GROVE", land_area_sqft=1839.6,
                                property_type="Terrace"))

Wraps the validated engine (EXP-0011/0012: LC2 street grid + fitted size curve +
lease matching -> LA1 pooled fallback -> conformal band) with:
  - inference of street statics (segment / district / coords / tenure) from URA caveats;
  - confidence tied to the measured error curve (street depth, anchor spread, big-plot);
  - independent reads surfaced (LC2 / LA1 / LB4) — convergence is signal, spread is a flag;
  - an explicit CONDITION treatment: URA prices a LAND+BUILDING BUNDLE it cannot decompose,
    so condition is an INPUT, never an invention (guardrail 5);
  - buyer/seller guidance DERIVED FROM — and separate from — fair value.

As-of semantics (the condo EXP-0008 lesson, applied from day one): no `asof` => LIVE, the
pulled store IS the information set (lag 0). An explicit past `asof` => reconstruction of
what was knowable then (56d caveat lag, day-granular).
"""
from __future__ import annotations

import datetime as _dt
import math as _math
from dataclasses import dataclass
from statistics import median

from .index import PriceIndex
from .landed_benchmarks import lb4_spatial_knn
from .landed_candidates import (la1_pooled_anchor, lc2_fitted_curve, lease_compatible,
                                remaining_lease)
from .landed_engine import landed_engine
from .landed_size_curve import is_big_plot, size_factor
from .market import MarketView
from .store import LANDED_PSF_BAND, TransactionStore, months_between

# Measured in EXP-0010: same-plot repeat dispersion = the irreducible per-print bundle noise.
NOISE_FLOOR = {"Terrace": 0.060, "Semi-detached": 0.078, "Detached": 0.082}
DEFAULT_NOISE = 0.06


@dataclass
class LandedSpec:
    street: str
    land_area_sqft: float
    property_type: str = "Terrace"      # Terrace | Semi-detached | Detached
    tenure_type: str | None = None      # inferred from the street when omitted
    lease_start: int | None = None
    condition: str | None = None        # original | renovated | rebuilt (an INPUT, not a guess)
    asof: str | None = None


def _landed_store(store=None):
    s = store or TransactionStore.load()
    return s.exclude_bulk().where(
        lambda t: t["type_of_area"].lower() == "land"
        and LANDED_PSF_BAND[0] <= t["psf"] <= LANDED_PSF_BAND[1])


def _infer(spec, store) -> dict | None:
    """Street statics from its caveats. Landed has no project id — STREET is the key."""
    key = (spec.street or "").strip().casefold()
    rows = [t for t in store.txs if (t["street"] or "").strip().casefold() == key]
    if not rows:
        return None
    same_type = [t for t in rows if t["property_type"] == spec.property_type] or rows

    def _mode(rs, k):
        vals = [r[k] for r in rs if r.get(k)]
        return max(set(vals), key=vals.count) if vals else ""
    xs = [r["x"] for r in rows if r.get("x") is not None]
    ys = [r["y"] for r in rows if r.get("y") is not None]
    ls = [r["lease_start"] for r in same_type if r.get("lease_start")]
    asof = spec.asof or _dt.date.today().isoformat()
    return {
        "id": "SUBJECT", "project": "", "street": spec.street,
        "market_segment": _mode(rows, "market_segment"), "district": _mode(rows, "district"),
        "property_type": spec.property_type, "type_of_area": "Land",
        "type_of_sale": "Resale",
        "tenure_type": spec.tenure_type or _mode(same_type, "tenure_type") or "freehold",
        "tenure_raw": _mode(same_type, "tenure_raw"),
        "lease_start": spec.lease_start or (int(median(ls)) if ls else None),
        "contract_ym": asof[:7], "area_sqft": float(spec.land_area_sqft),
        "psf": None, "price": None, "floor_lo": None, "floor_hi": None,
        "x": (sum(xs) / len(xs)) if xs else None,
        "y": (sum(ys) / len(ys)) if ys else None, "no_of_units": 1,
    }


def _confidence(n_comps, fallback, anchor_spread, big_plot, ptype) -> tuple[int, str]:
    """Anchored on the MEASURED landed error curve (EXP-0010/0012), not invented tiers.
    Ceiling is lower than condo's by construction: the bundle noise floor is ~6-8%/print."""
    if fallback:
        c, label = 40, "low — no lease-compatible street comp; pooled fallback (~10% typical)"
    else:
        c = 78 - 30 * _math.exp(-n_comps / 5)      # n=1 ~53, n=5 ~67, n=15 ~77
        label = ("moderate-low — thin street evidence" if n_comps <= 2 else
                 "moderate — some street evidence" if n_comps <= 7 else
                 "good — deep street evidence")
    if anchor_spread:
        c -= min(30.0, max(0.0, (anchor_spread - 0.06) * 140))
        if anchor_spread > 0.18:
            label += f"; hard case: methods disagree {anchor_spread*100:.0f}% — corroborate"
    if big_plot:
        c = min(c, 45)
        label += "; >=8k sqft: size curve poorly identified here — case-tier, indicative only"
    floor = NOISE_FLOOR.get(ptype, DEFAULT_NOISE)
    label += f"; bundle noise floor ~{floor*100:.0f}%/print caps achievable precision"
    return max(20, round(c)), label


def _street_ref(subject, market, ctx):
    """Freshest lease-compatible same-street same-type print, adjusted to the subject for
    time (capped) AND size — the single most credible evidence point."""
    area, asof_ym = subject["area_sqft"], ctx["asof_ym"]
    sim = [r for r in market.landed_on_street(subject["street"])
           if r["property_type"] == subject["property_type"]
           and lease_compatible(r, subject, asof_ym)]
    if not sim:
        return None
    fresh = max(sim, key=lambda r: r["contract_ym"])
    to_q = ctx.get("asof_q")
    tf = ctx["index"].factor(fresh["contract_ym"], to_q, "landed") if to_q else 1.0
    tf = min(max(tf, 0.80), 1.25)
    return {"contract_ym": fresh["contract_ym"], "area_sqft": fresh["area_sqft"],
            "raw_psf": fresh["psf"],
            "adj_psf": round(fresh["psf"] * tf * size_factor(fresh["area_sqft"], area), 1)}


def _comps(subject, market, ctx, n=8):
    """The comps the reader is shown MUST be the comps the point was built from — i.e.
    LEASE-MATCHED. Showing a freehold print next to a leasehold subject under a
    'lease-matched' caption misrepresents the basis and displays exactly the pairing the
    232% guard forbids (a real defect this exhibit had)."""
    area = subject["area_sqft"]
    rows = [r for r in market.landed_on_street(subject["street"])
            if r["property_type"] == subject["property_type"]
            and lease_compatible(r, subject, ctx["asof_ym"])]
    ranked = sorted(rows, key=lambda r: (abs(_math.log(r["area_sqft"] / area)),
                                         -months_between("2000-01", r["contract_ym"])))
    return [{"contract_ym": r["contract_ym"], "land_area_sqft": r["area_sqft"],
             "land_psf": r["psf"], "price": r["price"], "tenure": r["tenure_type"]}
            for r in ranked[:n]]


def value_landed(spec: LandedSpec, store: TransactionStore | None = None,
                 lag_days: int | None = None) -> dict:
    store = _landed_store(store)
    subject = _infer(spec, store)
    if subject is None:
        return {"error": "street_not_found",
                "message": f"No URA landed caveats on street {spec.street!r} in the rolling "
                           "5-year window. Check the URA street spelling, or this plot is out "
                           "of v1 scope — escalate to an Investment Suite street pull (app: "
                           "address -> Sale -> Street scope -> tap the type count -> Type "
                           "Summary), which carries deeper history than the URA API window."}
    today = _dt.date.today()
    asof = spec.asof or today.isoformat()
    t = _dt.date.fromisoformat(asof)
    live = t >= today
    if lag_days is None:
        lag_days = 0 if live else 56                # LIVE vs reconstruction (EXP-0008 lesson)
    if live and lag_days == 0:
        # The pulled store IS the info set. as_of's month-END convention (a backtest leakage
        # guard) would hide the CURRENT partial month — the freshest evidence. Gate at month
        # granularity only. (Ported from value_unit: the same defect was found and fixed for
        # condo in EXP-0008 and had been reintroduced here.)
        view = store.where(lambda x: x["contract_ym"] <= asof[:7])
    else:
        view = store.as_of(t, lag_days=lag_days)
    market = MarketView(view.txs, asof[:7])
    idx = PriceIndex.load()
    ctx = {"asof_ym": asof[:7], "asof_date": t, "index": idx, "asof_q": idx.as_of_quarter(t)}

    # CONDITION: the engine is condition-BLIND (URA carries none). There is no validated
    # condition effect yet (L2e backlog), so we must NOT shift the point or fake a band
    # widening — the conformal band is already calibrated on condition-blind residuals, i.e.
    # it embeds AVERAGE condition ignorance. What we can honestly give is DIRECTION.
    cond = (spec.condition or "").strip().lower() or None
    condition_note = {
        "rebuilt": "you report REBUILT: the comp set is a condition-blind mix, so a rebuilt "
                   "house typically prints ABOVE this estimate — treat the point as a FLOOR. "
                   "Magnitude is NOT quantified (no validated condition effect; L2e backlog).",
        "renovated": "you report RENOVATED: likely to print somewhat above a condition-blind "
                     "estimate; magnitude NOT quantified (L2e backlog).",
        "original": "you report ORIGINAL: rebuilt/renovated comps in the mix pull the "
                    "condition-blind estimate UP, so the point may be a CEILING for an "
                    "original house. Magnitude NOT quantified (L2e backlog).",
    }.get(cond, "condition NOT supplied and NOT inferred. The band already reflects AVERAGE "
                "condition ignorance (it is calibrated on condition-blind residuals); it is "
                "not widened further. Establish condition on site — it is the dominant "
                "unobserved driver of the bundle price.")

    # SUBJECT-SIDE LEASE HOLE (review blocker). `remaining_lease` returns quasi-freehold when
    # a leasehold has no lease_start — right for a COMP (it gets dropped, conservative) but
    # catastrophic for the SUBJECT: it upgrades a real leasehold to quasi-freehold and prices
    # it off freehold comps. Measured swing on a real street: 2,080 -> 1,197 land-psf (-42%)
    # once the lease start is supplied. Never guess a lease: refuse and ask.
    if subject["tenure_type"] == "leasehold" and not subject.get("lease_start"):
        return {"error": "lease_start_required",
                "message": f"{spec.street} is leasehold but no lease commencement year could "
                           "be established (none supplied, none on the street's caveats). A "
                           "leasehold plot CANNOT be priced off freehold comps — that is the "
                           "232% failure this engine exists to prevent. Supply lease_start "
                           "(from the title / INLIS), or escalate to an Investment Suite pull."}

    est = landed_engine(subject, market, ctx)
    if est is None:
        return {"error": "no_estimate",
                "message": "No lease-compatible landed evidence as-of the date — escalate."}
    lc2 = lc2_fitted_curve(subject, market, ctx)
    fallback = lc2 is None
    reads = {"LC2_street_grid": lc2["psf"] if lc2 else None}
    for tag, fn in (("LA1_pooled", la1_pooled_anchor), ("LB4_spatial_knn", lb4_spatial_knn)):
        a = fn(subject, market, ctx)
        reads[tag] = a["psf"] if a else None
    vals = [v for v in reads.values() if v]
    spread = (max(vals) - min(vals)) / est["psf"] if len(vals) >= 2 else None
    hard = bool(spread and spread > 0.18)
    area = subject["area_sqft"]
    big = is_big_plot(area)

    ref = _street_ref(subject, market, ctx)
    point_psf, directional = est["psf"], None
    if ref and est["psf"] > ref["adj_psf"] * 1.06:
        gap = est["psf"] / ref["adj_psf"] - 1
        directional = (f"point was {gap*100:.0f}% above the freshest comparable street print "
                       f"({ref['adj_psf']:.0f} land-psf adj, {ref['contract_ym']}) — "
                       f"stale-comp risk; corroborate")
        if hard:
            point_psf = round((est["psf"] + ref["adj_psf"]) / 2, 1)
            directional += f"; point pulled to {point_psf:.0f} (blended toward fresh print)"
    price = round(point_psf * area, 0)
    scale = price / est["price"] if est["price"] else 1.0
    lo, hi = round(est["low"] * scale, 0), round(est["high"] * scale, 0)
    if directional and hard:
        lo = min(lo, round(ref["adj_psf"] * area, 0))
    conf, conf_label = _confidence(est["n_comps"], fallback, spread, big,
                                   subject["property_type"])
    rem = remaining_lease(subject, ctx["asof_ym"])

    # GUIDANCE GATE. The conformal band is PREDICTIVE uncertainty (how wrong the engine
    # tends to be), NOT the price dispersion a seller can achieve. When the band is wide the
    # two diverge, and mechanically quoting its endpoints converts engine IGNORANCE into
    # negotiation AGGRESSION — e.g. "ask 21.8M" on a plot that prints 14M, at an implied psf
    # above every comp on the page. If the engine has already said "indicative only", it has
    # no business emitting an ask.
    # The gate must respond to THIS SUBJECT. band_rel alone cannot: the conformal table is
    # keyed on (street-liquidity x type), so band_rel is a per-CELL constant and is blind to
    # a hard case — trial 1 (ALNWICK) was hard_case=True and still emitted an ask above every
    # comp on its own page. Gate on the signals that actually vary per subject: the engine's
    # own hard_case / directional flags and its confidence.
    band_rel = (hi - lo) / price if price else 0.0
    guidance_ok = (not (big or fallback or hard) and conf >= 55 and band_rel <= 0.45)
    if guidance_ok:
        buyer = {"attractive_below": lo, "fair_range": [lo, hi], "walk_away_above": hi,
                 "note": "read off the conformal band — where comparable plots actually "
                         "print; NOT a negotiation target"}
        seller = {"ask": hi, "expected_clear": price, "quick_sale": lo,
                  "note": "ask at the top of the observed range; expected clear at fair "
                          "value; quick sale at the low end"}
    else:
        why = ("plot >=8k sqft (size curve poorly identified)" if big else
               "no lease-compatible street comp (pooled fallback)" if fallback else
               f"methods disagree {spread*100:.0f}% (hard case)" if hard else
               f"confidence {conf}/100 is too low" if conf < 55 else
               f"uncertainty band is +/-{band_rel/2*100:.0f}%")
        msg = (f"SUPPRESSED — {why}. The band here is the engine's own error, not an "
               f"achievable price range; deriving an ask/walk-away from it would be "
               f"aggression dressed as analysis. Use the point as INDICATIVE, establish "
               f"condition + geometry on site, corroborate via Investment Suite, then "
               f"re-value.")
        buyer = {"attractive_below": None, "fair_range": [lo, hi],
                 "walk_away_above": None, "note": msg}
        seller = {"ask": None, "expected_clear": None, "quick_sale": None, "note": msg}

    return {
        "subject": {"street": spec.street, "land_area_sqft": area,
                    "property_type": spec.property_type,
                    "tenure_type": subject["tenure_type"],
                    "remaining_lease_years": (None if rem >= 800 else round(rem)),
                    "market_segment": subject["market_segment"],
                    "district": subject["district"], "condition": spec.condition,
                    "asof": asof},
        "fair_value": {"land_psf": point_psf, "price": price, "low": lo, "high": hi,
                       "confidence": conf, "confidence_label": conf_label,
                       "n_street_comps": est["n_comps"], "basis": est["note"]
                       + ("; blended toward fresh print" if point_psf != est["psf"] else "")},
        "independent_reads_land_psf": reads,
        "method_disagreement": {"spread_rel": round(spread, 3) if spread else None,
                                "hard_case": hard},
        "recent_street_reference": ref,
        "directional_flag": directional,
        "condition_note": condition_note,
        "comps": _comps(subject, market, ctx),
        "buyer_guidance": buyer,
        "seller_guidance": seller,
        "verify_before_offer": [
            "TITLE & PLANNING (INLIS/URA): exact land area, tenure, road reserve/drainage "
            "reserve take, setbacks, conservation or landed-housing-area controls",
            "PLOT GEOMETRY (frontage/depth/shape/corner) — URA carries NONE of it; the model "
            "is geometry-blind, so a bad shape or a reserve take is unpriced here",
            "BUILDING CONDITION & AGE — the caveat price is a LAND+BUILDING bundle; confirm "
            "original / renovated / rebuilt and GFA on site",
            "redevelopment potential is NOT priced in — verify GPR/height/plot rules before "
            "paying for it",
        ] + (["thin/no street evidence or methods disagree — pull the street's Type Summary "
              "from Investment Suite (address -> Sale -> Street scope -> tap the type count) "
              "before offering"] if est["n_comps"] < 3 or hard or fallback else [])
          + (["large plot (>=8k sqft): the size curve is poorly identified here (EXP-0011) — "
              "treat the point as INDICATIVE and run the case protocol"] if big else [])
          + ([directional] if directional else []),
        "limitations": [
            f"URA prices a LAND+BUILDING BUNDLE and carries no condition/GFA/geometry -> an "
            f"irreducible per-print noise floor of ~{NOISE_FLOOR.get(spec.property_type, DEFAULT_NOISE)*100:.0f}% "
            f"(EXP-0010, same-plot repeats). No model on this data can beat it.",
            "Engine LV1 measured 9.3% median APE / 78.9% held-out band coverage on 7,027 "
            "walk-forward landed resales (EXP-0012) — honest high-single-digit, not condo-grade.",
            "The engine is CONDITION-BLIND and GEOMETRY-BLIND: it does not shift the point for "
            "condition (no validated effect — L2e backlog) and cannot see frontage/shape/"
            "corner/reserve at all. The band embeds AVERAGE condition ignorance because it is "
            "calibrated on condition-blind residuals — it is not widened per-subject.",
            "The band is the ENGINE'S predictive error, not an achievable negotiation range; "
            "where it is wide the buyer/seller guidance is suppressed by design.",
        ],
    }
