# Skills: PropNex Investment Suite → condo valuation pipeline

Reusable playbooks for reading the **PropNex Investment Suite** Android app and turning
the data into a defensible condo valuation and a buy/hold/sell recommendation. Together
they form one pipeline:

```
read-investment-suite  ->  harvest-scrolling-android-table  ->  value-a-property  ->  property-buy-sell-advisory
   (extract via UI)           (tables into rows)                 (comparable adj.)       (yield + costs + decision)
```

## The skills
| Slug | Description |
|---|---|
| [read-investment-suite](read-investment-suite/SKILL.md) | Extract development facts, transactions, rents and per-unit AVMs from PropNex Investment Suite via UI automation, using the adb-only `research/mbx.py` harness — tab/nav map, tap-by-text, and the no-resource-id / frozen-column / fling gotchas. |
| [harvest-scrolling-android-table](harvest-scrolling-android-table/SKILL.md) | App-agnostic technique to harvest any scrolling Android table into structured rows: dump → snap cells to header columns → scroll the data region → dedup → stale-stop. Reference: `research/harvest_sale.py`. |
| [value-a-property](value-a-property/SKILL.md) | Comparable-adjustment valuation: time/floor/size-quantum/unit-type adjustments, similarity weighting and a same-line anchor, run via `researcher/valuation/engine.py` for any unit. |
| [property-buy-sell-advisory](property-buy-sell-advisory/SKILL.md) | Advisory framework: rental yield, realised holding-period returns, the SG cost stack (BSD/ABSD/SSD), financing (TDSR/LTV/SORA), catalyst/timing, and a buy/hold/sell decision rule. |

## About these skills
These are **native Claude Code skills**: each lives in its own directory as a `SKILL.md`
with YAML frontmatter, so Claude **auto-discovers** them by their `description` and reaches
for the right one when the task matches. They are **tool-agnostic** — data is gathered with
whatever is available: WebFetch/WebSearch for anything on the web, and the `research/mbx.py`
adb harness for the Android app when web sources fall short. The backing code lives in this
repo (`research/`, `researcher/valuation/`, `deliverables/`); the optional Investment Suite
bridge profile lives in the separate `mobile_bridge` repo at
`mobile_bridge/apps/investment_suite.py`.
