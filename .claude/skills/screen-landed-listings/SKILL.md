---
name: screen-landed-listings
description: Use when you need the ACTUAL for-sale landed listings in a Singapore area (e.g. a school's 1km zone) and want them screened & ranked — pulls from PropertyGuru, then scores quality + land value.
---

# Pull SG landed listings (PropertyGuru) → screen & rank

Turns "what's actually for sale here" into a ranked shortlist. Runs AFTER
`landed-area-research` (which gives the area benchmark + hazards) and feeds
`landed-property-due-diligence` (per-house deep dive on the top picks).

## Data source — Investment Suite first (MANDATORY)

The **listings themselves** are portal-sourced (a listing only exists on PropertyGuru/99.co — see
"Access reality" below), but the **benchmark they are scored and value-graded against** — the area's
transaction / land-psf bands and any per-development AVM — **must come from Tier-1 ground truth:
PropNex Investment Suite** (via `read-investment-suite` / `research/lib/mbx.py`) and **SG-official**
sources (URA / URA REALIS, OneMap for the 1km ring). A listing's asking price and self-declared
"1km" / land size are Tier-3 claims — verify land area and catchment against Tier-1 before the
value grade counts. Portal transaction summaries are **Tier-2** (reconcile against Tier-1); research
reports and agent copy are **Tier-3** — conflicted, treat as claims, never as facts.

**If Investment Suite won't open, STOP — do not silently fall back to web data for the benchmark.**
Emulator not running, `adb devices` shows no device, app logged out, or session expired → pause
immediately, report the exact error, and wait for the user to start the emulator / sign in. Resume
only once Tier-1 access is restored, or the user explicitly says to proceed on lower-tier data.

## Access reality (important)

PropertyGuru blocks server-side fetches — **`WebFetch` → HTTP 403**. Working routes:

1. **`WebSearch` (primary, no setup)** — it surfaces *and summarises* live PropertyGuru
   listings (price, land sqft, built-up, psf, tenure, beds, 1km claim). Restrict with
   `allowed_domains: ["propertyguru.com.sg"]`.
2. **Claude-in-Chrome** browser extension — for full structured pulls / pagination (real
   browser session bypasses the bot wall). Use when WebSearch coverage is thin.
3. **PropertyGuru Android app via `mobile_bridge`** — the tested implementation is the
   explorer CLI in that repo: `scripts\propertyguru.ps1 guide` (offline JSON contract
   first), skill `explore-propertyguru`, docs `docs/propertyguru-explorer.md`. Use when
   you want the app's filters/sort + verified HTML evidence reports.

## Useful PropertyGuru URL patterns (cite, don't WebFetch)

- Area index: `/property-for-sale/near-<school>-674`, `/landed-house-for-sale/near-<school>-674`,
  `/detached-house-for-sale/near-<school>-674`
- Street: `/property-for-sale/p/<street-slug>`  ·  Listing detail: `/listing/...-<id>` (a
  `/markdown` suffix sometimes renders cleaner, but is also 403 to WebFetch).

## Queries that work

- `"<street> landed for sale propertyguru Singapore"`
- `"<area> semi-detached freehold sale land sqft psf 1km <school> propertyguru"`
- `"terrace / detached / bungalow for sale within 1km <school> psf propertyguru"`

## Steps

1. **Pull** ~8–15 listings via WebSearch. For each capture: street, type
   (terrace/semi_d/detached/bungalow/gcb), price, land_sqft, builtup_sqft, land_psf, tenure,
   beds, rebuilt?(brand-new/almost-new → recent), and the listing URL.
2. **Normalise** into `researcher/landed/<area>_listings.json` (see the Nanyang file for the
   shape, incl. the `benchmark_land_psf` bands from `landed-area-research`). Add any known
   per-listing screen hints (topography for a "hilltop", `flood_risk: "low"` for a known
   flood street, `rebuild_status`).
3. **Screen**: `python -m researcher.landed.screen <area>` — normalises each listing
   to the scorecard, scores **quality** (0–100) and flags **value** = land psf vs the area
   band (VALUE / FAIR / RICH / BUILD-PRICED), then ranks.
4. **Act**: take the top FAIR/VALUE picks into `landed-property-due-diligence` (INLIS title,
   site visit for plot shape/frontage/topography, rebuild costing).

## Gotchas

- Listings' **"1km" claims are marketing** — confirm with OneMap before trusting catchment.
- **Tiny-plot high psf = build-priced**, not land value: a 2,500 sqft semi-D at S$5,000 psf is
  you paying for a brand-new house, not the land. Prefer FAIR-banded larger regular plots for
  land value; price original houses as **land + rebuild** (S$450–700 psf GFA;
  canonical range: `landed-investment-analysis`).
- Land **psf alone hides plot quality** — shape/frontage/topography aren't in the listing;
  the scorecard leaves them at neutral defaults and flags "verify on site". A hilltop /
  cul-de-sac / above-road note is a real positive; low-lying near a canal is a real negative.
- Landed is **foreign-restricted** — every listing carries that resale caveat.
