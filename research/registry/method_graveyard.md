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

_Empty. No method has earned a REJECT verdict yet — the harness (EXP-0001) has not been_
_run on real data. The first honest backtest will start filling this._

**Watch-list (hypotheses the user flagged as likely-to-fail — must be *tested*, not assumed):**
- "District / segment average PSF" as a **standalone** valuation (vs. a coarse benchmark).
  It is deliberately included as benchmark **B5** so it is measured, not hand-waved. If it
  loses to same-project methods on liquid projects, that becomes GY-0001 with numbers.
