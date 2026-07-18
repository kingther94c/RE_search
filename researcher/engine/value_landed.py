"""L4: production landed valuation — value ONE landed house with the LV1 engine.

    from researcher.engine.value_landed import value_landed, LandedSpec
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

from researcher.backtest.index import PriceIndex
from researcher.backtest.landed_benchmarks import _tadj_psf, lb4_spatial_knn
from researcher.backtest.landed_candidates import (la1_pooled_anchor, lc2_fitted_curve, lease_compatible,
                                remaining_lease)
from .landed_engine import landed_engine, shipped_time_ctx
from researcher.backtest.landed_size_curve import is_big_plot, size_factor
from researcher.backtest.market import MarketView
from researcher.backtest.store import LANDED_PSF_BAND, TransactionStore, months_between

# Measured in EXP-0010: same-plot repeat dispersion = the irreducible per-print bundle noise.
NOISE_FLOOR = {"Terrace": 0.060, "Semi-detached": 0.078, "Detached": 0.082}
DEFAULT_NOISE = 0.06
# Share of the minority tenure class above which a street's tenure cannot be inferred from
# its mode (measured: ALNWICK 1.5% = quirk, safe; JALAN RINDU 44% = a coin flip worth ~70%).
MIXED_TENURE_SHARE = 0.10


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
    # EXACTLY the backtest universe (is_pure_landed = Land + Terrace/Semi-D/Detached):
    # production inference, comps AND the fitted local trend must see the same rows the
    # walk-forward validated, or "shipped = backtested" quietly stops being true.
    s = store or TransactionStore.load()
    return s.is_pure_landed().exclude_bulk().psf_band(*LANDED_PSF_BAND)


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
    # MIXED-TENURE DETECTION. Inferring tenure from the street MODE is safe only on a
    # single-tenure street. On a mixed street the mode silently upgrades a real leasehold
    # plot to freehold and prices it off freehold comps — the 232% failure class, at high
    # confidence with live guidance. Measured: JALAN RINDU (14 FH / 11 LH) swings +69.8%
    # (S$5.34M vs S$3.14M) on whether tenure is supplied. Surface it; the caller decides.
    # "Mixed" must be MATERIAL, not binary: 3 stray leasehold prints among 205 quasi-FH on
    # ALNWICK ROAD (1.5%) is a data quirk and the mode is safe; JALAN RINDU at 44% (14 FH /
    # 11 LH) is genuinely ambiguous and the mode is a coin flip worth ~70% of the value.
    n_quasi = sum(1 for r in same_type
                  if r.get("tenure_type") in ("freehold", "freehold_equiv"))
    n_lease = sum(1 for r in same_type if r.get("tenure_type") == "leasehold")
    tot = n_quasi + n_lease
    minority = (min(n_quasi, n_lease) / tot) if tot else 0.0
    mixed = tot >= 4 and minority >= MIXED_TENURE_SHARE
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
        "_tenure_inferred": spec.tenure_type is None,
        "_street_mixed_tenure": mixed,
    }


def _confidence(n_comps, fallback, anchor_spread, big_plot, ptype) -> tuple[int, str]:
    """MOTIVATED BY the measured landed error curve (EXP-0010: street depth 1-2 comps 13.5%
    -> 16+ 8.8%) — but the functional form is ASSERTED, not fitted; read it as an ordering,
    not a calibrated probability. Ceiling is lower than condo's by construction: the bundle
    noise floor is ~6-8%/print."""
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
    thin = " (thin: n=17 pairs)" if ptype == "Detached" else ""
    label += f"; bundle noise floor ~{floor*100:.0f}%/print{thin} caps achievable precision"
    return max(20, round(c)), label


def _adjusted_comp_psfs(subject, market, ctx, window_mo: int = 60) -> list[float]:
    """The lease-matched street prints, moved to the subject for time (capped) and size —
    i.e. WHAT COMPARABLE PLOTS ACTUALLY PRINTED, expressed at this subject's spec. This is
    the OBSERVED evidence distribution, and it is what buyer/seller thresholds must be built
    from. (The conformal band is the engine's PREDICTIVE ERROR; deriving an ask from it made
    72% of asks land above every comp on their own page — three hostile rounds' blocker.)

    `window_mo`: 60 = the LC2 comp universe (the shipped thresholds). 12 gives the
    supplementary RECENT markers (`guidance_recent_12mo`): on a street that outran the
    island index, quartiles of a 60-month pool sit below where the street currently
    trades (a Fable review measured a size-twin print 10% above the shipped ask), so the
    report shows the recent window BESIDE the main one — observation only, same filters,
    never a replacement."""
    area, asof_ym = subject["area_sqft"], ctx["asof_ym"]
    out = []
    for r in market.landed_on_street(subject["street"]):
        if r["property_type"] != subject["property_type"]:
            continue
        if not (0 <= months_between(r["contract_ym"], asof_ym) < window_mo):
            continue          # default = same 60mo window as the LC2 point
        if not lease_compatible(r, subject, asof_ym):
            continue
        # use the SAME adjustment the point is built from,
        # or the guidance and the exhibit silently drift apart from the estimate
        out.append(_tadj_psf(r, ctx) * size_factor(r["area_sqft"], area))
    return sorted(out)


def _pctl(vals: list[float], q: float) -> float:
    if len(vals) == 1:
        return vals[0]
    pos = q * (len(vals) - 1)
    lo = int(pos)
    hi = min(lo + 1, len(vals) - 1)
    return vals[lo] + (vals[hi] - vals[lo]) * (pos - lo)


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
    # same single adjustment path as the point/guidance
    return {"contract_ym": fresh["contract_ym"], "area_sqft": fresh["area_sqft"],
            "raw_psf": fresh["psf"],
            "adj_psf": round(_tadj_psf(fresh, ctx)
                             * size_factor(fresh["area_sqft"], area), 1)}


def _comps(subject, market, ctx, n=8):
    """The comps the reader is shown MUST be the comps the numbers were built from — i.e.
    LEASE-MATCHED (showing a freehold print next to a leasehold subject under a
    'lease-matched' caption displays the exact pairing the 232% guard forbids), and shown
    with their ADJUSTED psf. The point and the guidance quartiles both live on the
    time+size-ADJUSTED distribution, so a table of RAW psf makes a correct ask look like it
    sits above every comp — the exhibit must carry the column the numbers come from."""
    area, asof_ym = subject["area_sqft"], ctx["asof_ym"]
    rows = [r for r in market.landed_on_street(subject["street"])
            if r["property_type"] == subject["property_type"]
            and 0 <= months_between(r["contract_ym"], asof_ym) < 60
            and lease_compatible(r, subject, asof_ym)]
    ranked = sorted(rows, key=lambda r: (abs(_math.log(r["area_sqft"] / area)),
                                         -months_between("2000-01", r["contract_ym"])))
    out = []
    for r in ranked[:n]:
        out.append({"contract_ym": r["contract_ym"], "land_area_sqft": r["area_sqft"],
                    "land_psf": r["psf"],
                    "adj_land_psf": round(_tadj_psf(r, ctx)
                                          * size_factor(r["area_sqft"], area), 1),
                    "price": r["price"], "tenure": r["tenure_type"]})
    return out


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
    ctx = {"asof_ym": asof[:7], "asof_date": t, "index": idx, "asof_q": idx.as_of_quarter(t),
           # L2b (EXP-0017): the observed local-trend bridge — fitted on THIS view, so a
           # live valuation reads the freshest visible caveat months (in live mode the
           # bridge reaches the current partial month; reconstruction stops at the lag).
           **shipped_time_ctx(view.txs, asof[:7])}

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
    # The same door, its other half: refusing only when tenure is DECLARED leasehold left the
    # UNDECLARED case wide open — the street mode silently made a leasehold plot freehold.
    if subject.get("_tenure_inferred") and subject.get("_street_mixed_tenure"):
        return {"error": "tenure_required",
                "message": f"{spec.street} is a MIXED-TENURE street (both quasi-freehold and "
                           "leasehold plots trade here), so tenure cannot be inferred from the "
                           "street: guessing wrong swings the value by ~70% and would price a "
                           "leasehold plot off freehold comps (the 232% failure). Supply "
                           "tenure_type (and lease_start if leasehold) from the title/INLIS."}
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

    # THE SHIPPED POINT IS THE BACKTESTED POINT — no production-only blend.
    # A `directional AND hard` blend (point <- mean(LC2, fresh_ref)) used to live here. It was
    # never in the harness, and measuring it on 2,600 firewalled resales showed it FIRED on
    # 3.9% where the raw point was ALREADY unbiased (sign 48.5%) and made them worse: sign
    # 64.4%, median signed -5.98%, median APE +0.85pp. That is precisely why GY-0003 was
    # buried — "it broke the regimes that were already unbiased" — so keeping it in production
    # would apply, against our own standard, the failure we rejected. Deleted; the validated
    # LC2/LV1 point stands.
    #
    # The freshest comparable print is still surfaced, and now SYMMETRICALLY: the old flag
    # fired only when the point sat ABOVE it (17/17) — the side the engine is NOT biased on —
    # and was silent on 58 BELOW-side cases where the gap genuinely predicts error (point
    # <-20% below fresh -> median signed -7.6%, 70% of sales above the point). It annotates;
    # it never moves the point.
    ref = _street_ref(subject, market, ctx)
    point_psf, directional = est["psf"], None
    if ref:
        gap = est["psf"] / ref["adj_psf"] - 1
        if gap > 0.06:
            directional = (f"point is {gap*100:.0f}% ABOVE the freshest comparable street "
                           f"print ({ref['adj_psf']:.0f} land-psf adj, {ref['contract_ym']}) "
                           f"— stale-comp risk; corroborate before offering")
        elif gap < -0.06:
            directional = (f"the freshest comparable street print is {-gap*100:.0f}% ABOVE "
                           f"this point ({ref['adj_psf']:.0f} land-psf adj, "
                           f"{ref['contract_ym']}) — in an accelerating market read the point "
                           f"as a FLOOR (see the regime bias); corroborate before offering")
    price = round(point_psf * area, 0)
    lo, hi = est["low"], est["high"]
    conf, conf_label = _confidence(est["n_comps"], fallback, spread, big,
                                   subject["property_type"])
    rem = remaining_lease(subject, ctx["asof_ym"])

    # GUIDANCE GATE. The conformal band is PREDICTIVE uncertainty (how wrong the engine
    # tends to be), NOT the price dispersion a seller can achieve. When the band is wide the
    # two diverge, and mechanically quoting its endpoints converts engine IGNORANCE into
    # negotiation AGGRESSION — e.g. "ask 21.8M" on a plot that prints 14M, at an implied psf
    # above every comp on the page. If the engine has already said "indicative only", it has
    # no business emitting an ask.
    # GUIDANCE = OBSERVED EVIDENCE, NOT THE ENGINE'S ERROR BAR.
    # The conformal band is a PREDICTIVE interval (p10/p90 of actual/pred). Deriving an ask
    # from its top is not "the top of the observed range" — it is the engine's own ignorance,
    # and it does not bind: 72% of asks landed above EVERY comp on their own page. Thresholds
    # are therefore read off the lease-matched, time+size-adjusted comp distribution — what
    # comparable plots ACTUALLY printed at this subject's spec. The band stays where it
    # belongs: as the fair-value uncertainty, labelled as such.
    # The gate asks ONE question: is the observed evidence adequate to read quartiles from?
    # (`directional` is deliberately NOT a gate: it says the POINT drifted above the freshest
    # print, but the thresholds are quartiles of the comp distribution — which CONTAINS that
    # fresh print — so they are not contaminated by the point's drift. Suppressing them would
    # discard valid evidence because a different number is suspect. Instead it annotates
    # `expected_clear`, which IS the point.)
    band_rel = (hi - lo) / price if price else 0.0
    adj = _adjusted_comp_psfs(subject, market, ctx)
    guidance_ok = not (big or fallback or hard) and conf >= 55 and len(adj) >= 4
    # Supplementary RECENT markers (12mo), only when the main guidance stands and the
    # recent window alone can carry quartiles. Additive: same filters, same adjustment.
    guidance_recent = None
    if guidance_ok:
        adj12 = _adjusted_comp_psfs(subject, market, ctx, window_mo=12)
        if len(adj12) >= 4:
            guidance_recent = {"window_mo": 12, "n": len(adj12),
                               "p25": round(_pctl(adj12, 0.25) * area, 0),
                               "p75": round(_pctl(adj12, 0.75) * area, 0)}
    if guidance_ok:
        p25, p75 = round(_pctl(adj, 0.25) * area, 0), round(_pctl(adj, 0.75) * area, 0)
        # HONEST LABELS. These are the cheap/dear END of the observed evidence — NOT
        # "quartiles of outcomes". EXP-0013 measured where real sales actually fall against
        # them (627 as-of-firewalled resales): ~68-81% of sales land above p25 and ~33-40%
        # above p75, and the rate DRIFTS WITH THE REGIME (a time split gives p50 -> 50.8%
        # on 2024-2025H1 but 62.6% on 2025H2+ — the index-based adjustment lags an
        # accelerating market). A fixed "dear quartile" claim was tried and did not transfer
        # out-of-sample, so we ship the markers with their measured rates instead of
        # pretending to a calibrated probability.
        src = (f"p25/p75 of {len(adj)} lease-matched street prints, time+size-adjusted to "
               f"this plot — the cheap/dear END of what comparable plots ACTUALLY printed")
        measured = ("Measured (EXP-0013, re-measured under the L2b adjustment, EXP-0017): "
                    "~73-83% of real sales land above the p25 marker and ~32-38% above "
                    "p75, still drifting with the regime — evidence markers, NOT "
                    "calibrated probabilities.")
        drift = (f" NOTE: {directional.split(' — ')[0]} — see the directional flag."
                 if directional else "")
        buyer = {"attractive_below": p25, "walk_away_above": p75,
                 "fair_value_band": [lo, hi],
                 "note": f"attractive below / walk away above = {src}. {measured} The "
                         f"fair-value band is the engine's uncertainty, not a target."}
        seller = {"ask": p75, "expected_clear": price, "quick_sale": p25,
                  "fair_value_band": [lo, hi],
                  "note": f"ask / quick sale = {src}; expected clear at fair value. "
                          f"{measured}{drift}"}
    else:
        why = ("plot >=8k sqft (size curve poorly identified)" if big else
               "no lease-compatible street comp (pooled fallback)" if fallback else
               f"methods disagree {spread*100:.0f}% (hard case)" if hard else
               f"confidence {conf}/100 is too low" if conf < 55 else
               f"only {len(adj)} lease-matched street prints — too few to read quartiles")
        msg = (f"SUPPRESSED — {why}. Thresholds would have to come from the engine's own "
               f"error bar rather than observed prints, which is aggression dressed as "
               f"analysis. Use the point as INDICATIVE, establish condition + geometry on "
               f"site, corroborate via Investment Suite, then re-value.")
        buyer = {"attractive_below": None, "walk_away_above": None,
                 "fair_value_band": [lo, hi], "note": msg}
        seller = {"ask": None, "expected_clear": None, "quick_sale": None,
                  "fair_value_band": [lo, hi], "note": msg}

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
                       },
        "independent_reads_land_psf": reads,
        "method_disagreement": {"spread_rel": round(spread, 3) if spread else None,
                                "hard_case": hard},
        "recent_street_reference": ref,
        "directional_flag": directional,
        "condition_note": condition_note,
        "comps": _comps(subject, market, ctx),
        "buyer_guidance": buyer,
        "seller_guidance": seller,
        "guidance_recent_12mo": guidance_recent,
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
            "Engine LV1 measured 9.1% median APE / 78.9% held-out band coverage "
            "walk-forward landed resales (EXP-0017) — honest high-single-digit, not condo-grade.",
            "REGIME BIAS (EXP-0014, partially closed by EXP-0017): the engine is unbiased in "
            "stable markets but runs LOW when the market accelerates. The L2b observed "
            "local-trend bridge closed ~5pp of the ~16pp hot-regime excess (actual exceeded "
            "the point ~66% of the time in 2025 before; ~60-62% now; stable regimes stay "
            "~47-53%) — the residual did NOT meet the pre-registered 'fixed' bar and stays "
            "disclosed. In a hot market still read the point as a FLOOR. (Live valuations "
            "carry LESS residual staleness than this backtest bound: the bridge reads "
            "caveats to the current month, the backtest reconstruction stops ~2 months "
            "earlier.)",
            "The engine is CONDITION-BLIND and GEOMETRY-BLIND: it does not shift the point for "
            "condition (no validated effect — L2e backlog) and cannot see frontage/shape/"
            "corner/reserve at all. The band embeds AVERAGE condition ignorance because it is "
            "calibrated on condition-blind residuals — it is not widened per-subject.",
            "The band is the ENGINE'S predictive error, not an achievable negotiation range; "
            "where it is wide the buyer/seller guidance is suppressed by design.",
        ],
    }
