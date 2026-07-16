# Model & skill changelog

Newest first. Every material methodology/skill change: what · why · evidence · backtest
impact · assets affected.

---

## 2026-07-16 — Fable review round + PRIORITY PIVOT: landed first (R6 active)
- **What:** post-ship review of R0–R5 (EXP-0008). Applied the safe fixes: live-vs-
  reconstruction as-of semantics (live valuations no longer discard the freshest ~2 months),
  day-granular reconstruction, fallback band widened to the anchor's own coverage-swept band
  (the conformal table is C1-calibrated and under-covers on fallback), conformal↔code sha1
  fingerprint + red-test guard, smooth confidence depth curve. 117 tests.
- **Deferred to the condo backlog** (require recalibration; condo frozen): FLOOR_PP 0.004
  (re-fit, 4,415 pairs) and CCR elasticity −0.016. Fit scripts + numbers in EXP-0008.
- **PIVOT (user decision):** LANDED valuation is now the priority; condo + new-launch pause
  to the backlog. Roadmap updated: status table for R0–R8, condo backlog, and an R6 kickoff
  grounded in measured data reality (12,115 resale landed subjects; street median = 5
  caveats/5y → partial pooling mandatory; Land vs strata-landed split; land-psf semantics).
- **Assets affected:** condo (frozen, safer), landed (active next).

## 2026-07-16 — R5 SHIPPED: condo-resale-valuation skill, hostile review PASS 8.7/10 (G5 MET)
- **What:** the skill is production-accepted. 4 hostile-review rounds (6.6 → 7.6 → 7.6 →
  **8.7 PASS**), each fix re-verified by reproduction. Final polish: smooth confidence in
  anchor disagreement (no cliff) + mild-divergence label.
- **Why:** G5 ship bar = beat benchmarks + regression suite + field-trial hostile PASS ≥8 +
  interval calibration holds. All met (8.7, every dimension ≥8.0, zero blockers).
- **What ships:** `condo-resale-valuation` SKILL.md, `value_unit.py` (valuation + confidence
  + guidance + hard-case honesty), engine v2.1, `build_condo_v2_report.py`,
  `tests/test_value_unit.py` regression suite; value-a-property superseded.
- **Backlog (non-blocking):** re-fit FLOOR_PP; smooth comp-depth confidence tiers; as-of day
  granularity; the R4 Investment-Suite enrichment bridge. 116 tests.

## 2026-07-16 — R5 hostile-review revision: engine v2.1 (size/time fixes), EXP-0007
- **What:** re-fit size elasticity on URA (`research/fit_elasticity.py`, segment-specific);
  C1 size-gating + heavier size penalty + recency + time-quality weighting + time-adj cap;
  hard-case honesty in value_unit (recent-same-size reference, directional flag, band widen,
  conf cap, lease-aware fallback); SKILL.md IS-overclaim downgraded; report warning banner.
- **Why:** the R5 acceptance reviewer (REVISE 6.6) blocked on the ported −0.08 elasticity
  letting a shoebox value a large unit (The Foliage). A real guardrail-#5 violation.
- **Result:** the fixes IMPROVED the population — **C1 median 4.10%→3.68%, V2 3.71%**,
  conformal recalibrated (85%/0.185 width), every slice better. The Foliage now conf 55 +
  directional "12% above fresh print" + widened band — honest, not misleading. 116 tests.
- **Backtest impact:** engine got materially better AND more honest from the hostile review.
  Resubmitting to a fresh reviewer.

## 2026-07-16 — R3-finish: engine v2 FINAL (V2 = C1 + fallback + conformal), G3 MET
- **What:** `engine_v2.py` (V2), `conformal_table.json` (split-conformal, 85% nominal),
  `research/analyze_r3.py` (thin-comp matrix + conformal calibration/validation), E3
  3-anchor blend, run.py `--dump`. EXP-0006. 109 tests (+1).
- **Why:** close the 3 R3-finish items (conformal, 3-anchor, E1-vs-E2 on thin comps).
- **Reversal finding:** blending anchors into C1 HURTS the point everywhere same-project
  data exists — even 1-2 comps (C1 4.84% vs blends 5.1-5.8%). Anchors buy coverage +
  intervals, not point accuracy. So v2 dropped the blend for "C1 point + anchor fallback +
  conformal band".
- **Result — engine v2 = V2:** median **4.09%** / coverage **100%** / interval **82.7%**
  (conformal held-out 82.0%, width 0.197 — ~30-57% sharper than the E-series union band).
  Ties C1 on median (no anchor drag), beats E2/E3 (4.16%). **G3 MET.**
- **Superseded:** E0/E1/E2/E3 (kept as record). **Backtest impact:** first shippable condo
  engine — best point + honest calibrated bands + full coverage. Next: R4 (IS calibration)
  or R5 (condo skill).

## 2026-07-16 — R3 engine v2: team fan-out integrated + verified (G3 MET)
- **What:** integrated 3 team-built methods (`avm_pooled.py` A2, `avm_knn.py` A3,
  `ensemble_learned.py` E1) + a follow-up E2 (C1⊕A2) + `tune_e1.py` provenance. All
  independently re-verified in the main repo (numbers reproduce; leakage read clean). 108
  tests (+7). EXP-0005.
- **Why:** the R3 team (Workflow wf_234bc499-6eb) built alt anchors + a learned ensemble;
  the workflow died at the session boundary before its verify/synthesis tail, so the
  orchestrator re-verified from the journal + reproduction rather than trusting completion.
- **Result — engine v2 = E2_ensemble_pooled:** median 4.16% / 100% coverage / interval 87%.
  Ties the C1 bar (4.08%) while fixing interval calibration (43%→87%) and always answering —
  **G3 MET** (tie + better calibration). A2 pooled (5.46%) is the best independent anchor;
  E0 superseded by E1/E2.
- **Backtest impact:** first production-grade condo estimate — honest bands + full coverage.
- **Open (R3-finish):** per-cell conformal to sharpen intervals to exactly 80%; 3-anchor
  blend; E1-vs-E2 re-check on a thin-comp slice (the case the backtest under-weights).

## 2026-07-15 — R0 complete + R1 baseline (condo) + G0/G1 gates
- **What:** full URA pull (136,436 caveats, 61 months, EXP-0002, G0 PASS); harness
  performance refactor (`market.py` MarketView per-month indexes — dropped the per-subject
  O(n) copy, 61k subjects now tractable); data-hygiene filters (bulk/psf-band); C1 grid
  candidate (`candidates.py`) porting value-a-property to URA; first walk-forward
  leaderboard + slice panel (EXP-0003); GY-0001 (segment-avg) + GY-0002 (nearest-project)
  buried with numbers.
- **Why:** turn the harness into real numbers and let evidence set the bar and the next phase.
- **Findings:** bar = **4.1% median APE** (C1 grid ties B3, marginally beats naive
  same-project median); segment/nearest proxies 3-4x worse; medians flat across all slices
  but TAIL and interval calibration are the real defects.
- **G1 decision:** median rule opens no R2 module → pull R2d (AVM anchor) into R3 and make
  R3 = independent AVM anchor + conformal intervals + evidence-state ensemble; defer
  R2a/b/c bake-offs unless R3 leaves a gap. Rationale in EXP-0003.
- **Backtest impact:** establishes the number every future method is measured against.
- **Real-data robustness:** cp1252 decode fix, landed-spelling fix, EC exclusion.

## 2026-07-15 — Program roadmap v1 (R0–R8), planned on Fable 5
- **What:** `01_roadmap.md` — nine gate-driven phases from data-foundation completion to
  the three production skills + operations, with per-phase research directions, plans,
  guardrails, deliverables and kill/pivot gates; 10 cross-cutting guardrails; a
  disposition table for all 11 existing skills; a mandate coverage map.
- **Why:** the mandate is a full quant research programme; ungated it is a 100+ method-
  grid. The roadmap makes complexity error-driven (G1 opens bake-offs only where the
  benchmark bar is exceeded by 1.5×), splits validation protocols per asset, and
  elevates the IS guided-harvest rewrite to a first-class work-line (R4).
- **Notable position changes:** new-launch premium persistence and developer price
  ladders are directly backtestable from URA new-sale caveats within the 5y window
  (upgrade from "mostly case-based"); official rental evidence via URA's rental service
  joins R3; clean repeat-sales confirmed impossible on URA (no unit ids) → IS realised
  pairs carry that load (R4).
- **Backtest impact:** none yet — R0 (full pull + audit) is the next action.
- **Assets affected:** all three programmes.

## 2026-07-15 — Module 0: URA data spine + walk-forward backtest harness
- **What:** new `researcher/sources/ura.py` (URA private-residential caveat client +
  offline-testable `normalize`), `researcher/backtest/` (`store` as-of firewall, `index`
  time-adjustment with publication lag, `metrics`, `benchmarks` B1–B5, `harness`
  walk-forward, `run` CLI), research registry scaffold, 13 tests.
- **Why:** the mandate's mandatory time-consistent out-of-sample validation was impossible on
  the previous per-property UI-scrape architecture — there was no replayable, as-of-queryable
  transaction base. This builds it. Decision on record: URA = backtest base + baseline;
  Investment Suite = calibration + live production Tier-1.
- **Evidence:** 98/98 tests pass; the load-bearing `test_as_of_excludes_future` proves the
  leakage firewall. Real backtest numbers **pending the first URA pull** (needs `URA_ACCESS_KEY`).
- **Backtest impact:** n/a yet — establishes the mechanism to produce it.
- **Assets affected:** condo resale first (per sequencing decision); harness reused for
  landed / new-launch later.
