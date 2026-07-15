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
| Condo resale | URA resale caveats (bulk, as-of) | **quant walk-forward** vs benchmarks | harness built (EXP-0001), no numbers yet |
| Landed | URA landed caveats (few, heterogeneous) | walk-forward **+ heavy case regression** (noisy MAE, wide CIs expected) | not started |
| New launch | *often none* — developer price ≠ fair value; only later resale is truth | **mostly case-based + separation-of-quantities discipline** | not started |

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
