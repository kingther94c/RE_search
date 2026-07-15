# Experiment registry

Newest first. One row per experiment; link to code/commit. Verdict vocabulary in
[`README.md`](README.md).

---

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
