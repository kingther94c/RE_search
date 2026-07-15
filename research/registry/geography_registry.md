# Geography registry — Singapore value geography (shared dependency)

Geography is a **shared research module**, consumed by all three valuation skills; it is
**not** a user-facing skill of its own. The question it answers is not "where is this on a
map" but: *how likely is a buyer of A to treat B as a genuine substitute?* — valuation /
substitutability distance.

## Current state
- **Prior only.** CCR / RCR / OCR (from URA `marketSegment`, carried on every caveat) are
  treated as the **broad parent market**, nothing finer is validated yet. District and SVY21
  (x,y) coords are available per caveat for distance work.
- The `factors/` panels define a 27-project condo/landed universe with a beta/alpha layer —
  **project-level, learned on full history** → usable as a research prior, **NOT** inside a
  pre-t backtest without an as-of rebuild (see EXP-0001 leakage note 4).

## Methods to test (mandate Module 1) — none validated yet
- **A** official hierarchy (CCR/RCR/OCR → planning area → estate) — the current prior.
- **B** price-behaviour clustering (standardised relative-value co-movement).
- **C** feature-similarity / substitutability graph (project or street nodes).
- **D** learned spatial representation (embeddings / metric learning).
- **E** hybrid: official prior + data-derived overlapping sub-markets.

## Acceptance rule
A geography is accepted only if it **improves out-of-sample valuation / comp selection /
time-adjustment stability**, not on silhouette or any generic clustering score. Condo and
landed may need **different** geographies — do not assume one serves both.

## Verdict: _pending — no geography beyond the CCR/RCR/OCR prior has been validated._
