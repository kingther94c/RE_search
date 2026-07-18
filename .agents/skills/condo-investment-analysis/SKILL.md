---
name: condo-investment-analysis
description: Use when analyzing a Singapore CONDO as an investment (buy/hold/pass, what to pay, which unit) — applies the reviewed beta/alpha factor framework: segment beta first, priced-in factor checklist, policy-shock overlay, alpha tests gated by the friction hurdle.
---

# Condo investment analysis — the factor framework, operationalized

Built from the 2026-07 factor study (official 51y URA/SingStat series + 27-project
Tier-1 panel + three analyst-PASSed valuations), stress-tested by a bull/bear/quant
adversarial panel. Every rule below carries its evidence tier:
【实测】measured here ·【文献】industry-consensus mechanism ·【推测】hypothesis.
Full numbers: `researcher/factors/{beta_layer,factor_model,dialectic_synthesis}.json`;
investor report: `Factor_Study_Condo_Report.html` (in the gitignored `reports/` and the
Drive library `G:\My Drive RES\REsearch_Reports` — regenerate via
`deliverables/build_factor_report.py`).

## Data mandate (unchanged, non-negotiable)
Tier-1 = PropNex Investment Suite (`read-investment-suite` skill; doctor-gated) +
SG-official (URA/SingStat/OneMap/LTA/MOE/IRAS/MAS). Portals Tier-2 (reconcile);
research/agent reports Tier-3 (claims, never facts). App won't open → STOP per protocol.

## Step 0 — β before everything 【实测, 51y official series】
The segment (CCR/RCR/OCR) and asset class set most of the return path.
- Pull the official series: `python -m researcher.marketdata.singstat` then
  `python -m researcher.factors.beta_layer` — read segment CAGRs, cycle table,
  price/rent stretch (2026Q1: 130 vs peak 146 — partially normalized, still ~30%
  above the 2009 base; the whole sample sits in a ~1.4% mortgage regime).
- **Policy-shock β is Singapore's #1 risk factor**【辩证团新增】: every turning
  point since 2010 was measure-made (SSD/ABSD/TDSR/LTV), hitting
  foreigner/CCR/investor segments asymmetrically. Assume ≥1 measures round
  (either direction) inside any 5-year hold; score the target's policy exposure
  (marginal-buyer nationality mix, investor share, CCR tilt).

## Step 1 — value the unit, not the story
Run the validated engine (skill: `condo-resale-valuation`, engine v2 on the URA
spine); for hard cases corroborate with the IS three-surface craft pipeline
(skill: `value-a-property`, kept for exactly this). Anchor = floor-adjusted freshest
same-spec print; cap = min(AVM, model). The AVM's bias vs fresh prints is NOT
one-directional (measured −3.4%/+1.4%/+3.7%)【实测 n=3】— use it for negotiation
anchoring, never as a strategy.

## Step 2 — priced-in factor checklist 【实测: all 5 factors direction-stable
under leave-one-anchor-out (14 clusters); magnitudes NOT reliable — n=26,
anchor-clustered; segments from the app's Tier-1 Region field】
Within-segment psf premium: **newness ≈ popular-primary-1km strongest**; the
rest (project size, MRT proximity, coast, freehold) weak but direction-stable.
Rules:
- These are LEVEL factors: paying fair for them earns ~zero alpha【文献级假设——
  strict test needs factor-sorted forward returns】; their value is livability,
  liquidity, downside resilience.
- School factor: verify 1km via OneMap (`researcher/sources/onemap.py ring_check`)
  AND Phase 2C ballot history — never trust a listing's "1km" badge (the
  Watten-vs-Royalgreen exact-pin knife-edge is how buyers overpay). GEP was
  discontinued 2026; the premium now rides SAP brand + ballot scarcity, modestly
  haircut it.
- At resale, refuse to pay the newness premium (it is developer margin, not a
  durable factor)【牛方实操】.
- Yield: segment choice, not unit-picking. Panel medians CCR ~2.2% < RCR ~2.9%
  ≈ OCR ~3.0%【实测——CCR-vs-rest solid; RCR-vs-OCR thin in this panel; wider
  market-stylized bands CCR 2-2.5% < OCR 3-4% hold on broader samples】;
  within-segment differences are UNDETECTED at this sample size (power:
  critical ρ≈0.75 at n≈6-7) — treat "high-yield unit in segment" pitches as
  basis-mixing until proven (check price basis + rent contract basis).

## Step 3 — β modifiers on the ride
- Lease decay (99y): deterministic negative drift overlay (Bala curve)【文献】—
  barely represented in our young-leasehold panel, so do NOT extrapolate the
  panel's mild age slope to 30-50y leases; underwrite decay explicitly.
- Age cycle: new-premium digestion in years 1-3 post-TOP (One Pearl Bank low
  floors: 2019 buyers ≈ breakeven in 2026)【实测 case】.
- Mega-project liquidity (↑ turnover, but same-project competing listings cap
  rebounds)【推测】; school-zone demand stickiness【文献】.

## Step 4 — α tests, ALL gated by the friction hurdle
Round-trip friction: BSD ~4-6% (top tiers) + agent/legal ~2-3% + SSD 16/12/8/4%
inside 4y (post-2025-07) + ABSD if applicable (SC2 20%, foreigner 60%) —
compute exact figures with `researcher/tax.py` (`entry_costs`/`breakeven_gain_pct`).
**Gross edge < friction ⇒ not alpha. SSD means alpha is harvested at PURCHASE,
then held** — flipping is dead.
- Factor mispricing: unit priced off its factor-fair value within the project
  (floor/facing: fitted 0.44%/层 at OPB vs 0.30% generic — high floors at
  project-average psf = free spread)【实测】.
- Catalyst timing: buy ANNOUNCED-not-opened infrastructure; opened = priced
  (CCL6 案例)【牛方: money made at announcement】. Check GLS pipeline near the
  catchment — the state leans against catalyst runs【熊方】.
- AVM-lag negotiation windows【实测 n=3, anecdote-grade】.

## Step 5 — verify & stress before recommending
1. Rate stress: recompute carry at 3.5-4.5% mortgage + non-owner property tax.
2. Supply: URA unsold inventory + GLS in the planning area (the #1 missing
   overlay per the panel — do it manually until tooled).
3. Policy scenarios both ways (tightening AND relaxation whipsaw).
4. Every load-bearing number Tier-1-sourced; hostile review via
   `property-report-review` before the client sees anything.

## Known limits (say them, don't hide them)
n=26 anchor-clustered panel (fringe-CCR heavy, Sentosa absent); survivorship
(app shows marketable projects only); mixed new-sale/resale psf; straight-line
distances; single-rate-regime history. Conclusions are direction-grade, not
elasticities.
