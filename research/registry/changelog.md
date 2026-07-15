# Model & skill changelog

Newest first. Every material methodology/skill change: what · why · evidence · backtest
impact · assets affected.

---

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
