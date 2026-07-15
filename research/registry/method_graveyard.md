# Method graveyard

**Read this before proposing a method.** Rejected approaches live here with the evidence
that killed them, so we don't rediscover them. A method lands here only after a REJECT
verdict in the [experiment registry](experiment_registry.md) — nothing is buried on
intuition alone.

Format per entry:

> ### GY-NNNN — <method name> (asset, date)
> - **Claim it made:** …
> - **How tested:** experiment id, data, benchmark it lost to.
> - **Why rejected:** the specific out-of-sample failure (numbers).
> - **Scope of the rejection:** where it fails (may survive on a narrow slice — say so).
> - **Do not resurrect unless:** the condition that would change the verdict.

---

### GY-0001 — Segment (CCR/RCR/OCR) average PSF as a standalone valuation (condo, 2026-07-15)
- **Claim it made:** a market-segment median psf, time-adjusted, approximates a unit's value.
- **How tested:** EXP-0003, benchmark B5, 8,000-subject walk-forward.
- **Why rejected:** median APE **17.8%** vs 4.1% for same-project (4.3x worse), P90 56%,
  pct>10% 69%, and **systematically biased +20.4%** — it over-values because the segment
  pool skews to pricier/newer stock than the median resale subject.
- **Scope of the rejection:** as a *standalone valuation*. It is RETAINED as benchmark B5
  (the bar a real method must clear) and may survive as a coarse prior when NO local comp
  exists — but never as the estimate when same-project or substitute comps are available.
- **Do not resurrect unless:** mix-controlled (hedonic) — at which point it is no longer a
  "segment average" but the R2d/R3 AVM, tested separately.

### GY-0002 — Nearest-project PSF as a substitute (condo, 2026-07-15)
- **Claim it made:** the geographically nearest OTHER project is a good value proxy.
- **How tested:** EXP-0003, benchmark B4.
- **Why rejected:** median APE **13.9%**, P90 38%, pct>10% 63% — geographic proximity alone
  is a weak substitutability signal (adjacent projects differ by age/tenure/positioning).
- **Scope:** rejects "nearest = comparable". Motivates R2b: substitutability distance, not
  raw distance. A *learned/multi-factor* substitute model is a different method, still open.
- **Do not resurrect unless:** distance is combined with tenure/age/quantum/positioning
  similarity (that is the R2b hypothesis, not this one).

**Watch-list (tested, retained as benchmarks, not yet buried):** none outstanding — the two
proxy methods the user flagged are now measured and filed above.
