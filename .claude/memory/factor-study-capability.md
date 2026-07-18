---
name: factor-study-capability
description: "RE_search factor study (condo+landed): official beta layer, 27-project panel, dialectic-hardened findings — asymmetric capture, priced-in factor ordering, friction-gated alpha; 2 investor reports + 2 analysis skills"
metadata:
  node_type: memory
  type: project
  originSessionId: 05a8a0f6-1bf9-4533-9ace-a43bc7336084
---

**2026-07-13: the factor study shipped** (Kelvin's goal: 历史因子研究 → condo/landed
reports + analysis skills). Data layer all committed in RE_search:

- `researcher/marketdata/singstat.py` — official URA price index 1975Q1→ (SingStat
  M212261/M212311, no auth). `researcher/factors/beta_layer.py` — cycles, CAGRs,
  **asymmetric capture** (landed vs nonlanded: up 0.95 / down 0.74 — the honest
  replacement for "low beta + alpha"; alpha is start-date sensitive: ≈0 from 1996
  peak, +1.8%/yr t=2.25 over 51y), price/rent 130 vs peak 146.
- `research/lib/harvest_nearby.py` — Nearby Properties table = the panel multiplier
  (tenure/TOP/units/psf range/yield per surrounding project + frozen Dist column).
  Radius is fixed ~200m; panel breadth comes from visiting more anchors.
  **Landed pages have NO condo Nearby table** (that slot is Tier-2 agency listings).
  Landed address search needs a HOUSE NUMBER; street name alone finds projects only.
  Landed Street-scope = per-address PP panel (landed Tower View); per-address pages
  carry transaction history since 1998.
- `researcher/factors/` — enrich_onemap.py (146 MRT stations, 30 curated popular
  primaries, parks/malls/coast layers, postal-sector→district→CCR/RCR/OCR),
  factor_model.py (within-segment Spearman + OLS + **leave-one-anchor-out** — the
  cluster-honest robustness), panels, dialectic_synthesis.json.

**Findings that survived the bull/bear/quant panel** (evidence tiers matter):
within-segment premium ordering **school-1km > newness > MRT ≈ FH** (direction-stable
under LOO; magnitudes NOT quotable); yield spread lives BETWEEN segments (within =
underpowered null, critical ρ≈0.75 at n≈6-7); policy-shock beta is SG's #1 risk factor
(panel addition); **alpha must clear the friction hurdle** (BSD+agent+SSD 4y16% →
alpha harvested at purchase, then hold); Frankel landed street ~+6-7%/yr raw =
~4.5-5.5%/yr ex-quality (rebuild spread +39% same-street is the quality contamination
AND the alpha program); catalyst rule: announced-not-opened, opened=priced.

**Deliverables (both analyst-PASSed 2026-07-13):** Factor_Study_Condo_Report.html
**PASS 8.5** / Factor_Study_Landed_Report.html **PASS 8.6** (2 rounds each) + skills
`condo-investment-analysis` / `landed-investment-analysis` (evidence-tiered,
checklist-grade). Post-remap stats: within-segment ordering became **newness ≈
school-1km strongest** (all 5 factors LOO-stable, adj R² 0.49); segment mapping
MUST use the app's Region field (Tier-1) — postal-district heuristics mislabel
(D21 Beauty World=RCR, D2 Spottiswoode side=RCR). Recurring defect class caught
twice by review: hand-typed window bands / prose carrying regenerable numbers —
**render every display band and stat phrase from the data files**. See
[[condo-valuation-pipeline]], [[data-source-trust-hierarchy]],
[[multiagent-budget-lessons]] (the lean-brief dialectic pattern).
