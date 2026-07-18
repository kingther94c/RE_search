---
name: value-a-property
description: SUPERSEDED by condo-resale-valuation (the walk-forward-validated engine v2). Kept as the Investment-Suite comp-reconstruction reference — use only when you specifically need the IS three-surface craft pipeline (exact floor/twin/AVM-cohort) to corroborate a hard case; otherwise use condo-resale-valuation.
---

> **SUPERSEDED (2026-07-16).** The default condo valuation skill is now
> **`condo-resale-valuation`** — engine v2, quant-validated on 136k URA caveats (~3.7%
> median APE, ~82% held-out interval coverage; research/registry/ EXP-0006/0007). This IS-based
> craft pipeline is retained as the Investment-Suite corroboration path (exact
> floor/stack/twin/AVM-cohort that URA lacks) — the R4 enrichment layer — not the primary
> engine. Use it to CORROBORATE hard cases, not as the fair-value source of record.

# Value a condo unit — the deterministic pipeline

## When to use this
Put a defensible market value on a specific condo unit ("the subject"). Since 2026-07
this is a PIPELINE, not a craft: every number (comp set, trend, grid, sensitivities,
AVM cohort, cost stack, yield) is computed by `researcher/legacy/pipelines/condo_valuation.py`
the same way every time. Your job is (a) harvesting with the right tabs/windows,
(b) writing the narrative sections, (c) passing the hostile review. **Never hand-edit
numeric sections of the digest** (valuation / comps_table / cost_stack) — the
validation gates diff them against recomputation and will fail the run.

## Data source — Investment Suite first (MANDATORY)
Comparables, AVM cohort, rents and realised pairs come from **Tier-1: PropNex
Investment Suite** (skill: `read-investment-suite`), policy/planning facts from
SG-official sources (URA/OneMap/PUB/SLA/MOE/IRAS/MAS/LTA). Portals are Tier-2
(reconcile); research/agent reports are Tier-3 (claims, never facts). **If the app
won't open: STOP** — run `python research/tools/doctor.py`, do exactly what it prints, wait
for the user if it says so. Never silently fall back to web data.

## The checklist (each step = one command + one gate)

Set `PYTHONIOENCODING=utf-8` for EVERY python invocation on Windows (not just these —
any ad-hoc check printing Chinese dies on cp1252 without it). Narrative sections may
quote the current estimate/band/sensitivity values freely; any OTHER number placed next
to the word 点估 fails the stale-base gate by design.

```bash
# 0. readiness gate — must print READY
python research/tools/doctor.py

# 1. open the development in the app (read-investment-suite skill), then per tab:
#    Sale tab, 5Y window        ->  python research/lib/harvest_sale.py <slug>
#    Profitability tab, 5Y      ->  python research/lib/harvest_profitability.py <slug>
#    Rent tab, 5Y               ->  python research/lib/harvest_rent.py <slug>
#    Tower View tab             ->  python research/lib/harvest_towerview.py <slug>
#    GATE: each prints "saved N ..." — zero rows refuses to overwrite; the selected
#    window is recorded in meta.window (the tab after the "..." token) — check it says 5Y.

# 2. skeleton digest (once per subject)
python -m researcher.legacy.pipelines.condo_valuation <slug> --digest-slug <slug>_<unit> \
       --asof YYYY-MM-DD --init
#    fill subject{} from Property Info + Tower View (size/floor/bedrooms/unit/tenure)

# 3. compute + validate (+ render once gates pass)
python -m researcher.legacy.pipelines.condo_valuation <slug> --digest-slug <slug>_<unit> \
       --asof YYYY-MM-DD
#    GATE: prints 点估/区间/三角谈判带 and runs all digest gates. TODO placeholders
#    fail the gates by design — write the narrative (summary/risks/catalysts/advisory
#    stance/verification), re-run until "gates pass" and the report renders.

# 4. acceptance review — property-report-review skill (hostile analyst, iterate to PASS)
```

## What the pipeline computes (so you can explain it, not redo it)
- **Three-surface comp reconstruction** (`research/lib/reconstruct_comps.py`): Sale table ∪
  Profitability sell-legs ∪ Tower View PP, fuzzy dedup (same unit+price within 31 days =
  one caveat; surfaces disagree on dates by a few days). The Sale table lazy-loads AND
  skips mid-window rows — single-surface sets are structurally incomplete. Residual gaps
  (Tower View shows only each unit's last trade; head-only profitability) are written
  into `data_gaps` automatically — keep them in the report.
- **Trend ladder** (`choose_trend`): subject-segment cross-unit pairs (≥5) → repeat-sales
  median (≥3) → default 1.8%; clamped to [0%, 5%]; sensitivities at 0% and +2pp always
  run. Segments differ (#18-03 study: 1-2BR flat, 3BR rising) — never pool them. A
  reviewer round may justify overriding: rerun with `--trend 0.025` and write the
  rationale into the summary; the override is recorded in `digest.pipeline.trend`.
- **Adjustment grid** (`researcher/legacy/valuation/engine.py`): time/floor/size
  (elasticity −0.08)/compact-3BR(≤800sf, 3%) on each comp. The floor premium is
  FITTED per development from same-spec ±90d cross-floor pairs when ≥8 exist
  (One Pearl Bank fitted 0.43%/floor vs the 0.30% default — high-rise new-TOP
  towers are steeper; using the default overprices low floors), else 0.30%
  default; clamped [0%, 2%]. Similarity weights
  `1/(1+|ln(size ratio)|×3+Δfloor/25+Δyrs/2+0.6·异卧室数)`; subject's own last sale =
  anchor at weight 2.0 (in the quantile multiset ONCE). Range = exclusive/type-6 IQR.
- **Triangulation** (`valuation.triangulation`): negotiation band = envelope of AVM-cohort
  median ∪ model point ∪ freshest same-spec print. The AVM's bias vs fresh prints is
  NOT one-directional (measured: −3.4% Spottiswoode, +1.4% Gallop, +3.7% One Pearl Bank
  low floors — see deliverables/legacy/build_yield_ladder_memo.py) — never treat the AVM as a
  floor or ceiling a priori; **the freshest same-spec direct print is always the
  negotiation anchor**, the AVM is just one leg.
- **Cost stack / yield**: BSD, 75% LTV mortgage, gross yield off same-type recent
  contracts — recomputed from the current estimate every run (gates verify).

## Reading the output
`estimate_psf/price` = weighted point; `low/high` = IQR band (point always inside);
`sensitivity` = trend 0% / +2pp / no-anchor psf; `triangulation.negotiation_band_psf`
= what you quote a buyer/seller. Grid rows show `raw ×time ×flr ×size ×type → adj, wt`
— read the top-weight rows to see what drives the number, and say so in the summary.

**Worked result (#18-03 Spottiswoode Suites, 743sf 3BR L18, asof 2026-07-03, analyst
PASS 8.8/10):** 37-comp three-surface set; twin #18-02 printed $2,330 psf on
2026-06-23 (ceiling); AVM cohort $2,250 (floor); reviewed estimate S$1,716,000 @
$2,309 psf (trend 2.5%/yr adopted with cohort-pair rationale); negotiation band
$2,250–2,330. The pipeline's untouched ladder gives $2,218 psf (trend +1.03%,
cross-unit 3BR n=6) with band $2,218–2,330 — the difference is the trend choice;
both are defensible, the review round is where the argument happens and gets recorded.

## Limitations (state them in every report)
- Thin volume → the anchor/twin/AVM triangulation carries more weight than the mean.
- Calibration is segment-specific; the ladder is a floor, not an oracle.
- No condition/view/reno adjustment — note qualitatively.
- The app's Est. Val is LIVE (changes day to day) and its band-head aggregates are
  opaque — never force-reconcile them per print.

## Related files
- `researcher/legacy/pipelines/condo_valuation.py` — the pipeline CLI (this skill's engine room)
- `research/lib/reconstruct_comps.py` — three-surface union, trend ladder
- `researcher/legacy/valuation/engine.py` — grid; `researcher/legacy/valuation/validate_digest.py` — gates
- `research/tools/doctor.py` — readiness; `research/lib/harvest_{sale,profitability,rent,towerview}.py`
- `deliverables/legacy/build_condo_report.py` — bilingual HTML renderer
