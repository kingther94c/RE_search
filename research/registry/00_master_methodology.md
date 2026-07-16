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
| Condo resale | URA resale caveats (bulk, as-of) | **quant walk-forward** vs benchmarks | **engine v2 (EXP-0005): E2 ensemble 4.16% median / 100% cover / 87% interval — G3 MET**; R3-finish (conformal) then R5 skill |
| Landed | URA landed caveats (few, heterogeneous) | walk-forward **+ heavy case regression** (noisy MAE, wide CIs expected) | not started (data present: 12,990 caveats) |
| New launch | *often none* — developer price ≠ fair value; only later resale is truth | **mostly case-based + separation-of-quantities discipline** | not started (data present: 47,910 new-sale caveats) |

### Current condo engine (EXP-0003 bar → EXP-0005 v2)
- **Bar (C1 grid):** ~4.08% median APE, but interval coverage 43% and declines ~0.7%.
- **Engine v2 (E2_ensemble_pooled = C1 ⊕ A2 pooled-shrinkage anchor):** median **4.16%**,
  **100% coverage**, **interval 87%**. Ties the bar on median while fixing calibration
  (43%→87%) and always answering — **G3 MET** (tie + materially better calibration/coverage).
  E1 (C1⊕A1) is the near-tied, more-independent alternative (4.18%/81%).
- **Validated components:** C1 (same-project grid), A1 hedonic / A2 pooled / A3 kNN anchors,
  E1/E2 ensembles. A2 (5.46%) is the strongest independent anchor; segment-avg & nearest-
  project are dead (GY-0001/0002).
- **R3-finish (before the skill):** per-cell conformal to tighten intervals to exactly 80%;
  test a 3-anchor blend; re-check E1-vs-E2 on a thin-comp-enriched slice (backtest
  under-samples the no-same-project case that matters most in production).

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
