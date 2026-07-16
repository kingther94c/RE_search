# Experiment registry

Newest first. One row per experiment; link to code/commit. Verdict vocabulary in
[`README.md`](README.md).

---

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
