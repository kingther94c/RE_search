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
| Condo resale | URA resale caveats (bulk, as-of) | **quant walk-forward** vs benchmarks | **SHIPPED (R5): `condo-resale-valuation` skill, engine v2.1 = C1 + anchor-fallback + conformal — 3.71% median / 100% cover / ~82% interval. G3 + G5 MET (hostile review PASS 8.7/10).** Next: R4 IS enrichment / R6 landed |
| Landed | URA landed caveats (few, heterogeneous) | walk-forward **+ heavy case regression** (noisy MAE, wide CIs expected) | not started (data present: 12,990 caveats) |
| New launch | *often none* — developer price ≠ fair value; only later resale is truth | **mostly case-based + separation-of-quantities discipline** | not started (data present: 47,910 new-sale caveats) |

### Condo engine v2 — FINAL (EXP-0006, G3 MET)
- **`engine_v2.py` (V2, v2.1 after EXP-0007):** POINT = C1 same-project grid wherever it
  answers, else lease-aware anchor fallback for coverage; INTERVAL = split-conformal per
  (liquidity×segment) cell (`conformal_table.json`, 85% nominal). **Backtest: median 3.71% /
  100% coverage / interval ~82% held-out (85% nominal) / P90 11.5% / pct>10% 13.3%.** (EXP-0007 size/time fixes cut
  median from 4.09%.) C1 uses segment-specific size elasticity (CCR −0.02 / RCR −0.08 / OCR
  −0.09), size-gated comps, recency + time-quality weighting, time-adj cap [0.80,1.25].
- **Hard-case honesty:** anchor-disagreement flag, freshest-same-size reference + directional
  "possibly optimistic" flag, band widened to that reference, confidence capped, IS manual to-do.
- **Key lesson (drove the design):** blending an independent anchor into C1 HURTS the point
  everywhere same-project data exists — even at 1-2 comps (C1 4.84% vs blends 5.1-5.8%). The
  anchors buy COVERAGE (no-comp fallback) and INTERVALS, not point accuracy. So v2 is
  "best-method-where-it-applies + fallback + calibrated band", NOT an ensemble blend.
- **Superseded:** E0/E1/E2/E3 ensembles (the experiments that proved the above). Dead:
  segment-avg (GY-0001), nearest-project (GY-0002).
- **Retained components:** C1 (point), A2 5.46% / A3 7.2% / A1 10.3% (fallback + interval
  inputs), conformal table.
- **Known scope for R5 skill:** point accuracy is same-project-driven; the ~0.6% no-comp
  cases lean on A2 (5.5%) — flag lower confidence there. Conformal calibrated on 2023-24,
  validated 2025-26; recalibrate on each data refresh.

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
