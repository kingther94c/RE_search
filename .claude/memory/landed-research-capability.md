---
name: landed-research-capability
description: "RE_search SG property research: 4 studies done (landed x2, 新盘, condo), OneMap ground-truth tool, hostile-analyst critique loop — and the study-killing geography gotchas"
metadata: 
  node_type: memory
  type: project
  originSessionId: 05a8a0f6-1bf9-4533-9ace-a43bc7336084
---

RE_search runs a **study suite, all analyst-PASSED** (2026-07-03): Nanyang Primary 1km landed
(PASS 8.3, 4 rounds), Rosyth 1km landed (PASS 8.4, 4 rounds), Dunearn House 新盘 (Turf City
first launch, SELECTIVE 70/100; PASS 8.45, 2 rounds), Gallop Gables condo (in-ring alternative,
S$2,346 psf / S$4.09m, stable band 2,243–2,346; PASS 8.7, 5 rounds). Verdicts + scores recorded
in each digest under `review`. Reports → G:\My Drive\004 RES\REsearch_Reports
(see [[re-search-reports-dir]]).

**Tools** (all tested; `python -m pytest tests` in RE_search, 42+ tests):
- `researcher/sources/onemap.py` — public OneMap Search API geocode + haversine + `ring_check`
  (margin classification, 429 backoff, apostrophe sanitization: "KING'S ROAD" finds NOTHING,
  "KINGS ROAD" works). CLI: `python -m researcher.sources.onemap "<street>" --anchor "<school>"`.
- `researcher/sources/propertyguru.py` — `rank_listings()` + `screen_verdict()` (quality × value
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
