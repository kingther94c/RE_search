---
name: landed-investment-analysis
description: Use when analyzing Singapore LANDED property (terrace/semi-D/detached/GCB, an address or a street/estate) as an investment — asymmetric-capture beta read, land-psf pricing, rebuild economics, school-zone verification, liquidity discipline.
---

# Landed investment analysis — the factor framework, operationalized

Built from the 2026-07 factor study (official 51y series + street-level Tier-1
caveat evidence + two analyst-PASSed school-zone studies), stress-tested by a
bull/bear/quant adversarial panel. Evidence tiers:【实测】measured ·【文献】
consensus mechanism ·【推测】hypothesis. Numbers:
`researcher/factors/{beta_layer,factor_model,dialectic_synthesis}.json`;
investor report: `Factor_Study_Landed_Report.html`. Companion skills:
`landed-area-research`, `landed-property-due-diligence`, `read-investment-suite`.

## Data mandate
Tier-1 = Investment Suite landed surfaces (per-address pages with transaction
history since 1998; Street-scope PP panel; street transaction tables) +
SG-official. Landed pages have NO condo-style Nearby table — the panel below the
caveat table is Tier-2 agency listings, never mix. Address search needs a house
number ("23 Frankel Avenue"), street names alone surface projects only.

## Step 0 — the landed β read 【实测, 51y official series】
- Defensiveness = **asymmetric capture: up-capture 0.95 / down-capture 0.74**
  (vs non-landed, since 1998Q4) — NOT a naive low beta. It rides rallies and
  eats ~3/4 of drawdowns.
- α is start-date sensitive: ≈0 from the 1996 peak; +1.8%/yr (t=2.25) over the
  full 51y; +1.0%/yr (t=1.3, insignificant) from the 1998 trough — quote ranges,
  never one number.
- The index is thin-traded and appraisal-smoothed: measured risk is understated;
  index prints are NOT achievable exit prices in stress. 1996-98 landed fell
  MORE than condo (−48%): defensiveness fails in systemic crises.
- 2020-26 outperformance (+48% vs +42%) partly one-off (supply freeze, WFH,
  ABSD-60% diverting foreign money away from condos while citizen-only landed
  was untaxed)【熊方】— don't extrapolate.
- **Never leverage as if low β protects a forced seller; only underwrite with
  10-year holding power**【牛方】.

## Step 1 — price the LAND, not the house
- Unit of account = land psf. Quantum effect: bigger plots trade at lower psf.
- Tenure: FH/999y vs 99y are different assets — price separately.
- Street file first: harvest the Street-scope PP panel + transaction table
  (`research/build_factor_panel.py` parsers; captures via `read-investment-suite`).
  The app's street band head (low/avg/high) is the Tier-1 price band.
- Street long-run appreciation from cross-address same-type pairs (≥5y gap):
  read at ONE significant figure and know the bias — pairs embed plot/rebuild
  heterogeneity. Frankel Ave: ~+6-7%/yr raw, **~4.5-5.5%/yr ex-quality**
  【实测+辩证修正】; official landed index same window ≈ +5%/yr — reconcile
  street reads against it.

## Step 2 — rebuild economics (the largest single spread)【实测, mixed basis】
Same street, same month: **+39%** spread (9 Alnwick, rebuilt DETACHED, vs 15
Alnwick, original SEMI-D, similar land area) — this bundles rebuild status with
the detached-vs-semi-D form premium; a clean same-form rebuild pair is a data
gap, but the magnitude still shows rebuild state is the largest single landed
spread lever. The α program: buy original condition at land value when
`price < rebuilt_comp − build_cost(~$450-550/sqft GFA, post-COVID inflated)
− 2-3y carry − taxes`. Check: plot regularity, GCBA boundary (URA), road
reserve/setback, 999y-vs-99y. If the pro-forma only works at >5%/yr land
appreciation, it doesn't work.

## Step 3 — school-zone factor, verified not vibed 【实测】
1km ballot scarcity is the strongest demand-stickiness factor (Nanyang 2025
Phase 2C 1.5:1; Rosyth 2022-24 ~3:1). BUT:
- "Estate X = school 1km" is often FALSE — Serangoon Gardens core is NOT Rosyth
  1km (OneMap-measured). Always `ring_check` the exact address.
- GEP discontinued 2026 → premium rides SAP brand + ballot scarcity; haircut
  modestly, don't zero it【牛方: GEP was ~1% of cohort】.

## Step 4 — the costs of the asset class (say them first)
- Liquidity: single-street volumes are single-digit per YEAR; stress-period
  exit takes quarters. Read all bands wide; never mark to index prints.
- Friction: BSD top tiers + agent + SSD 4y 16/12/8/4 — alpha only at purchase.
- Capex: old stock carries rebuild/A&A obligations; landed index returns embed
  un-netted capex【量化怀疑者】— net it out of any return you quote.
- Policy: landed is citizen-gated (demand-side rigidity cuts both ways); assume
  a measures round within any 5y hold.

## Step 5 — verify & ship
1. Every load-bearing number Tier-1 (app captures / URA / OneMap), per
   [[data-source-trust-hierarchy]].
2. Stress at 4% mortgage; scenario rent normalization (2022-23 spike reversing).
3. Hostile review via `property-report-review` before the client sees anything.

## Known limits
Street evidence concentrated in 3 studied areas (Nanyang/Rosyth/Frankel);
cross-address pairs are not repeat sales; official series smoothing; the panel's
"landed defensive" history was generated under milder policy than today's stack.
