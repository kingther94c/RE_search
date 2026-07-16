# Experiment registry

Newest first. One row per experiment; link to code/commit. Verdict vocabulary in
[`README.md`](README.md).

---

## EXP-0009 — L0 landed data foundation: hygiene, land-psf band, same-plot matcher (2026-07-16)
- **Status: DONE. GL0 GATE: PASS** (`research/audit_landed.py` — re-runnable, `--json`
  machine-readable, `--pairs` prints the spot-check artifact).
- **Slice (2026-07-15 snapshot):** landed universe 12,990 = **pure-landed 11,344**
  (post-hygiene: Terrace 6,033 / Semi-D 3,693 / Detached 1,585; OCR 7,584 / RCR 2,303 /
  CCR 1,424; FH 7,961 / 999yr 1,723 / LH 1,627) + **strata-landed 1,629 ROUTED OUT**
  (orphaned sub-market — neither engine values it; condo backlog #4) + **17 stray
  Apartment+Land rows EXCLUDED** (walk-up / whole-building deals under placeholder
  projects like 'RESIDENTIAL APARTMENTS'; 15 after bulk — the roadmap's "15 stray rows"
  reconciled). **Rule R1: pure-landed requires BOTH type_of_area='Land' AND exact type in
  {Terrace, Semi-detached, Detached}.**
- **Land-psf band (R3):** `LANDED_PSF_BAND = [100, 6500]`, cuts **0 rows** — deliberate:
  BOTH extremes verified REAL (p0 = 107 psf = 70-yr-lease-from-1964 terrace with ~8 years
  left, Jalan Chempaka Kuning; p100 = 5,756 psf = Emerald Hill conservation terrace), and
  psf<700 is 81% leasehold — a genuine decaying-lease sub-market the band must NOT trim.
  The band wraps the verified range as a future-junk guard (percentile method, condo
  analogue [500, 6500] which does cut errors).
- **Exact-copy finding (OPEN, measured not resolved):** 21.4% of pure-landed rows sit in
  same-(street, exact-area, month, price) copies; 95% Resale; **zero normalized-id
  collisions → NOT pull/batch overlap — URA itself lists them as separate entries.**
  Twin-pair sales vs registry double-entry is unresolvable from URA alone. Decision:
  keep in store (condo cross-check: its 4.4% same-key rate is launch-batch pricing =
  real units, so global dedup is wrong), collapse inside the matcher (dt=0 carries no
  signal either way), and carry the documented ≤~21% overstatement bound on
  street-liquidity counts into L1.
- **Same-plot matcher** (`researcher/backtest/landed_pairs.py`): key = (street, exact
  area_sqm, property_type) + 5 rules — dedup dt=0 copies; >4 trades/key = development
  collision; same-month different-price = twin plots; **≥2 New Sales = mirror units (18
  keys / 21 New→New pairs killed — 20 of them would have contaminated the ≤18mo
  noise-floor fuel)**; Resale→New Sale KEPT deliberately (real redevelopment pairs, n=5,
  the L2e signal). Consecutive-trade pairs only (one holding period each).
- **Result:** **685 plots → 850 pairs; 395 with gap ≤18mo** (L1 noise-floor fuel);
  annualized p50 **+7.6%** (plausible for the 2021-26 landed run); wild movers (>|30/60%|
  ann.) 7.8% = rebuild signatures, surfaced not filtered.
- **Spot-check (by hand, seed 7, 25 pairs):** **24/25 structurally plausible** (gate bar
  ≥80%); the 1 miss — JALAN GRISEK New→New mirror pair — motivated rule 5, which removes
  its whole class. 3 pairs carry clear rebuild signatures (Alnwick 350sqm ×1.93/27mo,
  Jalan Chegar ×2.08/16mo, Joo Chiat ×1.82/21mo): same-plot-plausible AND exactly what
  L2e wants to detect.
- **Infra landed (all tested):** `store.is_pure_landed()/is_strata_landed()` +
  `PURE_LANDED_TYPES`/`LANDED_PSF_BAND`; `subjects(kind='pure-landed')` with LAND-area
  defaults 400..150,000 sqft (measured p0.1=883 / p99.9=27,909 — guards, not filters);
  `MarketView.landed()/landed_on_street()/landed_near()` (street index newest-first +
  own spatial grid); harness rows keep street/type_of_area for L1 slicing. 123 tests (+4).
- **GL0:** subjects 10,789 ≥10k ✓ | months 61 ≥48 ✓ | band set from data ✓ | pairs 850
  ≥500 ✓ | noise-floor fuel 395 ≥300 ✓ | rules documented (R1–R5) ✓ → **PASS. L1 (honest
  leaderboard + noise floor) unblocked.**

## EXP-0008 — Fable review round: production-semantics fixes + deferred re-fits (2026-07-16)
- **ADDENDUM (review round 2, 2026-07-16):** the applied fix #1 was itself incomplete —
  "live = lag 0" still ran `as_of`'s month-END visibility convention, so a LIVE valuation
  hid the current partial month's prints (measured: 205 July-2026 caveats in the 07-15
  snapshot invisible on 07-16; TREASURE had 2). Fixed: LIVE mode now gates at month
  granularity only (`contract_ym <= asof month` — drops future-dated data errors, keeps
  the partial month); reconstruction unchanged. Verified: TREASURE live n_comps 140→141
  (the 1,033 sqft July print enters; the 592 sqft one is correctly size-gated out).
  +2 regression tests (live sees current month; reconstruction still excludes). 119 tests.
- **Trigger:** post-ship Fable review of R0–R5. Found 2 real defects beyond the 4 hostile
  rounds, plus closed 3 recurring reviewer P2/P3s. **Mid-round the user pivoted priority to
  LANDED** — so fixes that change C1's residual distribution were fitted, recorded, and
  **deferred** (they require a recalibration run; condo is frozen).
- **APPLIED (safe — do not touch C1 residuals; 117 tests green):**
  1. **Live-vs-reconstruction as-of semantics** (`value_unit.value`): a LIVE valuation (no
     asof) now uses lag_days=0 — the freshly pulled store IS the information set; the old
     blanket 56d lag silently discarded the freshest ~2 months of prints (the most valuable
     evidence). An explicit past asof = reconstruction mode (56d, now DAY-granular, closing
     the month-end coarsening P3). Verified: Treasure live n=140 vs 7/1-reconstruction n=133.
  2. **Fallback band under-coverage fix** (`engine_v2`): the conformal table is calibrated on
     C1 residuals (~3.7% median) but was wrapped around fallback-anchor points (5.5–10%
     error) — and the "0|seg" cell doesn't even exist (C1 rows always have n>=1). Fallback now
     uses the WIDEST of the anchor's own coverage-swept band and the conformal cell.
  3. **Conformal↔code fingerprint**: `analyze_r3.py` stamps sha1(candidates.py) into the
     table; `test_conformal_table_matches_current_c1` turns silent drift into a red test.
  4. **Smooth confidence depth curve** (90 − 45·e^(−n/6)) — no more 7-vs-8-comp 9-point jump.
- **FITTED BUT DEFERRED (condo backlog — apply when condo resumes):**
  - **FLOOR_PP 0.003 → 0.004** (`research/fit_floor_premium.py`: 4,415 same-project
    near-simultaneous size-similar cross-band pairs; global +0.40%/floor, CCR +0.41 /
    RCR +0.37 / OCR +0.46). The last ported constant, now measured.
  - **CCR elasticity −0.02 → −0.016** (align to the EXP-0007 fit).
  - Apply = edit candidates.py, then `run --sample 8000 --dump` → `analyze_r3.py` (recalibrate
    + re-fingerprint) → verify leaderboard didn't regress → update SKILL numbers.
- **Also verified in review:** `_infer` uses the full store deliberately (static attrs only,
  never price — no leakage); `_wquantile`/comp-ranking correct; report renderer consistent.

## EXP-0007 — R5 hostile-review revision: size/time fixes → engine v2.1 (2026-07-16)
- **Trigger:** the R5 acceptance reviewer (REVISE 6.6) blocked on a real defect — the ported
  `SIZE_ELASTICITY=-0.08` was never re-fit on URA, and a 505sf shoebox was setting an 1100sf
  unit's value (The Foliage: point 1716 vs freshest same-size print 1488). Guardrail-#5
  violation (unvalidated constant). Fixed properly, not patched.
- **Elasticity re-fit** (`research/fit_elasticity.py`, 12,638 same-project near-simultaneous
  pairs): global median **−0.068** (≈ the old −0.08 — the reviewer over-generalized from one
  project), but **segment-varying: CCR −0.02, RCR −0.08, OCR −0.09**. Now segment-specific.
- **C1 fixes (all re-backtested):** (a) size-gating — prefer same-project comps within ±35%
  size, so a shoebox can't set a large unit's median; (b) heavier size penalty (×5); (c)
  stronger recency (dmonths/15) + a time-adjustment-QUALITY penalty (a stale comp needing a
  big index adjustment is down-weighted); (d) time-adjustment cap [0.80, 1.25].
- **Result: the fixes IMPROVED the whole population, not just the edge case** —
  **C1 median 4.10% → 3.68%**, V2 3.71% / 100% cover / conformal recalibrated to ~82-85%
  held-out (85% nominal) / width 0.185. Every segment/tenure/regime slice improved.
  pct>10% 15.4%→12.8%. (Headline the conservative ~82% from EXP-0006 held-out.)
- **Hard-case honesty (value_unit):** surface the freshest same-size print as
  `recent_same_size_reference`; a **directional flag** when the point sits >5% above it
  ("possibly optimistic on stale comps — corroborate"); widen the band down to that reference
  on hard cases; hard-case confidence cap 62→55; lease-aware fallback order (A1 first for
  leasehold); SKILL.md IS-corroboration downgraded from "automated" to a manual to-do.
- **The Foliage after fixes:** point 1710 (defensible from the comps), but now conf 55,
  band widened to 1680 (= the fresh reference), directional flag "12% above the 1527 fresh
  print", verify-before-offer says pull IS comps. Honest, not misleading.
- **Round-2 fresh review: REVISE 7.6, ZERO blocking issues** (up from 6.6 + 2 blockers —
  prior blockers confirmed closed). Two P1s fixed to cross the 8.0 PASS bar: (P1a) on a
  directional hard case the POINT is now pulled toward the fresh same-size print
  (median blend) + band rescaled — The Foliage 1710→1619 (was +12% over the 1528 fresh ref,
  now +6%); (P1b) SKILL.md/docstring numbers reconciled to v2.1 (3.7% / ~82% held-out, 85%
  nominal / segment elasticity); (P3) the recent-ref is now size-adjusted so the directional check is
  apples-to-apples (Stirling correctly 4.2% < trigger).
- **Known refinements (backlog, non-blocking — R5-follow / R8):** re-fit FLOOR_PP=0.003
  (still a ported constant, guardrail-#5); within-project lease-decay term for short-lease
  projects; conformal table point-method fingerprint + a 3rd split for nominal selection.
- **Verdict:** engine v2.1 ACCEPT. **R5 SHIPPED — hostile acceptance review PASS 8.7/10**
  (round 4; every dimension ≥8.0, zero blockers). Rounds: 6.6 (2 blockers: unvalidated
  elasticity) → 7.6 (0 blockers, point-vs-fresh-print) → 7.6 (doc coverage inconsistency) →
  **8.7 PASS**. Reviewer independently reproduced all field trials byte-for-byte, the
  elasticity fit, ~84% held-out conformal, and the leakage firewall. G5 MET. Remaining P2/P3
  are polish (FLOOR_PP re-fit, base-tier smoothing, as-of day granularity) — backlog. 116 tests.

## EXP-0006 — R3-finish: thin-comp reversal, 3-anchor blend, conformal → engine v2 (2026-07-16)
- **Status:** DONE. **G3 MET, cleanly.** Engine v2 = `engine_v2.py` (V2).
- **① Thin-comp reversal (the important finding).** Sliced every method by same-project comp
  count. Even at **1-2 comps**, plain **C1 is BEST (4.84%)**; blending in an anchor makes it
  WORSE (E2 5.08%, E3 5.57%, E1 5.81%). The anchors (5-15% APE cross-project) never beat even
  a 1-2-comp same-project read. **This REVERSES the R3-kickoff hypothesis** that anchors help
  thin-comp point estimates: they help COVERAGE (the ~0.6% no-same-project cases) and
  INTERVALS, not the point. Blending down-weights C1 exactly where it shouldn't.
- **② 3-anchor blend E3** (C1 ⊕ median(A1,A2,A3)): median 4.16%, tail marginally best of the
  blends, but union band over-covers (94%). Same lesson — no point-accuracy gain over C1.
- **③ Conformal intervals** (`research/analyze_r3.py`, split by time: cal<2025-01,
  test>=2025-01, per liquidity×segment cell, 85% nominal chosen by sweep): **coverage 82.0%,
  width 0.197 held-out** vs C1's own IQR band (43%, far too narrow) and the E-series union
  band (86-94%, too wide). ~30-57% sharper than union at target coverage.
- **Engine v2 = V2** (`engine_v2.py`): **C1 point wherever it answers, else anchor fallback
  (A2→A3→A1), + conformal band.** Backtest: **median 4.09% / coverage 100% / interval 82.7%
  / P90 12.6% / pct>10% 16.0%.** Ties C1 on median (no anchor drag), beats every blend
  (E2/E3 4.16%), fixes C1's coverage (99.3→100%) and calibration (43→83%).
- **Verdict:** V2 ACCEPT (engine v2). **E0/E1/E2/E3 SUPERSEDED** — necessary experiments that
  proved the blend doesn't help the point; kept as code + registry record, not shipped. A1/A2/A3
  retained as fallback + (future) interval inputs. Conformal table `conformal_table.json` shipped.
- **Simplicity win (mandate):** the evidence killed the more complex ensembles in favour of
  "best method where it applies + fallback + calibrated band." Complexity was not free — it hurt.
- **Leakage sign-off:** conformal calibration STRICTLY precedes its evaluation slice (time
  split); table is a fixed lookup at inference; V2 reads only as-of C1/anchors. Clean.

## EXP-0005 — R3 team fan-out: alt anchors + learned ensemble (2026-07-15/16)
- **Status:** DONE for 3 of 4 threads; **independently re-verified in the main repo** (numbers
  reproduce exactly; I read every method for leakage — all clean). Conformal thread did not
  finish (workflow died at the session boundary) — carried to R3-finish.
- **Method:** background Workflow (wf_234bc499-6eb) — 4 worktree-isolated agents each built +
  backtested a method; adversarial verify stage started but did not complete, so I did the
  verification myself (code read + full-backtest reproduction at n=4000/5000).
- **Results (verified, sorted best-first):**
  - **E2_ensemble_pooled (C1+A2)**: median **4.16%** / P90 12.7% / cover 100% / **interval 87%** / pct>10% 16.0%
  - **E1_ensemble_learned (C1+A1)**: median **4.18%** / P90 12.7% / cover 100% / **interval 81%** / pct>10% 16.3%
  - E0_ensemble (hand-set): 4.42% / interval 81%  (SUPERSEDED by E1/E2)
  - **A2_avm_pooled** (empirical-Bayes shrinkage, project→segment→broad): median **5.46%** / cover 100% — best independent anchor
  - **A3_avm_knn** (feature-space kNN, k=40): median **7.2%** / cover 100%
  - A1_avm_hedonic: 10.3% (weakest anchor)
- **Findings.** (1) A learned/tuned ensemble recovers the median to ~C1 (4.08%) while keeping
  100% coverage and fixing interval calibration to the 80% target — **E1/E2 meet G3** on the
  "tie within noise + materially better calibration (43%→81-87%)" branch. (2) The pooled
  anchor A2 (5.46%) >> hedonic A1 (10.3%): shrinking same-project psf toward a market prior
  beats regressing on hedonic attributes for this data. (3) Swapping A2 for A1 in the ensemble
  (E2) marginally wins in-sample (4.16 vs 4.18, better tail + calibration).
- **Honest nuance (the synthesis judgement).** E1 vs E2 are within noise. E2 is marginally
  better *in-sample* but A2 is same-project-CORRELATED (it uses same-project comps), so E2 is
  less genuine anchor-diversity and more "C1 + graceful fallback + honest band". E1 pairs C1
  with A1 which is attribute-based and genuinely independent — likely more robust on the
  thin/no-same-project production cases the backtest under-weights. **Recommendation: E2 as the
  default point estimate; keep A1/A2/A3 as validated components; R3-finish = (a) proper
  per-cell conformal to tighten intervals to exactly 80%, (b) test a 3-anchor blend, (c)
  re-check E1 vs E2 on a thin-comp-enriched slice before locking the skill.**
- **Team process lesson.** Worktree agents produced integrable, tested, leakage-clean code
  (verified). But the verify+synthesis tail was lost when the session ended — record: for
  long fan-outs, the orchestrator must re-verify from the journal, not trust the run to finish.

## EXP-0004 — R3 kickoff: independent hedonic AVM anchor + evidence-state ensemble (2026-07-15)
- **Status:** IN PROGRESS (5,000-subject walk-forward). Anchor + naive ensemble built &
  integrated; refinement (learned weights, alt anchors, conformal) handed to the team.
- **A1 hedonic AVM** (`researcher/backtest/avm.py`): stdlib OLS, log(psf) ~ log(area) +
  floor + time + segment + tenure + lease-age + district, fit once/month on the as-of condo
  set, subject evaluated at the as-of time coordinate (leakage-safe; unit test recovers
  synthetic coefficients within 3%). **Result: median APE 10.4% / P90 32% / coverage 100%
  / interval-cover 70%.** Far worse than same-project (4%) BUT never declines and beats the
  proxies (B4 14%, B5 18%) — a viable anchor for the thin/no-same-project cases.
- **E0 evidence-state ensemble** (`ensemble.py`): blend C1⊕A1 by same-project comp count.
  **Result: median 4.42% / P90 13.9% / coverage 100% / interval-cover 81%.**
- **Finding.** The ensemble **fixes the headline defect: interval coverage 44%→81% (hits the
  80% target) + full coverage**, at a small median cost (4.08→4.42%) caused by over-weighting
  the AVM on liquid cases (w_c1 only reaches 1.0 at n>=10). The point-accuracy trade is a
  weighting-tuning issue; the interval + coverage win is real and is what production needs.
- **Verdict:** A1 ACCEPT (as a thin-comp anchor, scope-limited). E0 MONITOR — beat it with
  learned weights before shipping. Next: team fan-out (below).
- **Leakage sign-off:** AVM fits on market.condo() (as-of only); subject evaluated at as-of
  time, never its own month; no full-history artifact. Unit-tested coefficient recovery.

## EXP-0003 — Condo-resale baseline leaderboard + G1 (2026-07-15)
- **Status:** DONE (8,000-subject sample, subjects >= 2023-01; lag-stable at 42/56/70d).
- **Result (median APE / P90 / cover / pct>10% / bias):**
  - C1_grid_adapted **0.041** / 0.122 / 0.994 / 0.154 / +0.007  ← THE BAR
  - B3_same_project_filtered 0.041 / 0.110 / 0.905 / 0.126 / -0.013
  - B2_median_last3 0.048 / 0.148 / 0.994 / 0.211
  - B1_latest 0.049 / 0.161 / 0.994 / 0.228
  - B4_nearest_project **0.139** / 0.376 / 0.997 / 0.626
  - B5_segment_avg **0.178** / 0.561 / 1.000 / 0.687 / **+0.204**
- **Findings.** (1) Same-project methods dominate (~4-5%); geographic/segment proxies are
  2.7-4.3x worse. (2) **C1 (the value-a-property grid) only ties B3 and beats the naive
  same-project median B2 by ~0.7pp median** — but with better tails (P90 0.122 vs 0.148,
  pct>10% 0.154 vs 0.211) at full coverage. The grid's time/floor/size adjustments earn a
  MARGINAL keep; the same-project signal itself carries the result. (3) Slices are flat on
  MEDIAN (segment 0.040-0.045, tenure 0.040-0.043, regime 0.040-0.045, all <6.0% = 1.5x
  bar) — leasehold is NOT worse (tenure is controlled within a project). (4) The real
  failures are in the TAIL: >4M quantum pct>10%=0.28 / P90=0.197; thin liquidity (1-2
  comps) pct>10%=0.236. (5) Interval coverage 0.44 vs 0.80 target — bands far too narrow.
- **G1 VERDICT — nuanced.** The strict "median >1.5x bar" rule opens NOTHING (max slice
  median 0.050 < 0.060). But that rule mis-measures here: the median is solved by
  same-project comps; the unacceptable defects are **(a) tail risk, (b) broken interval
  calibration, (c) same-project dependency** — and the backtest population (established
  resale) UNDER-represents production's thin/no-same-project cases, where our only fallback
  (B4/B5) is 14-18% APE. **Decision: skip the R2a/R2b/R2c median-driven bake-offs; pull R2d
  (independent AVM anchor) forward INTO R3, and make R3 = {AVM anchor that needs no
  same-project comp} + {conformal intervals} + {evidence-state ensemble}.** Re-open R2b/R2c
  only if R3 leaves a slice/tail gap. Recorded rationale, not a silent override.
- **Leakage sign-off:** as_of firewall (test_as_of_excludes_future); lag-stable 42/56/70;
  4% median is plausible for liquid same-project resale (not a leak signature); no
  full-history artifact used. contractDate month-granularity and index pub-lag respected.

## EXP-0002 — URA store audit / G0 (2026-07-15)
- **Status:** DONE. `research/audit_ura.py` (re-runnable).
- **Data:** full 4-batch pull — **136,436 caveats, 3,880 projects, 2021-07..2026-07 (61
  months)**. Segment CCR 20,582 / RCR 39,122 / OCR 76,732. Sale: Resale 83,461 / New
  47,910 / Sub 5,065. Tenure: leasehold 95,678 / freehold 36,066 / freehold_equiv 4,692.
- **Condo universe (Apt+Condo, EC excl):** 106,549. Landed 12,990. EC excluded 16,897.
  **Resale-condo subjects: 61,097.** Distinct condo projects 2,285 (liquid >=8: 1,431).
- **Exclusion rules (applied as subject AND comp):** no_of_units>1 (60 bulk/en-bloc);
  psf outside [500, 6500] (107 low + 2 high — data errors); EC excluded from condo
  universe (distinct sub-market); Land-type rows bucketed to landed.
- **G0 GATE: PASS** (>=48 months ✓ 61; >=20k subjects ✓ 61k; >=800 projects ✓ 2,285).
- **Real-data bugs caught (verify-before-trust paying off):** URA emits stray cp1252 bytes
  mid-batch (robust decode added); landed spelling `Semi-detached` + `Strata *` variants
  (substring match); EC contamination (excluded).

## EXP-0001 — Walk-forward harness + simple-benchmark baseline (condo resale)
- **Status:** infrastructure built; **awaiting the first real URA pull** to produce numbers.
- **Hypothesis:** a leakage-safe walk-forward backtest over URA caveats can rank valuation
  methods, and the mandate's 5 simple benchmarks form the bar every complex method must clear.
- **Data:** URA `PMI_Resi_Transaction` (rolling ~5y, month-granular caveats), normalized by
  `researcher/sources/ura.py`. As-of firewall = month-end + 56d caveat-lag buffer
  (`researcher/backtest/store.py`). Subject valued as of end of month M-1.
- **Methods under test (benchmarks):** B1 latest same-project · B2 median last-3 same-project ·
  B3 same-project ±30% size / 12mo · B4 nearest other project (1km, 12mo) · B5 segment
  (CCR/RCR/OCR) median psf, index-time-adjusted.
- **Benchmark:** these ARE the benchmarks — they set the bar for later hedonic/ML/graph methods.
- **Metrics:** MAE, mean/median/P75/P90 APE, %>10%, signed bias, interval coverage/width
  (`researcher/backtest/metrics.py`).
- **Result:** _pending real data._ Run: `python -m researcher.backtest.run`.
- **Failure analysis / slices to check first:** thin-volume projects (B1/B2 decline rate),
  CCR vs OCR, large/penthouse units, leasehold with short remaining lease, new-vs-resale mix.
- **Verdict:** _pending._

### Open leakage risks to audit before trusting any number
1. **contractDate is month-only** → same-month look-ahead is structurally avoided by valuing
   as of M-1, but verify no method reaches into month M.
2. **Caveat lag** is modelled as a flat 56d buffer — a guess. Sensitivity-test 42/56/70d.
3. **Index publication lag** (`index.as_of_quarter`, 35d) — a backtest at t must target the
   last *published* quarter, never a later one.
4. **Enriched panels** (`factors/panel_condo_enriched`, `dialectic_synthesis`, OneMap
   enrichment) are learned on FULL history → must NOT be fed into a pre-t valuation as-is.
   Any use inside the harness needs an as-of rebuild. **Not yet done — do not use them here.**
