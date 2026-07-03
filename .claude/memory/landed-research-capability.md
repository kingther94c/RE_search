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
