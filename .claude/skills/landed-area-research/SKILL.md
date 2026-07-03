---
name: landed-area-research
description: Use when researching a Singapore landed-housing AREA (e.g. a school's 1km zone or a named estate) to produce an area report + a buyer screening shortlist — desktop-first, before any site visit.
---

# Research a Singapore landed AREA (desktop-first)

Goal: do ~80% of the screening on the computer before visiting. Output is an **area
report** (what this micro-market is, prices, risks, future) + a **shortlist of criteria**
to filter listings. Pair with `landed-property-due-diligence` for a specific house.

Gather planning/policy/geography context with `WebFetch`/`WebSearch` against the official SG
sources below; **transaction, land-psf, rent and AVM data must come from Tier-1 — see "Data
source" next.**

## Data source — Investment Suite first (MANDATORY)

Every load-bearing figure — land-psf bands, named transactions, rents and any per-development
AVM — **must come from Tier-1 ground truth: PropNex Investment Suite** (via
`read-investment-suite` / `research/mbx.py`) and **SG-official** sources (URA / URA REALIS,
OneMap for the 1km school ring via `researcher/sources/onemap.py`, PUB for flood, SLA for title,
MOE for balloting). EdgeProp / PropertyGuru / 99.co / SRX are **Tier-2** (usable, but reconcile
against Tier-1); property research reports and agent/marketing sites are **Tier-3** — conflicted,
treat as claims, never as facts.

**If Investment Suite won't open, STOP — do not silently fall back to web data.** Emulator not
running, `adb devices` shows no device, app logged out, or session expired → pause immediately,
report the exact error, and wait for the user to start the emulator / sign in. Resume only once
Tier-1 access is restored, or the user explicitly says to proceed on lower-tier data.

## The value ordering (anchor every judgement to this)

```
Location → Street → Land → Zoning → Neighbours → Future planning → House → Renovation
```
"Buy the land, not the house — the house can be rebuilt; land and location cannot." Renovation
is the *least* important. Weight your report and shortlist accordingly.

## Step 1 — Define the catchment

- If school-driven: confirm the school's exact address, then the **1km** (and 2km) ring.
  Use **OneMap School Query** (https://www.onemap.gov.sg → School Query) — it is authoritative;
  do NOT trust a portal's "within 1km" badge. For balloting demand, find recent Phase 2C
  oversubscription.
- List every landed estate/street in the ring and classify: terrace / semi-detached /
  detached(bungalow) / GCB. Note other schools in the ring (they drive demand too).

## Step 2 — URA Master Plan (the single most important desktop check)

URA SPACE (https://eservice.ura.gov.sg/maps/) — for the estates and, critically, their **neighbours**:
- **Zoning**: Landed Housing / Residential / Commercial / Reserve Site / Educational / Place of
  Worship / Business. Flag anything non-landed *adjacent* — a future condo, school, temple,
  bus depot or GLS site beside a terrace changes its value.
- **Plot Ratio**: Residential 1.4 vs 2.8 → very different future density next door.
- **Designated Landed Housing Area** vs general Residential (different rebuild rules).
- **GCBA** (Good Class Bungalow Area): ~1,400 sqm min plot, 2-storey limit — confirm before
  pricing rebuild GFA, and note GCB = Singapore-citizen-only buyers.
- **Conservation**: limits what you can do.
- **2-storey vs 3-storey** landed limits / attic & basement rules for the estate.

## Step 3 — Transaction structure (read the spread, not the average)

URA REALIS / **EdgeProp** / squarefoot / PropertyGuru transactions. For the micro-market:
- Land-area **psf** ranges + typical **quantum** by segment (terrace / semi-D / detached / GCB).
- Explain the SPREAD on the same street — it is rarely random: rebuilt-vs-original, land size,
  corner/frontage, regular-vs-irregular plot, freehold vs 999/99. Same-street S$1.2m / S$3.5m /
  S$8m are NOT comparable until you adjust for these.
- Liquidity: how often these trade; 2024–2026 price direction for the segment.

## Step 4 — Environment, hazards, future (per street)

- **Google Earth** incl. **Historical Imagery**: orientation, topography, what's behind the
  plot (MRT, expressway, canal, factory, temple, school, ongoing construction), and how the
  area changed over years.
- **Flood**: PUB flood-prone areas (https://www.pub.gov.sg) + low-lying streets near canals/drains.
- **Future planning**: Reserve Sites, Government Land Sales, new roads/MRT, en-bloc pressure
  nearby — all via URA. A reserve site 100m away is a material unknown.
- Connectivity & amenities: MRT walk time, markets, malls, parks, expressway access.

## Step 5 — Produce the deliverables

1. **Area report** — estates table (type, GCBA, indicative land psf, note), price-by-segment,
   zoning/future-planning notes, hazards-by-location, regulatory context, and a clear
   "best-for / watch-outs". Generate HTML with `deliverables/build_landed_report.py` (writes to
   `G:\My Drive\004 RES\REsearch_Reports`).
2. **Screening shortlist** — the filter to apply to listings, e.g.: estate ⊂ 1km ring; regular
   rectangular plot; frontage ≥ target; land psf ≤ ceiling; not low-lying/near canal; freehold;
   rebuilt or rebuild-friendly. Feed candidates to `landed-property-due-diligence` +
   `researcher/landed/scorecard.py`.

## Official SG sources (bookmark)

| Need | Source |
|---|---|
| 1km/2km school zone | OneMap School Query |
| Zoning / plot ratio / GCBA / conservation | URA SPACE Master Plan |
| Transactions | URA REALIS, EdgeProp, squarefoot |
| Flood-prone | PUB |
| Title / easement / restrictive covenant | SLA INLIS |
| Foreign-ownership status | SLA LDAU (Residential Property Act) |
| Topography / history | Google Earth (Historical Imagery) |

## Gotchas

- Portal "1km" badges are wrong often enough to matter — OneMap is the source of truth.
- The biggest value-killer is usually a *neighbour* parcel's zoning, not the house — always
  check what's allowed on adjacent land, not just the plot itself.
- A cheap same-street comp is often cheap for a reason (irregular plot, low-lying, never
  rebuilt). Adjust before comparing.
