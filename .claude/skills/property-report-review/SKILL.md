---
name: property-report-review
description: Use when a RE_search research report (landed area / new-launch / condo valuation) is drafted and needs a critical acceptance review before delivery — spawns a hostile SG property-analyst judge, returns PASS/REVISE with blocking issues, iterate until PASS.
---

# Property-analyst acceptance review (批判性验收)

Goal: no report ships on first draft. A **hostile reviewer** — not the author — judges it
against this rubric; the author fixes and resubmits until PASS. Two consecutive PASS-quality
drafts in a row is normal; five REVISE rounds means the research, not the prose, is broken.

## The reviewer persona (spawn as a separate agent, never self-review)

> 20+ years Singapore residential analyst (ex-URA/consultancy), CFA-level rigor, pedantic
> about data provenance, deep D10/school-zone + new-launch + resale knowledge, hostile to
> marketing fluff. Deciding whether this report is fit to hand to a paying client.

Give the reviewer: the report HTML (or its rendered text), the digest JSON, and
this rubric. Do NOT give them the chat history — the report must stand alone.

## Rubric — six dimensions, 0-10 each (weights)

| # | Dimension | Wt | What 10 looks like |
|---|---|---|---|
| 1 | data_accuracy | 25% | Every number current & traceable; no contradiction with URA/OneMap/PUB/MOE/SLA; psf math checks. **Load-bearing transaction/AVM/rent/yield numbers must trace to Tier-1 (PropNex Investment Suite or SG-official URA REALIS), not Tier-2/3 web aggregators or research reports** — a study that ran only on portal/report data is a data_accuracy downgrade |
| 2 | method_rigor | 20% | Landed: value-ordering respected, spread explained not averaged. New-launch: price vs real comps, supply counted. Condo: adjustment grid defensible, range honest |
| 3 | completeness | 15% | Every checklist dimension of the underlying skill present (hazards, future, regulatory ABSD/SSD/LDAU, financing, liquidity) |
| 4 | decision_usefulness | 20% | Clear best-for/not-for, quantified screening thresholds, explicit go/no-go — buyer could act tomorrow |
| 5 | honesty_uncertainty | 10% | Data gaps declared, confidence marked, verify-before-trust steps (INLIS, bank valuation, OneMap) listed |
| 6 | presentation_bilingual | 10% | 中文/English both natural; tables render; units unambiguous (land psf vs strata psf, sqft vs sqm) |

`overall = Σ(score × weight)`. **PASS requires: overall ≥ 8.0 AND every dimension ≥ 6.0
AND zero blocking issues.**

## Blocking issues (any ONE fails the report regardless of scores)

- a load-bearing number is wrong (psf/price/date/policy rate that changes the conclusion)
- a major claim has no source and cannot be verified
- a load-bearing transaction/valuation number rests **only** on a Tier-3 source (research
  report, agent/marketing copy) with no Tier-1 (Investment Suite / URA REALIS) corroboration —
  conflicted sourcing presented as fact is a blocker, not a caveat
- internal contradiction (summary vs table, 中文 vs English disagree)
- misleading advice (ignoring SSD inside 4yr, wrong ABSD tier, wrong 1km/GCBA judgement)
- broken rendering (empty data section, mojibake, broken table)

## Reviewer output (structured)

```json
{"scores": {"data_accuracy": 0, "method_rigor": 0, "completeness": 0,
            "decision_usefulness": 0, "honesty_uncertainty": 0, "presentation_bilingual": 0},
 "overall": 0.0,
 "blocking_issues": [{"where": "", "what": "", "evidence": ""}],
 "improvements": [{"priority": "P1|P2|P3", "where": "", "what": ""}],
 "verdict": "PASS | REVISE",
 "praise": [""]}
```

## The loop

1. Author drafts report (digest → `deliverables/build_*.py`).
2. Spawn reviewer with report + digest + rubric. Reviewer may spot-check 2-3 load-bearing
   numbers against live sources (WebSearch) — accuracy scores must be evidence-based.
3. On REVISE: fix ALL blocking issues + P1s (P2/P3 at author's judgement — note skipped ones).
   Fixes that need new data go back to research, not wordsmithing.
4. Regenerate, resubmit to a FRESH reviewer agent (no memory of prior round — prevents drift
   toward leniency).
5. On PASS: record the final scores in the digest under `review` and ship.

## Gotchas

- The reviewer wants to find problems; if a round returns zero findings AND <8.5 overall,
  the review itself was lazy — rerun with an explicit "spot-check 3 numbers" instruction.
- Never let the author agent also be the reviewer in the same context (anchoring).
- Bilingual disagreement is a BLOCKER, not a style nit — the 中文 is what the client reads.
