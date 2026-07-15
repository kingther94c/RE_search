# Research registry — the durable knowledge base

The valuation program is run as **quant model research**, not prompt-writing. A method
enters a skill only after it beats simple benchmarks on the walk-forward harness
(`researcher/backtest`). This directory is the memory that stops the next agent from
re-deriving what we already settled — especially from **re-inventing a rejected method**.

| File | What it holds |
|---|---|
| [`00_master_methodology.md`](00_master_methodology.md) | current *validated* valuation architecture (per asset). Starts thin on purpose — only what survived validation goes here. |
| [`01_roadmap.md`](01_roadmap.md) | **the program roadmap** (R0–R8): per-phase research direction, plan, guardrails, deliverables, gates. Start every session here. |
| [`experiment_registry.md`](experiment_registry.md) | every experiment: hypothesis · data · method · benchmark · result · failure analysis · verdict. |
| [`method_graveyard.md`](method_graveyard.md) | rejected approaches **and why**. Read before proposing anything. |
| [`feature_evidence.md`](feature_evidence.md) | per valuation feature: mechanism · evidence · scope · functional form · confidence. |
| [`geography_registry.md`](geography_registry.md) | the Singapore value-geography method + its validation (shared dependency, not a user-facing skill). |
| [`changelog.md`](changelog.md) | every material methodology/skill change: what · why · evidence · backtest impact · assets affected. |

## Verdict vocabulary (every experiment ends with one)
- **ACCEPT** — beats benchmarks out-of-sample, stable, explainable.
- **ACCEPT WITH SCOPE LIMIT** — wins only on a defined slice (e.g. liquid OCR condos). Record the scope.
- **MONITOR** — promising but unstable / in-sample only; re-test with more data.
- **REJECT** — no robust out-of-sample edge, or worse tail risk, or unauditable. Goes to the graveyard.

## The loop (per component)
hypothesis → ≥3 materially-different methods → simplest benchmark → time-consistent
walk-forward → slice analysis → counterexample search → error diagnosis → refine →
revalidate → verdict. Do **not** stop after one good backtest.

## Discipline
Prefer the simple method unless the complex one *robustly* wins. Any coverage cap
(top-N, sampling, no-retry) must be logged, not silent. Distinguish, always: verified
fact · empirical finding · professional convention · hypothesis · open question · judgement.
