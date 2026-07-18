# Deliverables — Investment Suite property valuation

Trial project: value **#18-03 Spottiswoode Suites** (16 Spottiswoode Park Road,
D02, freehold, 743 sqft compact 3BR), read from the PropNex **Investment Suite**
Android app via **UI automation only**, and generalise into reusable tooling.

## Start here

| # | Deliverable | What it is |
|---|---|---|
| 1 | **[Spottiswoode_18-03_Valuation_Report.html](Spottiswoode_18-03_Valuation_Report.html)** | The research report — open in a browser. Self-contained: charts, screenshots, the model, and the buy/sell recommendation. |
| 2 | **[Development_Brief.md](Development_Brief.md)** | Engineering brief — what was built, the API gaps found & filled, method, reproduce steps. |
| 3 | **[../skills/](../skills/)** | Five reusable skill playbooks (read the app · harvest tables · value a property · buy/sell advisory · index). |

## Supporting

- [`../valuation/`](../valuation/) — the model: `engine.py` (generalises to any unit), `dataset.py` (extracted data), `run.py` (apply + advisory), `results.json`.
- [`../research/`](../research/) — extraction toolkit: `mbx.py` (adb harness), `harvest_sale.py` (table harvester), `spottiswoode_transactions.{json,csv}`, and `captures/` (a screenshot + UI dump per action — the audit trail).
- [`../mobile_bridge/apps/investment_suite.py`](../mobile_bridge/apps/investment_suite.py) — the bridge profile for the real app.

## Headline

Independent fair value **S$1.686M ($2,269 psf)**, range **S$1.60–1.80M**, **+1.5%**
vs the app's own AVM (S$1.661M). Gross yield ~3.2%. **Owner: hold / sell into
strength. Buyer: don't chase above fair value.** Figures are for research only —
not a formal valuation or financial advice.
