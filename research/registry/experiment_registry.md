# Experiment registry

Newest first. One row per experiment; link to code/commit. Verdict vocabulary in
[`README.md`](README.md).

---

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
