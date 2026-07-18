---
name: landed-research-capability
description: "RE_search SG property research: 4 studies done (landed x2, 新盘, condo), OneMap ground-truth tool, hostile-analyst critique loop — and the study-killing geography gotchas"
metadata: 
  node_type: memory
  type: project
  originSessionId: 05a8a0f6-1bf9-4533-9ace-a43bc7336084
---

RE_search runs a **study suite, REBUILT ON TIER-1 (Investment Suite) DATA and all
analyst-PASSED** (2026-07-03): Dunearn House 新盘 PASS 8.9 · Rosyth 1km landed PASS 8.6 ·
Gallop Gables condo PASS 8.55 (model S$2,351 psf / S$4.10m sits INSIDE the app's own 3BR AVM
band S$2,337–2,411 — model↔AVM cross-validated <2%) · Nanyang 1km landed PASS 8.45. Verdicts in
each digest under `review`; Tier-1 datasets + app screen captures under `research/`
(gallop_transactions/towerview/rents/profitability, tier1_comps, tier1_landed_*).
Reports → G:\My Drive\004 RES\REsearch_Reports (see [[re-search-reports-dir]]).

> **UPDATE 2026-07-17 (EXP-0018):** this study went app-only because URA appears to have
> nothing on Cardiff Grove. **It does have it — filed under `ALNWICK ROAD`.** URA's `street`
> is a coarse PARENT/locality label that merges adjacent roads (16 of 17 in-window Cardiff
> sales match an ALNWICK ROAD caveat on month+price+area). So a URA-based cross-check WAS
> available, and `street_not_found` anywhere is a naming failure, not a data gap. See
> [[valuation-research-system]].

**Study #19 — 19 Cardiff Grove landed single-house VALUATION (2026-07-14, PASS 8.5, 2 rounds).**
First landed *unit valuation* (not area study). Subject: 1,839.57sf terrace, Serangoon Garden
Estate D19, **999yr-from-1956** (≈929y left, quasi-FH), original (TOP -), last sold 2023-03
$4.15m/$2,256. **New app technique (landed street comps):** address page → **Sale → Street
scope** shows a by-type SUMMARY (Semi-D/Terrace with a **clickable count link, e.g. "29"**) →
tap the count → full-screen **"Type Summary"** table = ALL that-type caveats (the embedded
street table only previews ~10). Harvested 29 terraces; **completeness gate = harvested-mean
$3,663,164 == app band-avg $3,663,165 (<$1)**. Method (no turn-key pipeline like condos):
land-psf, **quantum elasticity −0.877** (bigger plot→lower psf; total price ≈size-independent,
~$3.5–5m band), recent-regime trend **flat** (2022+ −2.6%/yr R²=0.02 insig; 10Y +7.6% NOT
extrapolated), condition=largest spread (rebuilt/reno comps→ceiling, excluded from base),
recency-weighted same-spec-ORIGINAL grid → point **$2,075psf/S$3,817,000, −8% vs 2023 peak
buy** (freshest 2025 same-spec prints imply −18% downside). Scripts: `research/
cardiff_transactions.json` + `cardiff19_valuation.json`, `deliverables/build_cardiff_report.py`
(RE_search @ffe0aaf). **Review lesson (why R1 REVISE 7.65→R2 PASS 8.5):** don't add the
subject's own stale pre-softening print as a co-equal triangulation leg (it's already in the
grid = double-count + seller anchor); and **separate LEVEL (below 2023 peak) from SLOPE
(statistically flat)** — leading with "trending down" overstates an insignificant slope.
Also: the app-nav went flaky (Property Analysis blank) — `adb am start …MainActivity2` relaunch
fixed it.

**#19 follow-up — the 5-LAYER triangulation the client actually wanted** (Sale tab has 3 scopes:
**Street / Nearby(500m) / District**; scroll a scope's page for a by-type SUMMARY + a
"**Current Listings for Sale**" AGENCY-ASK panel(Tier-2, harvest like a table) + a psf trend
chart; **Market→Landed** tab = SG-wide 大盘 avg psf + trend). Layers: ①subject last txn
②same-street same-spec grid ③nearby-500m comparable ASK ④region/District avg ⑤SG 大盘.
Cardiff: nearby avg $1,810(5Y)/$1,506(10Y all-types), D19 $1,505, SG 大盘 $2,379 (+96%, new
highs); nearest comparable ask = Chuan Terrace 1,798sf $1,947. **Two review lessons (cost R3+R4):**
(a) **don't blend a nearby ASK into the central as a quantitative weight when its transactable
(~$1,850) ≈ the freshest same-street print already dominating the grid — that DOUBLE-COUNTS the
same softness through a second channel** (same class of error as the own-print leg in R1); keep
it as a buyer-range corroboration only. (b) **the SG 大盘 being at new highs vs a segment at
~$1,900 is a CROSS-SECTIONAL mix gap (prime/GCB lifts the islandwide avg), NOT a time-series
"segment lagged" — don't conflate**; the real slope evidence is the street's own regression.
Net: adding the layers CONFIRMED the same-street point ($2,075/-8%), didn't move it. R4 PASS 8.8.
See [[condo-valuation-pipeline]], [[data-source-trust-hierarchy]].

**The Tier-1 redo's two killer findings (why [[data-source-trust-hierarchy]] exists):**
- propertyforsale.com.sg's "Jun-2026 Alnwick four-deal cluster (S$1,571–2,815)" — which the
  web-era Rosyth report used as its freshest benchmark — is ABSENT from official caveats:
  the street's 2Y file has exactly TWO deals (Oct-2025: rebuilt detached $2,099 vs same-month
  original semi-D $1,512 = +39% for rebuild state). Aggregator transactions = claims until app-verified.
- 1 Kingsmead Rd (12,168 sqft, same size as the S$24m "24 Kingsmead" listing) transacted
  2026-03-30 at $21.998m / $1,808 psf — flipping that listing's web-era "VALUE" call to
  NEGOTIATE (ask +9% over print, possibly the same lot already sold).

**Tools** (all tested; `python -m pytest tests` in RE_search, 42+ tests):
- `researcher/sources/onemap.py` — public OneMap Search API geocode + haversine + `ring_check`
  (margin classification, 429 backoff, apostrophe sanitization: "KING'S ROAD" finds NOTHING,
  "KINGS ROAD" works). CLI: `python -m researcher.sources.onemap "<street>" --anchor "<school>"`.
- `researcher/landed/screen.py` — `rank_listings()` + `screen_verdict()` (quality × value
  band × data completeness; unknown tenure/flood/land ⇒ VERIFY DATA, never PURSUE).
- `deliverables/build_landed_report.py <slug>` / `build_newlaunch_report.py <slug>` /
  `build_condo_report.py <slug>` (generic; build_report.py is the Spottiswoode one-off) —
  all take asof from digest, have mojibake gates, embed ranked-listings/adjustment-grid tables.
- Skill **`property-report-review`** — hostile-analyst acceptance loop (6-dim rubric, weighted
  ≥8.0 + no dim <6 + zero blockers = PASS; FRESH reviewer agent each round; reviewer spot-checks
  3 load-bearing numbers on live web). Typical convergence: 7.3 → 7.85 → 8.1 → PASS 8.3.

**Study-killing gotchas (cost real rounds):**
- **Geography must be OneMap-measured, never assumed.** Rosyth's headline finding: Serangoon
  Gardens core is 1.36–2.04km from the school (it moved OFF Rosyth Rd in 1984→Parry Ave→2001
  Serangoon North Ave 4); research agents' coordinate guesses were off by ~1km. Nanyang: Prince
  of Wales Rd is 0.27km (v1 said "0.9–1.0km edge"); Coronation Rd West street-ref 1.47km = OUT.
- Street-reference-point ≠ house number — long streets need per-address re-checks; report "margin".
- Analyst blockers cluster in: double-encoded UTF-8 from PowerShell-written JSON (repair =
  s.encode('cp1252').decode('utf-8')), stale pre-correction sentences surviving in OTHER sections
  after a data fix (sweep summary+recs+listings notes together), internal revision jargon
  ("v1", "this pass", "403") in client-facing text, and untraceable benchmark bounds
  (every band edge must cite a listing ID or transaction; never mix built-up psf into land-psf bands).
- Digest vocab must map to scorecard vocab (`normalize()` aliases rebuilt_new/mid/999_yr/unverified).
- GEP is DISCONTINUED (last P4 intake 2026; HAL + 15 Advanced-Module centres from 2027) — every
  school-premium thesis must be re-based on SAP brand + balloting scarcity. See [[kelvin-user]].
