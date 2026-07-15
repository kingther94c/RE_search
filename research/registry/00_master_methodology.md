# Master methodology — current validated architecture

> Only what has **survived time-consistent validation** is stated here as method. Everything
> else is labelled *production craft (untested OOS)*, *hypothesis*, or *prior*. This file is
> the single source of truth for what the three skills are allowed to rely on.

## Target (mandate)
Three user-facing skills — `condo-resale-valuation`, `new-launch-valuation`,
`landed-valuation` — over shared modules (value geography, market/time adjustment,
independent evidence families, ensemble, validation). Geography is a **shared dependency**,
not its own skill.

## Validation status by asset
| Asset | Ground truth for OOS | Validation protocol | Status |
|---|---|---|---|
| Condo resale | URA resale caveats (bulk, as-of) | **quant walk-forward** vs benchmarks | **baseline set (EXP-0003): bar = 4.1% median APE (C1 grid ≈ B3), same-project methods dominate**; R3 next |
| Landed | URA landed caveats (few, heterogeneous) | walk-forward **+ heavy case regression** (noisy MAE, wide CIs expected) | not started (data present: 12,990 caveats) |
| New launch | *often none* — developer price ≠ fair value; only later resale is truth | **mostly case-based + separation-of-quantities discipline** | not started (data present: 47,910 new-sale caveats) |

### Current condo bar (EXP-0003, 8k walk-forward, lag-stable)
- **Point estimate:** C1_grid_adapted / B3 at **~4.1% median APE** is the number to beat.
  Same-project comps carry it; segment/nearest proxies are 3-4x worse (GY-0001, GY-0002).
- **Open defects R3 must fix:** tail (pct>10% = 15%, worse for >4M & thin-liquidity);
  interval coverage 44% vs 80% target; no good fallback when same-project comps are absent
  (production faces this more than the backtest does).

The protocol is **not uniform across assets** — this was an explicit correction to the
mandate. Do not pretend a clean walk-forward fair-value backtest exists for new launch.

## Current production craft (in use, NOT yet OOS-validated)
- `value-a-property` (condo): three-surface comp reconstruction from Investment Suite →
  trend ladder → adjustment grid (time/floor/size/compact-3BR) → triangulation (AVM cohort ∪
  model point ∪ freshest same-spec print) → uncertainty band → buyer/seller guidance.
  Treated as **a candidate baseline to be backtested**, not as settled truth.
- `factors/` beta/alpha framework: segment beta + priced-in factor checklist + friction
  hurdle. Research prior; **full-history, leakage-prone inside a backtest.**

## Data spine
- **URA `PMI_Resi_Transaction`** — backtest base (bulk, official, as-of replayable, month-
  granular, ~5y). `researcher/sources/ura.py`.
- **Investment Suite** — live, richer, per-unit Tier-1 for production single-property runs and
  for **calibrating** URA-based estimates (exact floor/stack/rent/realised pairs URA lacks).
  Bottleneck: extraction is UI-driven — a better harvest skill is its own work-line.
- **SingStat/URA PPI** — time adjustment (`researcher/backtest/index.py`, with publication lag).

## Invariants (do not violate)
- No fabricated adjustment factors — unresolved features widen uncertainty or request info.
- Every complex method competes with simple benchmarks before entering a skill.
- Fair value is separated from buyer/seller strategy, and from developer pricing power.
- Verified fact · empirical finding · convention · hypothesis · judgement are labelled distinctly.
