# Model & skill changelog

Newest first. Every material methodology/skill change: what · why · evidence · backtest
impact · assets affected.

---

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
