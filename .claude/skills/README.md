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
landed-area-research  ->  landed-property-due-diligence
 (area report + shortlist)   (per-house score + go/no-go; researcher/landed/scorecard.py)
```

| Slug | Description |
|---|---|
| [landed-area-research](landed-area-research/SKILL.md) | Desktop-first research of a landed AREA (e.g. a school's 1km zone): OneMap school zone, URA Master Plan zoning/GCBA/plot-ratio, transaction structure, hazards & future planning → area report + screening shortlist. |
| [landed-property-due-diligence](landed-property-due-diligence/SKILL.md) | Evaluate a specific landed house — land, structure, SLA INLIS title, rebuild economics, hazards, negotiation → a 0–100 screening score via `researcher/landed/scorecard.py`. |

## Backing code & data

`research/` (harness), `researcher/valuation/` (condo engine), `researcher/landed/`
(landed scorecard), `deliverables/` (report generators → output to
`G:\My Drive\004 RES\REsearch_Reports`). The optional Investment Suite bridge profile lives
in the separate `mobile_bridge` repo at `mobile_bridge/apps/investment_suite.py`.
