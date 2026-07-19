---
name: landed-valuation
description: Use to value a specific Singapore LANDED house (terrace / semi-detached / detached) — a defensible fair value on LAND psf, a calibrated range, confidence, street comps, and buyer/seller price guidance. Runs the walk-forward-validated engine LV1 on the URA land-caveat spine and renders a bilingual report. Plot-first; declines rather than guessing.
---

# Value a landed house — engine LV1 (validated)

## When to use
Put a defensible market value on a specific SG landed property. The engine is
**quant-validated**: time-consistent walk-forward on 7,027 landed resales gives
**~9.1% median APE / 78.9% held-out band coverage / 100% answer rate**
(research/registry/ EXP-0010/0011/0012/0017).

**Read this number honestly.** Landed accuracy is structurally worse than condo's 3.7%,
and that is not a defect: URA prices a **LAND+BUILDING BUNDLE** and carries no condition,
GFA, age or plot geometry. Same-plot repeat sales put an **irreducible noise floor of
~6% (terrace) / ~7.8% (semi-D) / ~8.2% (detached, thin: n=17 pairs) per print**
(EXP-0010). At ~9.1% the engine is within ~3pp of the floor — most of the remaining error is *unobservable from
bulk data*, not modelling slack. **Never promise condo-grade precision on landed.**

## Inputs
- **Required:** street (as URA spells it), **LAND area in sqft**, property type.
- **Optional but material:** condition (original / renovated / rebuilt), tenure, lease
  start, `--asof`.
- **Out of scope (v1):** strata-landed / cluster housing (a different sub-market — the
  engine's store excludes it); streets with no URA caveat in the rolling 5y window.

## Run it

**An ADDRESS → the full report (估值 + DD + 成本栈). This is the default entry point:**
```bash
python deliverables/build_landed_full_report.py "19 CARDIFF GROVE" --type Terrace \
       --area 1839.57 --condition original --profile PR --count 2
```
Chinese-primary, layered (结论 → 关键数据 → 证据 → 局限), and it does three things this skill
alone cannot: resolves the address's road to the URA street it is actually filed under
(`street_alias.py` — **evidence only, refuses when unknown**, GY-0006), takes the plot area
from MP2025 when `--area` is absent (declared as indicative — the valuation is `land psf ×
area`, so a wrong area is a wrong report), and prices the **cost stack** (BSD/ABSD/SSD), which
dominates any short hold. `--digest <slug>` mounts an authored judgement layer; without it the
report says plainly that it gives **no go/no-go**.

The renderer also carries four observational blocks ported from the 2026-07-19 A/B experiment
(all computed from data already in the run, RAW psf, direct-street only): **近窗读数**
(trailing-12m / 6m / last-3-print cluster medians + cumulative re-rating + implied monthly
drift), **年度趋势表** (street vs subject-cohort by year, in the evidence layer), **离群值语境化**
(a freshest print >5% off its preceding 3-print cluster is labelled 上/下尾单笔·不做锚 instead of
"most credible evidence"), and the **出价读法叙事行** (beyond p75 needs a verifiable reason;
above the top adjusted print you are endorsing one outlier). The digest may carry
`price_path_risks` (see landed-property-due-diligence) — rendered right after the conclusion.

## The AI-blind second arm — run it for EVERY full report

After the tools report is written, spawn ONE subagent to write an independent AI-authored
report of the same subject, **blind**: its only inputs are `researcher/landed/<slug>_dd_raw.json`
and `<slug>_dd.json`. It must NOT open `reports/`, must NOT run engine/builder/comps code, and
every load-bearing number must trace to those two files or to arithmetic it shows. Output:
`<slug>_landed_full_report_AI.html`, published through `write_report` in
`deliverables/report_out.py` (same dual destination), with a top banner
「AI 直写对照版 — 非 walk-forward 验证引擎输出」.

Why (measured, 2026-07-19, 14 Seletar Green Walk): blind arm landed 2.5% off the engine point
— but its band was ±5% where the calibrated band is −15%/+22%, and it self-scored confidence 70
vs the engine's 63. The arm's residual value is **independent reasoning + risk surfacing**
(its top-3 price-path risks were verified and merged into the digest), not uncertainty.

**The blind prompt MUST carry these prohibitions** (each is a failure we observed):
1. The band is a **judgement band** — say so, never present it as calibrated, and do not
   self-score confidence above what "uncalibrated" honestly supports.
2. **No SSD year-by-year enumeration** (user ruling 2026-07-18: tax arithmetic is not a
   decision input) — state only the 4-year hard minimum hold.
3. Stations split **MRT vs LRT** per the official island-wide list — no "nearest station"
   conflation.
4. No estate names or attributes not present in the two input files; every number sourced.

**Compare, then act:** point estimates >5% apart → treat as a hard case (corroborate via
Investment Suite before quoting either; note the divergence in the report tail). Risks the AI
surfaces that the digest lacks → verify each against the raw file, then merge into the digest's
`price_path_risks`. Within 5% and risks overlapping → record one line, done.

**A STREET + area (no address, no DD):**
```bash
python deliverables/build_landed_valuation_report.py --street "ALNWICK ROAD" --area 2800 \
       --type Terrace --condition original
```
Programmatic: `from researcher.engine.value_landed import value_landed, LandedSpec`.
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
  method explode: **LV1 (what you actually get) measures ~11% @8-15k and ~21% @15k+ (n=49),
  vs LC1's 24% / 41%.** (LC2 alone looks prettier because it declines ~29% of 15k+ subjects;
  LV1 answers 100% by picking those up on the pooled anchor, at somewhat worse error.)
- **Lease matching is mandatory, not a nicety.** L1's decisive failure: spatial kNN priced
  ~20-year-left 99yr terraces off freehold neighbours — **median APE 232%**. Quasi-freehold
  (FH/999yr) and real leasehold are NEVER comparable; leaseholds must be within ±25y of
  remaining lease.
- **Time adjustment = published PPI + an OBSERVED bridge (EXP-0017).** Comps ride the
  official landed PPI to the last published quarter — whose midpoint is **~4.5 months
  stale at every valuation date** — then a **fitted local trend** (`local_trend.py`:
  as-of two-way FE on ln psf ~ (street,type)+month) bridges each comp from
  **max(its own month, the quarter's midpoint)** to the newest *visible* caveat month
  (per-comp anchor — a fresh comp must not be double-bridged). Observations only, never a
  forecast: three forecast/replacement variants are in the graveyard (GY-0003/0004/0005).
  Live valuations read the freshest months automatically.
- **Range = split-conformal** per (street-liquidity × type) cell, calibrated on an earlier
  slice, validated **78.9%** held-out through the production band code. It is the ENGINE'S
  predictive error — not a negotiation target.
- **Confidence** is MOTIVATED BY the measured error curve (street depth, method spread,
  big-plot) — an ordering, not a fitted probability — and the label carries the bundle noise
  floor that caps achievable precision.

## The regime-dependent bias — READ THIS BEFORE QUOTING THE POINT
The engine is **unbiased in stable markets and runs LOW when the market accelerates**.
The L2b observed bridge (EXP-0017) closed **~5pp of the ~16pp hot-regime sign-test
excess**; the residual did **not** meet the pre-registered "fixed" bar and stays disclosed
(sign test = % of actual sales above the point; 50% = unbiased):

| regime | 2023H1 | 2023H2 | 2024H1 | 2024H2 | 2025H1 | 2025H2 | 2026H1 |
|---|---|---|---|---|---|---|---|
| sign test (shipped, EXP-0017) | 53.0% | 47.1% | 53.0% | 51.4% | **60.8%** | **62.1%** | **59.6%** |
| — pre-L2b (EXP-0014) | 51.6% | 47.6% | 49.6% | 50.1% | 66.3% | 66.5% | 60.4% |
| median APE | 9.1% | 8.9% | 10.1% | 8.2% | 9.0% | 9.5% | 9.2% |

*(2026H2 omitted: n=28 — too thin to read; it measures 46.4% under the shipped engine vs
60.7% pre-L2b.)*

**Median APE is flat across every regime while the bias still swings ~15pp** — a comp-based
estimate structurally lags an accelerating market; the un-bridgeable tail (newest visible
caveat month → the sale, ~2-3 months in this backtest, less on a live run) is where the
residual lives. **This is permanent, not pending** (EXP-0018): Investment Suite — the only
other Tier-1 source — carries the SAME caveats at the SAME lag (0 of 104 rows newer than
URA's), so no data fixes it either. Its newer-looking rows are the Tier-2 *Realtime Agency
Data* panel: asking/agency data, never caveats. In a hot market treat the point as a **floor**, not a centre. Three
mechanical "fixes" are in the graveyard: index-momentum extrapolation (GY-0003, broke the
unbiased regimes), cap widening (GY-0004, the exposure was ~zero), full PPI replacement
(GY-0005, broke 2023H1). Only the observed bridge survived its regime panel.

## Scope limits (declare them, don't paper over)
- **≥8k sqft plots**: EXP-0011 found the size curve is *worst identified* exactly where the
  error is largest (pre-2023 vs full-history disagree; n=14-51 street groups). The engine
  widens the band ×1.6, caps confidence ≤45, and says **indicative only — run the case
  protocol**. GCB is this case squared.
- **Plot geometry** (frontage / depth / shape / corner / reserve take): URA carries NONE.
  The model is geometry-blind by construction; the report says so and pushes it to
  verification. Never invent a corner premium.
- **Condition** is an INPUT and the engine is condition-BLIND: it does NOT shift the point
  (no validated effect — L2e backlog) and does NOT widen per-subject (the band already embeds
  AVERAGE condition ignorance, being calibrated on condition-blind residuals). It returns a
  DIRECTION (floor/ceiling) only. Never inferred.
- **Redevelopment potential** is never priced — verification-gated language only.

## Fair value vs guidance (kept separate — and built from DIFFERENT things)
- **Fair value** = engine point + **conformal band**. The band is the engine's **predictive
  error** (p10/p90 of actual/pred, 78.9% held-out) — *not* an achievable price range and
  never a negotiation target.
- **Guidance** is read off the **observed evidence**: the lease-matched street prints,
  time+size-adjusted to this plot. **Buyer:** attractive `< p25`, walk-away `> p75`.
  **Seller:** ask `= p75`, expected clear `= point`, quick sale `= p25`.
  *Deriving thresholds from the band instead made 72% of asks land above every comp on the
  subject's own page — a guardrail built from engine ignorance cannot bind.*
- **These are evidence MARKERS, not calibrated probabilities** (EXP-0013; re-measured under
  the shipped L2b adjustment in EXP-0017 — `python research/tools/calibrate_landed_guidance.py`,
  547 as-of-firewalled resales): **~73-83% of real sales land above the p25 marker and
  ~32-38% above p75**, and the rate **still drifts with the regime** (p50 → 53.1%
  pre-2025H2 vs 67.2% after — the residual hot-market lag, see the regime table). We tried
  to re-cut the upper marker to deliver a true 25%; **it did not transfer out-of-sample**,
  so the markers ship with their measured rates rather than a fabricated "quartile" claim.
- **Guidance is SUPPRESSED** (with the reason) when the evidence can't carry quartiles:
  ≥8k plot, pooled fallback, hard case, confidence <55, or <4 lease-matched prints.
  `directional_flag` does not suppress — it annotates *expected clear*, since the quartiles
  already contain the fresh print the point drifted from.

## Verification layer
Every report's `verify_before_offer` carries the engine's flags **plus** the heads of
`landed-property-due-diligence` — INLIS title, road/drainage reserve, setbacks, GCBA /
landed-housing-area controls, condition & GFA on site. **That skill is the verification
layer; this one does not duplicate it.** For a real bid, run both.

## Failure & escalation
- `street_not_found` → **usually a street-NAMING mismatch, not a data gap** (EXP-0018).
  **URA's `street` is a coarse PARENT/locality label that merges adjacent roads**; the app
  resolves the true address street. Proven: **Cardiff Grove** (the engine's classic refusal)
  is carried by URA under **`ALNWICK ROAD`** — 16 of its 17 in-window sales match an ALNWICK
  ROAD caveat on month+price+area; likewise `URA "LOYANG RISE" = IS Loyang Rise (104) + IS
  Loyang View (31) = 135`, exactly. **So: find the PARENT street and value there** (confirm
  via IS: address → Sale → Street scope → the transactions listed there carry real addresses).
  Only escalate for history older than URA's rolling 5y window — which IS genuinely has
  (10Y street window; per-address history back to ~1996). The engine does NOT call IS
  automatically.
- `hard_case` (methods disagree >18%) / `directional_flag` (point above the freshest street
  print) → treat the point as indicative, corroborate with IS, say so.
- Pooled fallback used → confidence ≤40; don't offer on the number alone.

## Reliability / regression
`tests/test_landed.py` + `tests/test_local_trend.py` — size-curve continuity/regimes, the
lease-matching guard (the 232% fix), big-plot scope limit, guidance separation, the Cardiff
escalation, and the trend estimator (mix-robustness, no-extrapolation). **Rerun on every
engine change; the conformal table is fingerprinted against the FULL residual-determining
code (`landed_benchmarks` + `landed_candidates` + `landed_size_curve` + `local_trend`), so
changing the point OR the time adjustment without recalibrating turns the suite RED.** The
harness default (`run_landed`) IS the shipped configuration; `--no-ltrend` is the ablation.

## Related
- `researcher/engine/value_landed.py` — this skill's engine room
- `researcher/engine/landed_engine.py` (LV1 + `shipped_time_ctx`) · `landed_candidates.py`
  (LC2/LA1 + lease) · `landed_size_curve.py` (EXP-0011) · `landed_benchmarks.py` (the L1
  bar + time adjustment) · `local_trend.py` (the L2b observed bridge, EXP-0017)
- `research/experiments/fit_land_size_curve.py` · `research/tools/analyze_landed.py` (conformal) ·
  `research/experiments/landed_noise_floor.py` · `research/experiments/diagnose_l2b.py` (EXP-0016) ·
  `research/experiments/run_l2b_variants.py` / `research/experiments/validate_l2b_v2.py` (EXP-0017)
- `research/registry/` — EXP-0009..0017, the graveyard, the roadmap's L-track
- `landed-property-due-diligence` (verification) · `landed-area-research` (area layer) ·
  `screen-landed-listings` (listing layer)
