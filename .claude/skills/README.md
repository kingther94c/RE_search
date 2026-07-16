# Skills

Reusable, **native Claude Code skills** (each is a `SKILL.md` with YAML frontmatter, so
Claude **auto-discovers** them by `description`). They are **tool-agnostic** — data is
gathered with whatever fits: `WebFetch`/`WebSearch` for the web (OneMap, URA, EdgeProp,
PUB, SLA…), and the adb harness `research/mbx.py` for Android apps. Two families so far:

## A · Condo valuation (PropNex Investment Suite)

```
read-investment-suite -> harvest-scrolling-android-table -> value-a-property -> property-buy-sell-advisory
   (extract via UI)          (tables into rows)               (comparable adj.)     (yield + costs + decision)
```

| Slug | Description |
|---|---|
| [read-investment-suite](read-investment-suite/SKILL.md) | Extract development facts, transactions, rents and per-unit AVMs from PropNex Investment Suite via UI automation (`research/mbx.py`). |
| [harvest-scrolling-android-table](harvest-scrolling-android-table/SKILL.md) | App-agnostic technique to harvest any scrolling Android table into structured rows. Ref: `research/harvest_sale.py`. |
| [value-a-property](value-a-property/SKILL.md) | Comparable-adjustment valuation for any condo unit. Ref: `researcher/valuation/engine.py`. |
| [property-buy-sell-advisory](property-buy-sell-advisory/SKILL.md) | Yield, holding returns, SG cost stack (BSD/ABSD/SSD), financing, buy/hold/sell rule. |

## B · Singapore landed research

```
landed-area-research  ->  screen-landed-listings  ->  landed-property-due-diligence
 (area report + benchmark)   (PropertyGuru -> rank)      (per-house score + go/no-go)
```

| Slug | Description |
|---|---|
| [landed-area-research](landed-area-research/SKILL.md) | Desktop-first research of a landed AREA (e.g. a school's 1km zone): OneMap school zone, URA Master Plan zoning/GCBA/plot-ratio, transaction structure, hazards & future planning → area report + benchmark + screening shortlist. |
| [screen-landed-listings](screen-landed-listings/SKILL.md) | Pull the ACTUAL for-sale listings (PropertyGuru, via WebSearch — WebFetch is 403-blocked) → normalise → rank by quality score + land-value flag (psf vs area band). Tool: `researcher/sources/propertyguru.py`. |
| [landed-property-due-diligence](landed-property-due-diligence/SKILL.md) | Evaluate a specific landed house — land, structure, SLA INLIS title, rebuild economics, hazards, negotiation → a 0–100 screening score via `researcher/landed/scorecard.py`. |

## C · Singapore new launch (新盘)

```
new-launch-research  ->  scorecard (BUY/SELECTIVE/WAIT/AVOID)  +  pricing (breakeven/ROI)
 (identity -> verify -> thesis)   researcher/newlaunch/scorecard.py        researcher/newlaunch/pricing.py
```

| Slug | Description |
|---|---|
| [new-launch-research](new-launch-research/SKILL.md) | Research a SG new launch / pre-launch: establish identity (developer/site/tenure/units/TOP), price-position vs new-launch + resale comps, demand/take-up/supply, payment scheme, thesis & risks — with a verify-before-trust (验收) step. Tools: `researcher/newlaunch/scorecard.py` (quality + stance) and `pricing.py` (entry cost, breakeven psf, ROI scenarios with BUC progressive payment). |

## Backing code & data

`research/` (harness), `researcher/valuation/` (condo engine), `researcher/landed/`
(landed scorecard + listings), `researcher/sources/` (PropertyGuru), `researcher/newlaunch/`
(new-launch scorecard + pricing), `deliverables/` (report generators → every report goes to
BOTH the gitignored `reports/` and `G:\My Drive\004 RES\REsearch_Reports`, via
`deliverables/report_out.py`). The optional Investment Suite bridge profile lives
in the separate `mobile_bridge` repo at `mobile_bridge/apps/investment_suite.py`.
