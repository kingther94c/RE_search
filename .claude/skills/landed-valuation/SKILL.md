---
name: landed-valuation
description: Use to value a specific Singapore LANDED house (terrace / semi-detached / detached) — a defensible fair value on LAND psf, a calibrated range, confidence, street comps, and buyer/seller price guidance. Runs the walk-forward-validated engine LV1 on the URA land-caveat spine and renders a bilingual report. Plot-first; declines rather than guessing.
---

# Value a landed house — engine LV1 (validated)

## When to use
Put a defensible market value on a specific SG landed property. The engine is
**quant-validated**: time-consistent walk-forward on 7,027 landed resales gives
**~9.3% median APE / 78.9% held-out band coverage / 100% answer rate**
(research/registry/ EXP-0010/0011/0012).

**Read this number honestly.** Landed accuracy is structurally worse than condo's 3.7%,
and that is not a defect: URA prices a **LAND+BUILDING BUNDLE** and carries no condition,
GFA, age or plot geometry. Same-plot repeat sales put an **irreducible noise floor of
~6% (terrace) / ~7.8% (semi-D) / ~8.2% (detached) per print** (EXP-0010). At 9.3% the
engine is within ~3pp of the floor — most of the remaining error is *unobservable from
bulk data*, not modelling slack. **Never promise condo-grade precision on landed.**

## Inputs
- **Required:** street (as URA spells it), **LAND area in sqft**, property type.
- **Optional but material:** condition (original / renovated / rebuilt), tenure, lease
  start, `--asof`.
- **Out of scope (v1):** strata-landed / cluster housing (a different sub-market — the
  engine's store excludes it); streets with no URA caveat in the rolling 5y window.

## Run it
```bash
python deliverables/build_landed_v2_report.py --street "ALNWICK ROAD" --area 2800 \
       --type Terrace --condition original
```
Programmatic: `from researcher.backtest.value_landed import value_landed, LandedSpec`.
As-of: **omit `--asof` for a LIVE valuation** (the pulled store is the info set); an
explicit past `--asof` reconstructs what was knowable then (56d caveat lag).

## What the engine does (explain it, don't redo it)
- **Point = LC2**: same-street, same-type, **lease-matched** grid; every comp moved to the
  subject on the **fitted size curve**; recency half-life 18mo; weighted median. Where the
  street can't answer, **LA1** (lease-matched pooled anchor) takes over purely for coverage
  — never blended into a street answer (L1 showed even 1-2 street comps beat every
  cross-street pool; the condo thin-comp reversal, transposed).
- **The size curve (EXP-0011)** replaced a ported −0.877 constant. Fitted within-street
  (street FE, n=10,399): elasticity is **−0.51 to −0.64 below 5k sqft** but **collapses to
  ~−0.2 above 8k**. Economically: small terraces trade on QUANTUM (extra land ≈ free);
  big plots trade on LAND (每 sqft 计价). Applying one constant to both is what made the old
  method explode: **LV1 (what you actually get) measures 11% @8-15k and 20% @15k+, vs LC1's
  24% / 41%.** (The prettier 11%/17% belongs to LC2, which declines ~29% of 15k+ subjects;
  LV1 answers 100% by picking those up on the pooled anchor, at somewhat worse error.)
- **Lease matching is mandatory, not a nicety.** L1's decisive failure: spatial kNN priced
  ~20-year-left 99yr terraces off freehold neighbours — **median APE 232%**. Quasi-freehold
  (FH/999yr) and real leasehold are NEVER comparable; leaseholds must be within ±25y of
  remaining lease.
- **Range = split-conformal** per (street-liquidity × type) cell, calibrated on an earlier
  slice, validated **78.9%** held-out. It is where comparable plots actually print — not a
  negotiation target.
- **Confidence** is anchored on the measured error curve (street depth, method spread,
  big-plot) and is **capped by the bundle noise floor** — the label says so.

## Scope limits (declare them, don't paper over)
- **≥8k sqft plots**: EXP-0011 found the size curve is *worst identified* exactly where the
  error is largest (pre-2023 vs full-history disagree; n=14-51 street groups). The engine
  widens the band ×1.6, caps confidence ≤45, and says **indicative only — run the case
  protocol**. GCB is this case squared.
- **Plot geometry** (frontage / depth / shape / corner / reserve take): URA carries NONE.
  The model is geometry-blind by construction; the report says so and pushes it to
  verification. Never invent a corner premium.
- **Condition** is an INPUT. Unknown condition widens the band; it is never inferred.
- **Redevelopment potential** is never priced — verification-gated language only.

## Fair value vs guidance (kept separate)
Fair value = engine point + conformal range (objective). **Buyer:** attractive `< low`,
fair `[low, high]`, walk-away `> high`. **Seller:** ask `= high`, expected clear `= point`,
quick sale `= low`.

## Verification layer
Every report's `verify_before_offer` carries the engine's flags **plus** the heads of
`landed-property-due-diligence` — INLIS title, road/drainage reserve, setbacks, GCBA /
landed-housing-area controls, condition & GFA on site. **That skill is the verification
layer; this one does not duplicate it.** For a real bid, run both.

## Failure & escalation
- `street_not_found` → the URA 5y window has nothing on that street (real: **Cardiff Grove**,
  which has a PASS-8.5 craft valuation but zero URA caveats). **Escalate to Investment Suite**:
  address → Sale → Street scope → tap the type count → **Type Summary** (deeper history than
  the URA API window). The engine does NOT call IS automatically.
- `hard_case` (methods disagree >18%) / `directional_flag` (point above the freshest street
  print) → treat the point as indicative, corroborate with IS, say so.
- Pooled fallback used → confidence ≤40; don't offer on the number alone.

## Reliability / regression
`tests/test_landed.py` — size-curve continuity/regimes, the lease-matching guard (the 232%
fix), big-plot scope limit, guidance separation, and the Cardiff escalation. **Rerun on every
engine change; the conformal table is fingerprinted against the point code, so changing LC2
or the curve without recalibrating turns the suite RED.**

## Related
- `researcher/backtest/value_landed.py` — this skill's engine room
- `researcher/backtest/landed_engine.py` (LV1) · `landed_candidates.py` (LC2/LA1 + lease)
  · `landed_size_curve.py` (EXP-0011) · `landed_benchmarks.py` (the L1 bar)
- `research/fit_land_size_curve.py` · `research/analyze_landed.py` (conformal) ·
  `research/landed_noise_floor.py`
- `research/registry/` — EXP-0009..0012, the graveyard, the roadmap's L-track
- `landed-property-due-diligence` (verification) · `landed-area-research` (area layer) ·
  `screen-landed-listings` (listing layer)
