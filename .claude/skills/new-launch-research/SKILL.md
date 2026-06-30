---
name: new-launch-research
description: Use when researching a Singapore NEW-LAUNCH / pre-launch condo (新盘) for an own-stay or investment decision — developer & site, price positioning vs comps, demand/supply, payment scheme, thesis & risks, with a verify-before-trust step.
---

# Research a Singapore new launch (新盘)

New-launch data is marketing-heavy and projects get renamed (en-bloc site → launch brand),
so **establish identity first, verify the load-bearing facts, and treat "indicative PSF" as a
starting point, not truth.** Output: a research report + a BUY/SELECTIVE/WAIT/AVOID verdict.
Tool-agnostic: gather with `WebSearch`/`WebFetch`.

## Step 0 — Establish identity (do this before anything else)

Confirm, with evidence: developer/consortium · exact location & district · **tenure** (freehold
vs 99-yr + lease start) · **site origin** (which GLS tender or *which collective sale* — and the
land/breakeven psf if reported) · site area · plot ratio · **total units** · expected **TOP** ·
**launch status & date** · architect. New launches are easily confused with similarly-named or
neighbouring projects — name the subject explicitly and your confidence.

## Step 1 — The five dimensions

1. **Identity, developer & site** (Step 0). Developer track record matters for execution & resale.
2. **Pricing & comparables** — indicative/launch psf + quantum by unit type; position vs
   (a) nearby **new-launch** comps and (b) **resale** in the vicinity → premium or discount, and why.
   The entry price is the single biggest driver of new-launch returns.
3. **Location/connectivity/schools/nature** — MRT walk time, expressways, 1–2km schools, malls,
   parks/nature, and future planning.
4. **Demand, take-up & supply** — launch take-up (% sold, star buys), absorption of nearby
   launches, and the **upcoming supply pipeline** (GLS + launches in the same belt = oversupply risk),
   plus rental-demand drivers / tenant profile.
5. **Thesis, risks, payment & regulatory** — appreciation catalysts (MRT opening, en-bloc uplift,
   scarcity, area transformation), projected yield, **99-yr lease decay**, the BUC **progressive
   payment** scheme (and any deferred option), ABSD/BSD/SSD, TDSR/LTV, mortgage rates.

## Step 2 — Verify (acceptance / 验收)

Before relying on the research, **adversarially re-check** the load-bearing facts via fresh
searches: identity, developer, tenure, site origin, total units, TOP, launch status, indicative
psf, and the comparables. Mark each confirmed / disputed / unverified. Let DISPUTED/UNVERIFIED
facts temper the verdict — don't state guesses as certainties.

## Step 3 — Quantify

- `python -m researcher.newlaunch.scorecard`  → 0–100 quality + BUY/SELECTIVE/WAIT/AVOID, weighted
  to **price positioning** (22) and location (20), with red/amber flags.
- `python -m researcher.newlaunch.pricing`    → entry cost (BSD/ABSD), breakeven psf after
  SSD-free holding, projected exit ROI at appreciation scenarios, gross/net yield. Models the
  BUC progressive-payment timing.

## Step 4 — Deliver

`deliverables/build_newlaunch_report.py <slug>` reads `researcher/newlaunch/<slug>_digest.json`
→ bilingual HTML to `G:\My Drive\004 RES\REsearch_Reports`, incl. the verification table.

## Data sources

| Need | Source |
|---|---|
| Project facts / brochure / price list | Developer site, EdgeProp, PropertyGuru, 99.co, Stacked Homes |
| Site origin / GLS / collective sale | URA GLS records, Business Times / EdgeProp news |
| Transactions (post-launch) & comps | URA REALIS, EdgeProp, squarefoot |
| Zoning / plot ratio / future planning | URA Master Plan (SPACE) |
| Take-up / supply pipeline | EdgeProp/PropertyGuru research, URA pipeline, news |

## Gotchas

- **Indicative ≠ transacted** — showflat/agent psf runs optimistic; check actual caveats once launched.
- **Premium pricing kills returns** — a launch priced well above nearby resale needs the whole area
  to re-rate before you break even; quantify with `pricing.py`.
- **Supply pipeline** in the same belt can cap appreciation and rents for years.
- **99-yr decay** + **progressive payment** change the real return vs a freehold resale — model them.
- New-launch marketing is persuasive; the verify step exists precisely to discount it.
