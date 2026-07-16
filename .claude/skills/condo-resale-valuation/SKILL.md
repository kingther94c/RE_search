---
name: condo-resale-valuation
description: Use to value a specific Singapore resale CONDO unit — a defensible fair value (psf + price), a calibrated range, confidence, comps, and buyer/seller price guidance. Runs the walk-forward-validated engine v2 (URA data spine) and renders a bilingual report. Supersedes value-a-property.
---

# Value a resale condo unit — engine v2 (validated)

## When to use
Put a defensible market value on a specific Singapore resale condominium unit. The engine
is **quant-validated**: time-consistent walk-forward backtest on 136k URA caveats gives
**~3.7% median APE** with **~82% held-out interval coverage (85% nominal)**
(research/registry/experiment_registry.md EXP-0006/0007). Not a craft judgement call — every
number is computed the same way.

## Inputs
- **Required:** project name (as it appears in URA), unit size (sqft). The project must
  have URA caveats — segment / district / coords / tenure are inferred from them.
- **Optional but improve the read:** floor, actual remaining lease, `--asof` date.
- **Out of scope (v1):** a project with NO URA caveats (brand-new, never-transacted) →
  the engine returns `project_not_found` and tells you to escalate to an Investment-Suite
  comp pull. It never fabricates a number.

## Data-source priority
1. **URA private-residential caveats** — the validated spine (bulk, official, as-of). Comes
   from the committed snapshot; refresh with `python -m researcher.sources.ura`.
2. **Investment Suite** (Tier-1, per-unit) — enrichment for exact floor/stack/rent/twin
   prints URA lacks. **NOT yet wired into the engine (R4 builds the automated bridge).** On a
   `hard_case` / fallback / `directional_flag`, the report tells YOU to pull IS twin-unit +
   AVM comps MANUALLY before offering — treat that as a required to-do, not an automated step.
3. **SG-official** (URA/OneMap/URA PPI) for time adjustment and policy facts.
Portals are Tier-2 (reconcile); agent reports Tier-3 (claims, never facts).

## Run it
```bash
# one unit -> full valuation + bilingual HTML report (RESEARCH_REPORTS_DIR or deliverables/)
python deliverables/build_condo_v2_report.py --project "TREASURE AT TAMPINES" --area 936 --floor 12
```
Programmatic: `from researcher.backtest.value_unit import value, SubjectSpec`.
As-of semantics: **omit `--asof` for a LIVE valuation** (the pulled store is the info set —
freshest prints included); an explicit past `--asof` reconstructs what was knowable then
(56-day caveat-lag, day-granular). Don't backdate asof for a live question.

## What the engine does (so you can explain it, not redo it)
- **Point = C1 same-project adjustment grid** wherever the project has resale caveats:
  same-project prints, each time-adjusted (URA PPI, capped ±25%), floor-band and size
  adjusted (segment-specific elasticity CCR −0.02 / RCR −0.08 / OCR −0.09, re-fit on URA in
  EXP-0007; size-matched comps preferred), similarity-weighted. Best on EVERY liquidity slice — even
  1-2 comps beat any cross-project anchor (EXP-0006). No same-project comp → **fallback**
  to the pooled anchor A2 (→A3→A1) purely to keep coverage; flagged as lower confidence.
- **Independent reads (transparency):** three anchors that need no same-project comp —
  A1 hedonic, A2 empirical-Bayes pooled, A3 feature-kNN — are shown alongside. Their
  **convergence is a signal; a spread >15% is a HARD CASE** (corroborate before offering).
- **Range = split-conformal band** per (liquidity × segment) cell, calibrated on 2023-24,
  validated ~82% coverage on 2025-26. It is the empirical spread within which ~82% of
  comparable units actually printed — not a guess.
- **Confidence (0-100)** is tied to the empirical error curve: same-project comp depth,
  band width, and anchor disagreement. Deep liquid market → ~88; boutique/divergent → ≤62.

## Fair value vs guidance (kept separate)
- **Fair value** = engine point + conformal range. Objective.
- **Buyer guidance** (derived from the band): attractive `< low`, fair range `[low, high]`,
  walk-away `> high`.
- **Seller guidance:** ask `= high`, expected clear `= point`, quick sale `= low`.
Never present asking-price aspiration as fair value.

## Mandatory verify-before-offer (in every report)
Exact remaining lease for THIS unit (URA tenure is project-level); actual floor/stack/facing
(URA has no unit id → no stack/view adjustment); condition & renovation (not modelled);
en-bloc/redevelopment status, levies, encumbrances. If same-project comps < 3: pull
twin-unit + AVM comps from Investment Suite BEFORE offering.

## Failure & escalation
- `project_not_found` → out of scope; escalate to Investment-Suite pull.
- `hard_case` true (anchors disagree >15%) → treat the point as indicative, widen the band,
  corroborate with IS/twin prints, say so.
- Fallback used (no same-project comp) → confidence ≤ 40; do not offer on the number alone.

## Limitations (state them)
URA is month-granular, floor-BAND, no unit id → no stack/view/condition/renovation
adjustment (note qualitatively). Point is same-project-driven. The band is empirical, not a
guarantee. Not a substitute for a licensed valuation.

## Reliability / regression
`tests/test_value_unit.py` asserts archetype behaviour (liquid → high-confidence + anchor
agreement; boutique → flagged; unknown → escalates; guidance separated). **Rerun on every
engine change; an update that breaks a green case does not ship.**

## Related
- `researcher/backtest/value_unit.py` — this skill's engine room (valuation + guidance)
- `researcher/backtest/engine_v2.py` — C1 point + anchor fallback + conformal
- `researcher/backtest/{candidates,avm,avm_pooled,avm_knn}.py` — the methods
- `research/registry/` — the validation record (EXP-0003/0005/0006, method graveyard)
- `deliverables/build_condo_v2_report.py` — the bilingual HTML renderer
