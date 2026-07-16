---
name: landed-property-due-diligence
description: Use when evaluating a SPECIFIC Singapore landed house (terrace/semi-D/detached/GCB) before offering — land, structure, title, rebuild economics, hazards, negotiation — producing a DD report with a screening score, a go/no-go, and a mandatory deep-DD alert section.
---

# DD a specific Singapore landed house

Run AFTER `landed-area-research` has shortlisted the area. Output is a **DD report** for one
address. The land matters more than the house — score it that way. Quantify with
`researcher/landed/scorecard.py`.

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

## Data source — scope the Tier-1 gate to the figures that need it

**Pricing, comps, land-psf, rents and per-unit AVM must come from Tier-1**: PropNex Investment
Suite (via `read-investment-suite` / `research/mbx.py`) or URA (REALIS / URA Data Service,
`researcher/sources/ura.py`). EdgeProp / PropertyGuru / 99.co / SRX are **Tier-2** — usable,
reconcile against Tier-1, and label them as claims. Agent and marketing sites are **Tier-3**.

**If Investment Suite won't open, STOP — on the priced sections only.** Report the exact error
(emulator down, `adb devices` empty, logged out) and wait, or proceed only if the user says to
use lower-tier data. Do **not** let the gate block DD-1: zoning, geography, schools, hazards and
title facts need no transaction data, and a DD report that stops before doing the free official
checks has failed for a reason that had nothing to do with them.

## DD-1 — free, official, reproducible. RUN it, don't list it.

A DD-1 item is only done when it has **a value, a source and a date**. "Check URA SPACE" is not
a finding. Everything here is scriptable and needs no account:

- **Pin the exact address.** `researcher/sources/onemap.py` → blk_no + postal. Assert the road
  (`geocode(q, expect_road=...)`): OneMap is fuzzy and silently substitutes (`SELETAR ROAD` →
  `SELETAR AEROSPACE ROAD 1`, 3.7km off; `YIO CHU KANG ROAD` → `OLD YIO CHU KANG ROAD`). Judge
  precision on **blk_no + postal**, never on `match` — it returns the estate name and makes a
  house-level hit look like a fuzzy one.
- **Zoning + landed control.** `researcher/sources/mp_zoning.py` → MP2025 zone, GPR, landed
  TYPE and storey **envelope**, from URA's gazetted layers on data.gov.sg (MP2025 in force
  **1 Dec 2025** — MP2019 is superseded; say which plan you read).
- **The neighbour-parcel scan — the highest-yield check in this skill.** The value-killer is
  usually an adjacent parcel's zoning, not the house. Scan nearest-edge distance per zone out
  to ~1km, then **identify what you find before you rate it**: parcel AREA disambiguates a
  14 sqm feeder-pillar `UTILITY` from a substation, and a **transect** tells you whether a
  `BUSINESS 2` parcel 150m away sits behind a zoned park (durable buffer) or a fence. Rating a
  zone label by distance alone invents risks and misses real ones.
- **Flood.** PUB publishes a flood-prone list (Nov 2025 vintage) + a data.gov.sg dataset —
  but it is **~36 locations for all of Singapore**. Absence is near-zero evidence about one
  plot. Report it as "not on the national list", never as "not flood-prone", and send the
  actual question (does *this* plot pond?) to DD-3.
- **Trees.** Only **two** Tree Conservation Areas exist (gazetted 2 Aug 1991, South Central +
  Eastern). Inside one, felling a tree >1m girth (at 0.5m up) on private land needs approval.
  Outside them, do not raise a TCA alert — check the site instead.
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

1. **Verdict** — go / no-go / go-at-a-price, with the price.
2. **DD-1 verified** — every item with **value + source + date**. Bilingual per repo
   convention. Say which Master Plan vintage you read.
3. **DD-2 obtained / outstanding** — title facts, or an explicit "not yet pulled (S$16)".
4. **⚠ Deep-DD alerts — a standalone section, always present.** One row per item:
   *what is unresolved · why the desk can't settle it · who settles it · cost · **when**
   (pre-offer / in-option / OTP condition / priced-and-accepted) · **is it seller-gated?***
   Never merge these into the body. If the list is empty, the report is wrong.
5. **Scorecard** — `python researcher/landed/scorecard.py` (0–100 + red/amber flags), mirroring
   Location → Street → Land → Zoning → Neighbours → Future → House.

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
