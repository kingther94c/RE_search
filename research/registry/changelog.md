# Model & skill changelog

Newest first. Every material methodology/skill change: what · why · evidence · backtest
impact · assets affected.

---

## 2026-07-17 — L2b SHIPPED: observed local-trend bridge in the landed time adjustment (EXP-0016/0017)
- **What:** LV1's time adjustment is now published-PPI-to-last-published-quarter **× an
  OBSERVED bridge** from max(comp month, quarter midpoint) to the newest visible caveat
  month — `local_trend.py`, an as-of two-way-FE monthly curve (ln psf ~ (street,type) +
  month), 3-mo median smoothed, clamped, **never extrapolated**. One constructor
  (`landed_engine.shipped_time_ctx`) feeds production, the harness default and the tests.
  Conformal recalibrated; fingerprint extended to the FULL residual-determining file set
  (the old 2-file set had a hole exactly where L2b operates). Guidance marker rates
  re-measured under the shipped adjustment. Fable-review fixes in the same change: dead
  `drift_factor` deleted from `index.py`, guidance/exhibit pools aligned to LC2's 60mo
  window, `analyze_landed` A5 now scored through production `_band`.
- **Why:** EXP-0016 refuted the cap hypothesis by measurement and located the regime bias
  in publication staleness (~4.5mo) × market pace; GY-0003 already proved forecasts break
  stable regimes — only an OBSERVATION can close the gap.
- **Evidence:** walk-forward n=7,027 — median APE **9.34→9.05%**, hot-regime sign test
  **66.3/66.5/60.4 → 60.8/62.1/59.6**, stable regimes 47.1-53.0 (unharmed), lag-stable,
  bar cleared same-adjustment (LC1 10.45%), conformal held-out **78.9%** via production
  band code. Pre-registered "fixed" bar (all regimes ∈[42,58]) **NOT met → the regime-bias
  disclosure stays**, updated. Field catch: the first bridge double-counted fresh comps
  (a subject's own same-month print +4%) — found on BOWMONT GARDENS live, fixed as the
  per-comp anchor, regression-locked. 158 tests.
- **Backtest impact:** all landed methods share `_tadj_psf`, so LB/LC/LA rows all move;
  the leaderboard stays internally consistent. Condo untouched.
- **Assets affected:** landed only. GY-0004 (cap widening), GY-0005 (lt_full) buried.

## 2026-07-16 — L1 landed baseline DONE — GL1 PASS: bar 10.5%, floor ~5.5-6% (EXP-0010)
- **What:** the honest landed leaderboard (LB1-LB5 + LC1 craft port, walk-forward over
  7,027 resale pure-landed subjects, lag-stable) + the same-plot NOISE-FLOOR study.
  **THE LANDED BAR = LC1_craft_landed 10.51% median APE @ 87.3% coverage** (the Cardiff
  same-street grid skeleton with the ported area^-0.877 size prior); best tail = LB4
  spatial kNN (p90 0.310). **Noise floor: ~5.3-6.2% per print** — only ~4-5pp of the bar
  is closable; landed honest accuracy is structurally high-single-digit (vs condo 3.7%).
- **Why:** roadmap L1 — evidence sets the bar and selects L2 modules; nothing fitted.
- **Key findings:** error explodes monotonically in plot size (8.8% at 1.5-3k sqft →
  41% at 15k+); cross-street kNN prices short-lease terraces off freehold neighbours at
  6-10× (sub-2M slice median APE 232%) → **remaining-lease control mandatory for every
  cross-street method**; even 1-2 same-street comps beat all cross-street pools (the
  condo thin-comp reversal transposed); comp-IQR intervals broken (38-50% coverage) as
  expected. L2 opens: L2a size curve (mandatory), L2c retrieval+lease-matching, L2d
  anchors (coverage only), L2b time-adj (cheap), L2e bounds; Detached ≥8k sqft / GCB →
  case-tier scope. Detail + memo in EXP-0010.
- **Assets affected:** landed (L2 unblocked). 125 tests.

## 2026-07-16 — L0 landed data foundation DONE — GL0 PASS (EXP-0009)
- **What:** the L-track's data spine. `store.is_pure_landed()` (Land + exact landed type;
  strata-landed routed out; Apartment+Land walk-ups excluded), `LANDED_PSF_BAND [100,
  6500]` (cuts 0 — both extremes verified real: 107 psf short-lease / 5,756 psf Emerald
  Hill), `subjects(kind='pure-landed')` with land-area defaults, MarketView landed
  support (street index + spatial grid), **same-plot matcher** `landed_pairs.py` (5
  anti-collision rules) → **685 plots / 850 repeat pairs / 395 with gap ≤18mo**, and
  `research/audit_landed.py` with the GL0 gate (re-runnable, --json). 123 tests (+4).
- **Why:** roadmap L0 — no landed research is trustworthy before hygiene + measurement.
- **Evidence:** GL0 PASS — 10,789 pure-landed resale subjects (≥10k), 61 months (≥48),
  band from data, matcher hand-spot-check 24/25 plausible (the 1 miss motivated matcher
  rule 5, which removes its class: ≥2-New-Sale mirror-unit keys). Open finding carried
  to L1: 21.4% exact-copy row involvement (real-vs-double-entry unresolvable from URA;
  liquidity counts carry the bound).
- **Assets affected:** landed (L1 unblocked: honest leaderboard + noise-floor study).

## 2026-07-16 — Fable review round 2: LIVE valuations now see the current partial month
- **What:** `value_unit.value` LIVE mode gates at month granularity (`contract_ym <=
  asof month`) instead of running the backtest's month-END visibility convention with
  lag 0 — which was still hiding every current-month print from a live valuation (205
  July-2026 caveats invisible on 2026-07-16). Reconstruction mode unchanged (month-end +
  56d, day-granular). Also re-synced `.agents/` screen-landed-listings SKILL.md (stale
  "Codex-in-Chrome" wording). EXP-0008 addendum; 119 tests (+2 as-of regression tests).
- **Why:** EXP-0008 fix #1's stated semantics ("the pulled store IS the information
  set") were only partially implemented — month-end gating is a leakage guard for
  backtests, not a fact about what a live valuer knows.
- **Backtest impact:** none (backtest path untouched; C1 residuals unchanged, conformal
  fingerprint intact). Live production estimates now use the freshest prints.
- **Assets affected:** condo (live skill path only). Landed L0 starts next.

## 2026-07-16 — Roadmap v2: LANDED-FIRST re-plan (L0–L4)
- **What:** `01_roadmap.md` rewritten as v2. The one-section R6 became a full delivery
  track: **L0 data foundation (hygiene, land-psf band from data, same-plot matcher) → L1
  baseline leaderboard + NOISE-FLOOR study (the bundle-identification bound) → L2
  error-driven modules (land-size curve expected mandatory; time-adj; retrieval/pooling;
  anchors with the condo-reversal expectation preset; improvement-contribution bounds) →
  L3 engine LV1 + conformal (fingerprinted from day one) + condition-input hook → L4 skill
  ship (regression suite, ≥3 field trials incl. Cardiff Grove #19 cross-check, fresh-
  reviewer hostile loop to PASS ≥8)**. Est. 4.5–6 sessions. Condo R0–R5 sections condensed
  (results live in the registry); R4/R7 preserved as parked plans; guardrails unchanged +
  landed-specific honest limits (bundle noise, geometry blindness, GCB scope).
- **Why:** user decision — landed must land first; v1's condo-first structure no longer
  described the program. Condo lessons are baked into the L-track as presets (G1 criteria
  = median+tail+coverage+calibration; anchors buy coverage not points; live-lag semantics;
  fingerprint discipline) so they are not re-learned at landed prices.
- **Assets affected:** landed (active), condo/new-launch (frozen, unchanged).

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
