---
name: landed-property-due-diligence
description: Use when evaluating a SPECIFIC Singapore landed house (terrace/semi-D/detached/GCB) before offering — land, structure, title, rebuild economics, hazards, negotiation — producing a DD report with a screening score, a go/no-go, and a mandatory deep-DD alert section.
---

# DD a specific Singapore landed house

Address in, bilingual HTML DD report out. Run AFTER `landed-area-research` has shortlisted the
area. The land matters more than the house — score it that way.

## Run the chain

```powershell
# 1. FACTS — the whole free/official chain. Never hand-edit the output.
python -m researcher.landed.dd "14 SELETAR GREEN WALK" --road "SELETAR GREEN WALK" `
    --slug seletar_green_walk_14          # -> researcher/landed/<slug>_dd_raw.json

# 2. JUDGEMENT — you write this: archetype, verdict, highlights, deep-DD alerts, tax clock.
#    researcher/landed/<slug>_dd.json     (copy seletar_green_walk_14_dd.json as the shape)

# 3. RENDER — summary + KPIs + charts + per-dimension detail + the alert section.
python deliverables/build_landed_dd_report.py <slug>
```

One-time: the chain needs a **free** URA Data Service key (register at
https://www.ura.gov.sg/maps/api/), saved to `research/.secrets/ura_access_key` (gitignored —
never commit it), then `python -m researcher.sources.ura` to pull the caveats.

**The facts/judgement split is load-bearing.** `_dd_raw.json` is reproducible by re-running the
chain; `_dd.json` is your argument. Hand-editing the raw file destroys the only property that
makes it worth trusting. If a raw number is wrong, **fix the tool, re-run, and say so.**

## Verify the tools — every run, before the report

The chain encodes checks that were learned from getting them wrong by hand. It does not encode
judgement, and it can be wrong. Before anything goes in a report, spot-check against source:

- **Re-run one zoning point** and one `nearby_zones` row against `mp_zoning` directly.
- **Re-read one caveat** — does the cohort median match the rows you can see?
- **Confirm the geocode is the house**: `blk_no` + `postal`, not the estate name.
- **Read every `reaches_target: false`** — that transect never landed in the parcel it names.
- **Sanity-check the plot area** against the caveats' land areas on the same street. Two
  independent sources agreeing is the whole reason plot area is usable without a title.

A tool that is wrong in a way nobody checks is worse than no tool. Report what you verified.

## It is all DD — the tiers are about who settles it and when

There is no "screening" phase that is somehow not due diligence. Every question is a DD
question; they differ only in **who can answer it, what it costs, and how late in the deal it
can wait**. Never file an item by "free vs paid" — an S$16 title search is not deep DD, and a
free site visit at 7am is not a desk check.

## It is all DD — the tiers are about who settles it and when

There is no "screening" phase that is somehow not due diligence. Every question is a DD
question; they differ only in **who can answer it, what it costs, and how late in the deal it
can wait**. Never file an item by "free vs paid" — an S$16 title search is not deep DD, and a
free site visit at 7am is not a desk check.

| Tier | Who runs it | Cost | When | Gate |
|---|---|---|---|---|
| **DD-1** | you, at the desk | free | **every** candidate, before viewing | none |
| **DD-2** | you, at the desk | ~S$5–200 | shortlist, **before offering** | none — self-serve |
| **DD-3** | QP / surveyor / PE / lawyer / inspector | S$1k–15k+ | OTP-conditioned, or pre-offer if you'll risk the spend | **several need the SELLER's consent** |

**The DD-3 gate is the part people miss.** Some DD-3 items are not "expensive", they are
*not yours to obtain*: the approved plans need the owner's signed authorisation. If it needs
the seller, it is a **negotiation item that must be agreed before or inside the OTP** — not a
task you can quietly schedule. Put it in the alert section, not the to-do list.

**Timing is a hard constraint, not a preference.** A landed OTP typically gives ~14 days to
exercise. A topographical survey + soil investigation + PE report does not fit in 14 days.
So each DD-3 item resolves exactly one way — and the report must say which:
(a) spend before offering and risk losing the house, (b) fits inside the option period,
(c) written into the OTP as an express condition, or (d) **accepted as a priced risk**.
An item with no answer to "when" is not a finding, it is a wish.

## Condition the DD on the archetype FIRST

The same checklist applied to every house produces a mountain of irrelevant alerts and hides
the two that matter. Decide the archetype before running anything:

| Archetype | What actually drives the DD |
|---|---|
| **Teardown / rebuild play** | Buildability is everything: nett site area, envelope, sewer/drain corridors, soil, trees, neighbour party walls. Structure condition barely matters — it's going. |
| **Recently-built turnkey** (developer estate, <10 yrs) | Buildability is **moot** — nobody rebuilds a 5-year-old house. Plans should be clean; risk shifts to defects, build quality, warranty/DLP expiry, and the **estate's surroundings**. |
| **A&A candidate** (sound structure, dated) | The hybrid, and the hardest: what can be *retained* decides the cost, and only a QP can say. |
| **GCB** | Its own regime: ~1,400 sqm min plot, 2-storey limit, Singapore-citizen-only buyer pool. |

A rebuild-cost model on a turnkey house, or a defects inspection on a teardown, is wasted work
that makes the report look thorough while missing the point.

## Data source — Tier-1 is URA, and it is free

**Pricing, comps and land-psf must come from Tier-1**: **URA Data Service**
(`researcher/sources/ura.py`, free key) or Investment Suite. For landed, URA is enough and
often better: `typeOfArea='Land'` rows carry the **LAND area**, so `psf` IS land psf — the
denominator landed pricing actually runs on. EdgeProp / PropertyGuru / 99.co / SRX are
**Tier-2** — usable, reconcile against Tier-1, label them as claims. Agent sites are Tier-3.

URA's limits shape every figure: month granularity (no day), ~5y rolling, caveats lag so recent
months under-report, and **landed project names are anonymised** to "LANDED HOUSING DEVELOPMENT"
— the STREET is the only join key, so you cannot pin a caveat to a house number from URA alone.

**Investment Suite is optional here, not a gate.** If it is wanted and won't open (emulator
down, `adb devices` empty), say so and carry on with URA — do not stall the whole report on it.
Nothing in DD-1 needs transaction data at all.

**Read the caveats before you trust a portal.** On Seletar Green Walk all 63 URA prints say
"999 yrs lease commencing from 1879"; portals round that to "freehold". Free, and it catches a
tenure misstatement before you offer.

## DD-1 — free, official, reproducible. The chain RUNS it; you interpret it.

A DD-1 item is only done when it has **a value, a source and a date**. "Check URA SPACE" is not
a finding. `researcher/landed/dd.py` chains all of it; what each piece means:

- **Address** (`onemap.py`) → blk_no + postal. Always pass `expect_road=`: OneMap is fuzzy,
  never says "no match", and substitutes (`SELETAR ROAD` → `SELETAR AEROSPACE ROAD 1`, 3.7km
  off; `YIO CHU KANG ROAD` → `OLD YIO CHU KANG ROAD` — which is why the assert is equality, not
  substring). Judge precision on **blk_no + postal**, never on `match`: it returns the estate
  name, so a house-level hit looks fuzzy.
- **Zoning + landed control** (`mp_zoning.py`) → MP2025 zone, GPR, landed TYPE and storey
  **envelope**, off URA's gazetted layers on data.gov.sg. MP2025 is in force **1 Dec 2025** —
  MP2019 is superseded; say which vintage you read.
- **Plot area, free** (`mp_zoning.plot_area_at`) → in landed areas the Land Use layer is cut
  **per plot**, so the containing parcel is the house's own plot. Cross-check it against the
  land areas on the street's caveats: on Seletar Green Walk the parcels read 150.0 sqm and 42
  of 63 caveats report exactly 1,615 sqft. Two independent official sources agreeing is what
  makes this usable — but it is an indicative **zoning** parcel, not a cadastral lot. The legal
  area is still INLIS (DD-2).
- **The neighbour scan — the highest-yield check here** (`nearby_zones` + `transect`). The
  value-killer is usually an adjacent parcel's zoning, not the house. But a zone label plus a
  distance **invents risks**: read the parcel **AREA** (a 14.5 sqm `UTILITY` is a cable box,
  not a substation) and walk the **transect** (a `BUSINESS 2` parcel 151m south sits behind
  ~100m of zoned park and a road — durable, though a Master Plan amendment could still change
  it). Honour `reaches_target: false`: that ray never landed in the parcel it names.
- **Flood** (`pub_flood.py`) → the list is ~36 named locations covering **23.3 ha of
  Singapore's ~73,000 ha (0.032%)**. There is no free geospatial flood layer — the data.gov.sg
  "Flood Prone Areas" dataset is a national hectares series, not polygons, and matching is by
  NAME so a flooding road next to yours won't hit. Report "not on the national list", never
  "not flood-prone"; send the real question to DD-3.
- **Trees.** Only **two** Tree Conservation Areas exist (gazetted 2 Aug 1991, South Central +
  Eastern). Inside one, felling a tree >1m girth (at 0.5m up) on private land needs approval.
  Outside them, do not raise a TCA alert — check the site instead.
- **Comps** (`researcher/landed/comps.py`) → **never quote a street average psf.** Landed land
  psf is strongly size-dependent: on one street, one period, one tenure, Seletar Green Walk's
  <1,800 sqft plots run a median $2,663/psf against $2,186 for 1,800–2,500 sqft. An average
  mixes cohorts and describes no real house — and is why portal psf figures look
  self-contradictory. Price the subject against `subject_cohort()`, its OWN size band.
- **"Nearest X" is only a claim about Singapore if the list is island-wide.** Schools and
  MRT/LRT now come from `researcher/sources/amenities.py` — every P1-bearing MOE school
  (School Directory, data.gov.sg) and every station (OneMap), pre-geocoded and cached with a
  build date. They used to be **15 primaries and 8 stations hardcoded** for the Seletar/
  Serangoon area this chain was first written against; anywhere else the report silently
  said *"no primary within 2.2km"* — 385 Loyang Rise's did, and it is false. **A false
  negative is worse than a gap: the gap is visible.** Malls/expressways are still a curated
  north-east list and are reported as *"nearest of these"*, never *"nearest in Singapore"*.
  Refresh: `python -m researcher.sources.amenities --rebuild`.
- **"Street" is URA's PARENT label, not the road** (measured, EXP-0018) — two claims you must
  therefore never make. **(1) "No transactions on this street."** An empty comp set means
  nothing is filed under that NAME: URA files small roads under the estate's main road, so
  `CARDIFF GROVE` returns nothing while its houses sit under `ALNWICK ROAD` (16 of 17 sales
  matched on month+price+area). **Look up the parent road before reporting an absence.**
  **(2) "These are all houses on this road."** A street set can include adjacent roads: URA's
  `LOYANG RISE` (135) is exactly Loyang Rise (104) + Loyang View (31). Only Investment Suite
  resolves a caveat to a real address (it is also the only way to get the parent mapping).
- **Schools — and the 1km ring is not a permanent attribute.** Distance is a *number with a
  method*. The operative artifact is OneMap **SchoolQuery** (`onemap.gov.sg/school`, free, enter
  the postal code), which measures the shortest distance from **any point on the school's
  boundary** to the residential address, off building plans. Our haversine to the school's
  *point* is a conservative **over**-estimate — safe when it says inside, undecided near the
  line, and **never a substitute for the category itself**. Read SchoolQuery's own disclaimer
  before calling the ring a fact: it is recomputed **annually** (June vintage), "distances can
  change yearly when building plans or school boundaries are updated", SLA supplies it "as is"
  as a *guide*, and tells parents to verify the category **in their child's registration year**.
  So a ring status verified today does not bind a registration years out — on a school-driven
  purchase that belongs in the alerts, not the verified list. MOE has stated it found no
  computation error in SchoolQuery — do not repeat that rumour.

## DD-2 — cheap, self-serve, and it belongs BEFORE the offer

SLA **INLIS** (app.sla.gov.sg/inlis), no professional needed:
- **Property Ownership Information — S$5.25.** Registered owner.
- **Property Title Information — S$16.00.** Lot number and **lot area**, Certified Plan
  number, tenure/lease commencement and expiry, mortgages and charges, caveats, court orders,
  and a **Known Encroachment** flag.

S$16 to know the legal land area, the tenure and whether there is a charge — before you view,
let alone offer. Filing this under "deep DD you do later" is how people offer on an area
figure copied from a listing.

Two SLA caveats that change how you search: SLA disclaims the **address→lot correlation**
(search by **lot**, and verify the address maps to it), and disclaims accuracy of data
extracted from instruments. Title tells you an easement or covenant *exists*; what it *does*
to your plans is a lawyer's and a QP's call — that part is DD-3.

## DD-3 — professional, on-site, or seller-gated

**Seller-gated (agree it before/inside the OTP, or price the risk):**
- **BCA approved architectural/structural plans.** A prospective buyer **cannot** buy these.
  BCA's Plan Purchase admits only the registered proprietor, their corporation's staff, an
  MCST chairman, or an **authorised person holding the owner's signed authorisation plus the
  owner's property tax statement**. So: ask the seller to furnish or authorise. **A seller who
  won't authorise is itself the finding** — without the plans you cannot compare the house to
  what was approved, which is the only way to detect unauthorised works.
- Unauthorised works become the buyer's problem after completion. Treat "as-built ≠ approved"
  as a price/withdraw issue, not a snag list.

**Professional-routed:**
- **Sewer / drainage**: PUB **Sewerage Information Plan** (public sewer alignment) and
  **Drainage Interpretation Plan** (drainage reserves / land reserved for future schemes),
  applied through PUB e-services / CORENET, fee computed from development parameters — the
  route is the **QP's**, not yours. PUB itself says the DIP does not resolve common drains
  inside a development or the Minimum Platform Level; those stay site-verified.
- **Boundary and land area**: SLA Certified Plan + a registered surveyor. The MP layer is
  "indicative" by URA's own label and is not a legal boundary.
- **Buildability**: only a QP, on a surveyed plan — nett site area, setbacks, envelope,
  end-terrace→semi-D, subdivision, basement, retention of existing footprint.
- **Condition**: building inspector / structural PE; CCTV the sanitary line; termites;
  waterproofing; retaining-wall ownership and movement.
- **Site, at the right hours**: weekday day, school dismissal, after 9pm, and during/after
  heavy rain. Two or three of the four. Nothing on a map tells you about headlights, lorry
  noise, or where water goes.

## Rebuild economics (teardown / A&A archetypes only)

- SG landed reconstruction (2025–2026): ~**S$450–600/psf GFA** normal, **S$700+/psf** high-end.
  Add demolition, professional fees, authority fees, GST, contingency, 18–24 months.
- Value = land value + rebuild − teardown/holding, vs a comparable already-rebuilt house.
  Don't pay rebuilt-price for original-condition. "TOP year" is a trap — ask when it was last
  **rebuilt**.
- These are planning numbers. A real A&A budget is a QP feasibility + 2–3 contractor prices.

## Tenure, buyer pool, and the tax clock

- **Tenure**: freehold vs 999 vs 99. A 999-year lease is not freehold — say which, and read the
  commencement year off the title, not the listing.
- **Foreign ownership**: landed is restricted under the Residential Property Act (SLA **LDAU**
  approval; Sentosa Cove the main exception). A restricted title narrows the resale pool.
- **SSD — changed 4 Jul 2025.** For residential bought **on/after 4 July 2025** the holding
  period is **4 years** (was 3) and rates are **4pp higher at each tier (4%–16%)**. No
  transition. It runs off the OTP-exercise date. On any hold shorter than 4 years this is
  usually a bigger number than everything else in the report — carry it explicitly.

## Output — the DD report

`build_landed_dd_report.py` renders: **摘要 Summary** (KPI strip + verdict + highlights +
archetype) → per-dimension detail (plot & planning · neighbours + transect charts · transactions
with the land-size scatter and trend · schools · transport · flood · tax clock) → **the alert
section** → provenance & not-covered. Bilingual, self-contained, no JS.

You write `<slug>_dd.json`:
1. **archetype** — first, before anything else. It decides what the DD is even about.
2. **verdict** — go / no-go / go-at-a-price. If you can't price it, say why in the verdict.
3. **highlights** — what a reader must know before the detail. Lead with what CHANGED a view.
4. **⚠ dd3_alerts — structural, never optional.** One row per item: *what is unresolved · why
   the desk can't settle it · who settles it · cost · **when** (pre-offer / in-option / OTP
   condition / priced-and-accepted) · **seller_gated?*** An empty list renders as a contract
   breach, because a landed DD that escalates nothing did not look.
5. **tax_clock** — carry SSD explicitly; on a short hold it dominates everything else here.

**Do not state a fair value.** A caveat price bundles land AND building and is not decomposable
into land value by dividing by land area — a cohort median is a market observation, not this
house's worth. The landed AVM is a separate in-flight track (`research/registry/01_roadmap.md`,
L0–L4). Give observed prints and their spread; let the reader see the cohort.

`researcher/landed/scorecard.py` (0–100 + red/amber flags) still applies for a screening score,
mirroring Location → Street → Land → Zoning → Neighbours → Future → House.

## Gotchas

- Report **what you verified**, not what you'd check. A DD-1 line without a source is a guess
  wearing a checkmark.
- Absence of evidence is not evidence of absence — the flood list is the standing example.
- Confidence labels ("high/medium") are worthless unless something measured them. This repo
  walk-forward-validates its condo engine; nothing has validated a landed reliability rating.
  Don't import one.
- Identify before you rate: an area figure or a transect usually dissolves a scary label.
- Manholes, sewer lines, protected trees and party walls are the cheap-to-miss,
  expensive-to-fix items — but only on the archetypes where they bite.
