---
name: condo-valuation-pipeline
description: "RE_search one-command condo valuation pipeline — numbers deterministic, narrative from model, 13 gates; sonnet-proven; use IT, never hand-craft digests"
metadata:
  node_type: memory
  type: project
  originSessionId: 05a8a0f6-1bf9-4533-9ace-a43bc7336084
---

**Since 2026-07-08 condo valuations in RE_search are a PIPELINE, not a craft.** Never
hand-build comps/valuation/cost_stack in a digest again — run:

```
python research/tools/doctor.py                                  # readiness gate (5 checks, exact fixes)
python research/lib/harvest_{sale,profitability,rent,towerview}.py <slug>   # app on that tab, 5Y window
python -m researcher.legacy.pipelines.condo_valuation <slug> --digest-slug <slug>_<unit> --asof DATE [--init]
```

The pipeline reconstructs the three-surface comp set (per-row **price=psf×sqft arithmetic
gate** + stale-panel fingerprint gate + same-day conflicting-price resolution), fits trend
(ladder: subject-segment cross-unit pairs ≥5 → repeat-sales ≥3 → 1.8% default, clamp
[0,5%]) AND floor premium (same-spec ±90d cross-floor pairs ≥8, clamp [0,2%]; OPB fitted
0.44%/层 vs 0.30% default — the default overprices low floors), runs the grid +
sensitivities (0%/+2pp/no-anchor/**resale_surfaces_only** — launch-PP prints can dominate
new-TOP comp sets and inflate the model leg), computes the **triangulation band** (AVM
cohort median ∪ model ∪ freshest same-spec print; the note names the actual upper/lower
legs — never boilerplate the direction), recomputes BSD/mortgage/yield, and runs 13 digest
gates (stale 点估 in BOTH S$ and psf scales, per-row comps arithmetic, recompute checks,
mojibake, **, TODO, Tier-1 provenance). Model writes ONLY narrative; gates refuse to ship
inconsistency. `--trend 0.0xx` override exists for reviewed rationale (on the record).
**Buyer advisory rule: cap = min(AVM, model), anchor = floor-adjusted freshest same-spec
print; the band top / model leg is NEVER an authorization to pay more.**

**Proven simple-model-safe:** a sonnet agent, given only the skills, reproduced the #18-03
valuation to the digit in 3 commands / ~98K tokens (2026-07-08 dry run). Its stumbles were
fixed: gates now whitelist sensitivity/band values near 点估; skeleton says "declare data
gaps, never fabricate".

**Studies shipped through it:** gallop_0304 (11 clean comps, 2,400 psf, band 2,354–2,400,
analyst PASS 8.35 after an R1 REVISE caught the stale-panel artifact) and onepearl_0316
(163 clean comps, band 2,323–2,543; R1 REVISE caught the wide-grid cross-cell
misalignment — 62/450 units carried a neighbour's PP strings; R2 caught prose counts
contradicting the table — profitability sections are now derived from the PROFIT SIGN,
not screen position) + Yield_Ladder_Memo (deliverables/build_yield_ladder_memo.py pulls
numbers from digests programmatically).

**Key analytical finding (operational):** the app AVM's bias vs the freshest same-spec
print is NOT one-directional — measured −3.4% (Spottiswoode), +1.4% (Gallop), +3.7%
(OPB low floors). Never treat AVM as floor/ceiling a priori; **the freshest same-spec
direct print is always the negotiation anchor.**

See [[investment-suite-valuation]] for harvest gotchas, [[data-source-trust-hierarchy]].
