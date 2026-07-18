# Development Brief — Spottiswoode Suites #18-03 Valuation Pipeline

**Date:** 2026-06-28 · **Trial project:** value `#18-03 Spottiswoode Suites` (16 Spottiswoode Park Road, D02, freehold, 743 sqft compact 3BR) · **Target app:** PropNex **Investment Suite** (`com.investmentsuite`) on `emulator-5554` · **Constraint:** UI automation only — no reverse engineering, no traffic interception, no auth bypass. Sign-in is the operator's job.

---

## 1. Goal → outcome

Point the existing `mobile_bridge` read-pipeline at a *real* property-agent app for the first time, use one unit as a trial, investigate the surrounding price trend, then build a **reusable valuation model for any unit**, a **buy/sell advisory framework**, and ship the lot as skills. Develop/patch the "API" wherever the existing bridge fell short.

**Delivered:**

| Deliverable | Path |
|---|---|
| HTML research report (self-contained, charts + screenshots) | [`deliverables/Spottiswoode_18-03_Valuation_Report.html`](Spottiswoode_18-03_Valuation_Report.html) |
| Skill playbooks (5) | [`skills/`](../skills/) |
| This development brief | `deliverables/Development_Brief.md` |
| Valuation engine + data + results | [`valuation/`](../valuation/) |
| Extraction toolkit (harness + harvester) | [`research/`](../research/) |
| Bridge profile for the real app | [`mobile_bridge/apps/investment_suite.py`](../mobile_bridge/apps/investment_suite.py) |
| Raw captures (PNG + XML + JSON per screen) | `research/captures/` |

**Headline result:** independent model fair value **S$1.686M ($2,269 psf)**, range **S$1.60–1.80M** — **+1.5%** vs the app's own AVM (S$1.661M). The two corroborate; ours is marginally higher because the app appears to under-weight the strong small-unit market and the imminent Cantonment MRT opening. Recommendation: **owner HOLD / sell into strength; buyer do not chase above fair value** (compact-3BR gross yield only ~3.2% vs ~4% for the 1-beds).

---

## 2. What the app gives us (and how it's read)

A single development screen exposes 8 analysis tabs and 5 bottom modules. Everything is native `TextView` text (fully readable via the accessibility tree) but **most nodes carry no resource-id** (Compose-style classes like `s2.e2`). So extraction is **text/desc-anchored + full-screen dumps**, not id-based per-element selectors.

| Tab | What we pulled |
|---|---|
| Property Info | Freehold, TOP 2017, 183 units, D2/RCR, plot ratio 2.8, developer |
| Sale | 15 recent resale transactions (date/level/unit/type/sqft/psf/price) + 10Y price band |
| Rent | rental comps by size band → yield; 3BR 700–800 sqft @ $4,450–4,600/mo |
| **Tower View** | per-unit grid: last txn **and the app's own Est. Val per unit** — the key benchmark |
| Profitability | matched buy→sell pairs with annualised realised returns |
| Nearby Properties | 6 freehold projects within 200 m with sale psf + avg rental yield |
| Maps / Planning Decisions | location & URA master-plan context (qualitative) |

---

## 3. API gaps found → filled ("发现 api 有欠缺随时开发补全")

The existing bridge assumed a **search → result cards → detail** app (Wikipedia/fixture). The real app is **table-driven with frozen columns and no ids**. Gaps and what was built:

1. **No profile for a real, id-less app.** → `apps/investment_suite.py` using `text`/`xpath` locators; registered in `apps/__init__.py`. Honestly flags the search-field locators as provisional.
2. **No table extraction.** The transaction table has a **frozen left "Contract Date" column**; only swiping the *data* columns scrolls it, and fling momentum makes paging non-deterministic. → `research/harvest_sale.py`: dump → snap each cell to the nearest **header column x-centre** → scroll data region → **dedup + stale-round stop**. App-agnostic technique.
3. **No fast recon / per-coordinate operation.** → `research/mbx.py`: an adb-only harness (`cap` / `tap_text` / `xy` / `swipe` / `region` / `back`) that parses any uiautomator dump to nodes with `text/desc/id/bounds/center/clickable` and saves PNG+XML+JSON per step (auditable, replayable).
4. **No valuation capability.** → `valuation/engine.py`: a transparent comparable-adjustment model (time / floor / size-quantum / unit-type adjustments, similarity weighting, same-line anchor) that generalises to any unit; `dataset.py` (extracted data), `run.py` (apply + advisory), `deliverables/build_report.py` (report generator).

**Recommended next API work** (promote the above into first-class `mobile_bridge` service endpoints): `GET /read_table` (generalised column-snap harvester), `GET /read_tower_grid` (per-unit Est. Val harvester), `GET /compare_developments` (Nearby tab), and a `read_screen` path that falls back to text anchors when resource-ids are absent.

---

## 4. Method & provenance

- **Extraction:** UI automation only. Each read saved a screenshot + UI-dump under `research/captures/` for audit. No app internals were touched.
- **Triangulation:** an external market-research agent corroborated the app's facts (freehold / TOP 2017 / 183 units / D2) and supplied macro & regulatory context (URA index, ABSD/SSD/BSD, financing, the 12 Jul 2026 Cantonment MRT catalyst). Notable cross-check: the app's transaction-based blended rental yield (**2.91%**) is well below optimistic portal aggregates (~4.4%) — the app figure is the more reliable.
- **Model:** documented parameters, not a black box; back-tested on a 1-bed (returned $2,425 psf → S$1.10M, top of the recent 1-bed cluster — well calibrated). Treat the **range**, not the point, as the operative output given thin transaction volume for this layout.

## 5. Team / workflow

Lead (live emulator — a single serialised resource, driven directly) + two background subagents: (a) **market researcher** (web triangulation), (b) **documentation engineer** (skill playbooks from the real source files). Modeling, the bridge profile, and the HTML report were done by the lead for coherence.

## 6. Reproduce

```powershell
# data already captured under research/captures/ ; to re-run the analysis:
.\.venv\Scripts\python valuation\run.py            # model + advisory -> valuation/results.json
.\.venv\Scripts\python deliverables\build_report.py # -> deliverables/*.html
.\.venv\Scripts\python -m pytest -q -W ignore       # Tier-1 suite (unaffected)

# to read the app again (must be logged in, development screen open):
.\.venv\Scripts\python research\mbx.py cap my_screen
.\.venv\Scripts\python research\harvest_sale.py      # harvest the Sale table
```

## 7. Limitations & caveats

- Compact-3BR layout transacts rarely → the subject leans on time-adjusted same-line + adjacent-size comps; the point estimate carries real uncertainty (hence the range).
- Search-field locators in the profile are **provisional** (verify with `dump_ui` on your build).
- The app's per-unit Est. Val is a useful but **undocumented** AVM — used as a benchmark, not ground truth.
- "18 Spottiswoode Park Road" is a *different* development (Spottiswoode 18); the subject is at **16** Spottiswoode Park Road, "#18-03" = floor 18 / stack 03. Confirmed in-app.
- For research/illustration only — not a formal valuation or financial advice.
