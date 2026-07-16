# Program roadmap v2 — LANDED FIRST (L0–L4), condo shipped & frozen

_v2 2026-07-16 (Fable re-plan on user decision: landed must land first) · supersedes v1
(R0–R8, condo-first — executed through R5; v1 text in git history, results in the registry).
This is the operating document for every session: pick the current phase, check its gate,
work its plan. Amend via changelog, not silently._

## Where the program stands

| Track | Status |
|---|---|
| **Landed (L0–L4)** | **← ACTIVE — L0 DONE (GL0 PASS, EXP-0009) · L1 DONE (GL1 PASS, EXP-0010: bar = LC1 10.5% @ 87% cover; noise floor ~5.3-6.2%/print); next: L2 (L2a size curve mandatory + L2c lease-matched retrieval first). Goal: ship `landed-valuation` (hostile-review PASS ≥8)** |
| Condo resale | **SHIPPED & FROZEN** — `condo-resale-valuation` accepted (PASS 8.7/10; engine v2.1: 3.71% median APE / 100% coverage / ~82–85% held-out interval). Backlog below; nothing ships without its gate |
| New launch (was R7) | PARKED (plan preserved below) |
| IS calibration bridge (was R4) | PARKED — becomes relevant again for condo hard-cases and landed condition evidence |
| Operations (was R8) | NOT STARTED — after L4, build ONE refresh runbook covering both shipped skills |

Infrastructure is DONE and asset-agnostic: as-of store + leakage firewall, walk-forward
harness, metrics, PPI (has a **Landed** series — wiring verified), conformal calibration
pattern + code fingerprint, registry discipline, and the R5 ship playbook (benchmarks → bar
→ error-driven methods → engine + calibrated uncertainty → skill + regression suite →
fresh-reviewer hostile loop). **The L-track reuses all of it; only data hygiene, benchmarks
and domain logic are landed-specific.**

## North star (mandate, unchanged)

> For a specific SG property, using only information available at the valuation date: the
> most reliable estimate of worth, the explanation, quantified uncertainty, and actionable
> buyer/seller price guidance. Defensible + transparent + empirically validated + actionable.

## Landed data reality (measured 2026-07-16 — every design choice below answers to this)

- **12,849 landed caveats / 12,115 resale subjects** (~199/mo island-wide): island-level
  walk-forward is viable. Per-street it is NOT: **1,072 streets, median 5 caveats/street
  per 5 years** (p90 = 30) → **partial pooling is mandatory**; a street-only benchmark will
  mostly decline, and that decline rate is itself a finding.
- **87% of rows are `type_of_area='Land'`: psf = LAND psf, area = LAND area** (p50 2,640
  sqft, p95 7,622). **1,613 strata-landed** (cluster housing) trade on strata area — a
  different sub-market, currently covered by NEITHER shipped skill (orphaned — see L0).
- Tenure: 68% freehold + 14% 999-yr + 18% leasehold. Segment: OCR 8,593 / RCR 2,484 /
  CCR 1,772. Type: Terrace 6,003 / Semi-D 3,648 / Detached 1,570 (GCB subset is thin).
- **URA gives NO plot geometry (frontage/depth/shape/corner), NO building age/condition/GFA,
  NO address-level id.** Consequences: geometry is case-tier by construction; the caveat
  price is a LAND+BUILDING BUNDLE we cannot decompose in bulk — L1 must MEASURE the
  resulting noise floor and the skill must publish it (no false precision).
- A same-plot matcher looks feasible: (street, exact land area, type) — land areas are
  near-unique per lot → candidate repeat-sales pairs for time adjustment, dedup, and
  rebuild-detection. Precision must be spot-checked before trust (L0).

---

## L0 — Landed data foundation (est. 0.5–1 session)

**Research direction.** None — hygiene and measurement. No conclusions in L0.

**Plan.**
1. Store slice: pure-landed = `type_of_area='Land'` + landed types. **Strata-landed OUT of
   scope for v1** (recorded as an orphaned sub-market with a routing note — backlog: a thin
   condo-engine variant on the strata-landed pool). Resolve the 15 stray 'Apartment' rows
   inside the landed slice (inspect, write the rule).
2. **Land-psf sanity band from the data** (percentile method, like condo's [500, 6500] —
   the roadmap prescribes the METHOD; the number comes from measurement, per guardrail 5).
3. **Same-plot matcher**: (street, exact area, type) → repeat pairs. Measure pair count,
   spot-check ≥20 by hand for plausibility, dedup true duplicates (same plot+month+price).
   This asset feeds L1's noise floor, L2b's repeat-sales time signal, and L2e's rebuild
   detection — it is the landed analogue of what IS realised-pairs were for condo.
4. MarketView landed support: landed pool + spatial grid (small, mirrors `condo_near`).
5. Subjects definition: resale, pure-landed, sane band, ≥18-months-in start.
6. Landed audit script (extend `audit_ura.py` or `audit_landed.py`) with a **GL0 gate
   check**, machine-readable, re-runnable.

**Guardrails.** Verify-before-trust on every landed field semantic (area=LAND area, psf=
land-psf confirmed per row type); the same-plot matcher is UNTRUSTED until spot-checked.

**Deliverables.** EXP-0009 audit + hygiene rules · same-plot pair set + precision note ·
landed MarketView support.

**Gate GL0.** ≥10k pure-landed resale subjects; ≥48 usable months; hygiene rules documented;
matcher spot-check ≥80% plausible; land-psf band set from data. Fail → data strategy
escalation before any research.

**→ OUTCOME (2026-07-16): PASS — EXP-0009.** 10,789 subjects / 61 months / band [100,
6500] wraps verified-real extremes (cuts 0) / matcher 685 plots → 850 pairs (395 ≤18mo),
spot-check 24/25 / rules R1–R5 in `research/audit_landed.py`. Open finding carried to L1:
21.4% exact-copy row involvement (twin-sale vs double-entry unresolvable from URA alone —
street-liquidity counts carry the bound). Strata-landed (1,629) routed out on record.

---

## L1 — Landed baseline: the honest leaderboard (est. 1 session)

**Research direction.** What do simple, practically-knowable methods achieve on landed
BUNDLES; where is the error mass; and what is the irreducible noise floor?

**Plan.**
1. Benchmarks (simple → THE LANDED BAR):
   - **LB1** same-street recent land-psf (will often decline — the decline rate is data);
   - **LB2** pooled street→district (street if n≥k else district), type-matched, time-adj;
   - **LB3** type × tenure × segment pool median land-psf, time-adjusted (LANDED index);
   - **LB4** spatial kNN (nearest landed sales, same type, size-similar, time-adjusted);
   - **LB5** district median total price by type (naive quantum);
   - **LC1** craft port: the Cardiff land-psf quantum method skeleton (land-psf × area with
     a log-log size prior) — the incumbent, competing like C1 did for condo.
2. Walk-forward over all eligible landed resale subjects; lag-stability 42/56/70d.
3. Slices: type / tenure / segment / land-size bucket / street-liquidity / regime / quantum
   / GCB-flag (crude: detached ∧ area ≥15,070 sqft ∧ prime districts).
4. **Noise-floor study (landed-specific, load-bearing):** same-plot repeats with gap ≤18mo →
   market-adjusted price dispersion = the lower bound on achievable accuracy (bundle noise:
   condition changes + negotiation variance). This number goes into the skill's honest
   accuracy statement and caps what any model may claim.
5. Interval baseline: comp-IQR bands (expect them broken, as condo's were at 43% — the
   calibrated fix is L3's conformal).

**Guardrails.** Fit nothing in L1; leakage checklist signed; **per the condo G1 lesson, the
gate criteria are median + TAIL + coverage + calibration together — the median rule alone
mis-measured last time.**

**Deliverables.** EXP-0010 leaderboard + slices + THE BAR + noise floor · decision memo:
which L2 modules open, with the error evidence that opens them.

**Gate GL1.** Leaderboard reproducible & lag-stable; bar/tail/coverage/noise-floor recorded;
L2 selection justified by error mass against documented thresholds.

**→ OUTCOME (2026-07-16): PASS — EXP-0010.** Bar = **LC1 craft 10.51% @ 87.3% cover**
(tail: LB4 kNN p90 0.310); noise floor **~5.3-6.2%/print** (only ~4-5pp closable — honest
accuracy is structurally high-single-digit); lag 42≡56 (month-end arithmetic), 70d +0.03pp;
IQR intervals 38-50% (broken, as condo's were). Error mass: plot size monotone 8.8%→41%
(15k+), Detached 17.2%, GCB 30%, cross-street kNN 6-10× on short-lease (sub-2M 232% —
lease control MANDATORY cross-street). L2 opens: **L2a (mandatory) + L2c (lease-matched
retrieval) first**, L2d anchors for coverage, L2b cheap, L2e bounds; Detached ≥8k /GCB →
case-tier. Full memo in EXP-0010.

---

## L2 — Error-driven method work (est. 1–2 sessions; worktree fan-out per the R3 pattern)

Pre-scoped modules — open only what GL1's error mass justifies; each runs the 10-step loop
to a verdict (ACCEPT / ACCEPT-WITH-SCOPE / MONITOR / REJECT → graveyard).

- **L2a Land-size curve (expected mandatory — the landed elasticity lesson):** marginal land
  value; price = f(land area) as log-log elasticity by type × tenure × segment, fitted from
  same-street near-simultaneous different-size pairs + a pooled hedonic cross-check. A
  1,600 sqft terrace plot must never price a 7,000 sqft detached (the condo shoebox lesson,
  transposed). Kills or scopes "flat average land psf" with numbers (mandate 6c).
- **L2b Time adjustment:** island landed PPI vs segment sub-indices vs local fitted trend vs
  same-plot repeat-sales signal. Hypothesis from the factor study (asymmetric capture
  0.95/0.74): landed lags downside — test, don't assume.
- **L2c Retrieval/pooling:** spatial-kNN vs street-cluster (enclave) pooling weights;
  validated ONLY through backtest accuracy (geography earns its keep via retrieval, never
  via clustering scores).
- **L2d Pooled/hedonic anchors:** A2-style shrinkage (street→district→segment) + a hedonic
  log(price) anchor. **Expectation set by the condo reversal: anchors buy COVERAGE and
  hard-case detection, not point accuracy where local comps exist.** Stated up front so
  nobody re-learns it expensively.
- **L2e Improvement-contribution bounds (the identification problem):** residuals vs the
  land model; same-plot long-gap jumps as rebuild signals. MEASURE what URA can and cannot
  resolve → the ±X% condition band the skill will carry. A verdict of "bulk-unresolvable
  beyond ±X% — case-tier input required" is a legitimate, publishable outcome.

**Guardrails.** Forward-chained folds only; graveyard-first; fan-out agents build+backtest
in worktrees with adversarial verify; the orchestrator re-verifies from the journal (the
workflow-death lesson); every rejected method → graveyard with numbers.

**Deliverables.** EXP-001x per module · verdicts · fitted curves in feature evidence ·
graveyard entries.

**Gate GL2.** Every opened module has a verdict; the land-size curve is ACCEPTed or its
absence is justified with numbers.

---

## L3 — Landed engine + calibrated uncertainty (est. 1 session)

**Plan.**
1. **Engine LV1** = best local-comp method (size curve + time adjustment + pooling) where
   street/local comps exist → pooled fallback for coverage (100% answer rate), mirroring
   the condo "best-method-where-it-applies + fallback + calibrated band" architecture that
   beat the blends.
2. **Split-conformal intervals** per cell — candidate cells (street-liquidity × type) or
   (segment × type); use whichever has n≥50 per cell; **fingerprint discipline from day
   one** (table stamped with the point-method sha1; red test on drift).
3. Hard-case honesty ported: anchor-disagreement flag, freshest same-street same-size
   reference, directional stale-comp flag, smooth confidence.
4. **Condition input hook:** user-supplied building state (original / renovated / rebuilt
   + year) shifts the POINT only per L2e-validated effects; otherwise the band widens by
   the measured ±X%. Unknown building state is never silently ignored.

**Gate GL3.** LV1 ≥ bar on median OR tie with materially better tail/calibration; interval
coverage 80%±5pp; every estimate decomposes (land baseline → adjustments → condition band);
claimed accuracy respects the L1 noise floor.

---

## L4 — `landed-valuation` skill ship (est. 1–1.5 sessions incl. review loop)

**Plan.**
1. Production entry `value_landed`: input = street + land area (+ type, tenure; optional
   exact address→OneMap geocode, GFA, condition/rebuilt-year, asof). **Live-vs-
   reconstruction as-of semantics from day one** (the condo EXP-0008 lesson — no blanket
   caveat-lag on live valuations).
2. Output: land-value baseline · explicit improvement/condition treatment · conformal fair
   range · smooth confidence · comps + anchor reads · buyer/seller guidance separated from
   fair value · **mandatory verification list = engine flags ∪ `landed-property-due-diligence`
   checklist heads** (INLIS title, road reserve/drainage, GCBA / landed-housing-area rules,
   setbacks, conservation) — the existing skill becomes the verification layer, referenced
   not duplicated.
3. **Scope declaration (honest):** pure landed only; strata-landed declines with a routing
   note; GCB/luxury detached = wide-band + case protocol (possibly ACCEPT-WITH-SCOPE-LIMIT:
   "indicative only"); redevelopment optionality is verification-gated language, never
   priced as fact.
4. **Regression suite** (structural asserts on real archetypes): liquid OCR terrace street ·
   thin GCB detached · short-lease landed · strata-landed (must decline + route) · unknown
   street (escalates) · condition input shifts point only where validated · irregular/corner
   (case-tier escalation note).
5. **Field trials ≥3, including the Cardiff Grove #19 cross-check** against the PASS-8.5
   craft valuation (agreement/divergence analyzed, not assumed), plus a Nanyang/Rosyth-area
   terrace and one thin case.
6. Hostile review loop — fresh reviewer each round — to **PASS ≥8.0**.
7. Disposition executed: `landed-investment-analysis` keeps its beta/strategy framing, its
   land-psf pricing core re-based on LV1; `landed-area-research` / `screen-landed-listings`
   unchanged (area/listing layers).

**Gate GL4 (ship bar).** Beats the landed bar on ≥70% of major slices, no major slice >1.3×
worse; regression suite green; field trials + Cardiff cross-check documented; hostile PASS
≥8; **published achievable-accuracy statement** (median APE + noise floor + band coverage).

---

## After L4 → operations (one runbook, both skills)

Monthly refresh: pull → audit-lite → rolling re-validation (condo AND landed) → conformal
recalibration when fingerprints demand → drift report vs frozen baselines → registry sync.
Quarterly: MONITOR verdicts re-tested; snapshot archive (rolling window drops old months).

## Condo & new-launch backlog (FROZEN 2026-07-16 — nothing ships without its gate)

1. Apply fitted-but-deferred constants (EXP-0008: FLOOR_PP 0.004, CCR elasticity −0.016) →
   recalibrate conformal (fingerprint test enforces) → re-verify leaderboard → update SKILL.
2. R4 IS bridge: guided-harvest skill v2 + URA↔IS reconciliation + unit/stack premiums —
   automates the condo skill's manual hard-case corroboration; later also serves landed
   condition evidence (IS has per-property detail URA lacks).
3. Hard-case blend rule (50/50 toward fresh print): validate or bound on a backtest slice.
4. Strata-landed sub-market: give it a home (thin condo-engine variant) — currently orphaned.
5. R7 new-launch programme (premium persistence + developer ladder are URA-backtestable;
   plan in v1/git history — five-quantity separation discipline unchanged).
6. Listing evidence (MONITOR tier); strategy-layer re-basing on shipped engines.

## Cross-cutting guardrails (unchanged, binding on the L-track)

1. As-of firewall everywhere; new sources declare publication lag before entering the store.
2. Time-forward validation only; full-history artifacts banned unless as-of rebuilt.
3. Benchmark discipline + graveyard-first; every verdict logged.
4. Simplicity preference — complexity must beat the simple method robustly, or the simple
   one ships (the condo blends died this way; expect the same for landed).
5. No fabricated adjustments — an uncalibrated factor is "unresolved → widen band or ask";
   for landed this SPECIFICALLY covers plot geometry, condition, and redevelopment premium.
6. Label epistemic status: verified fact · empirical finding · convention · hypothesis ·
   open question · judgement.
7. Fleet budget: sonnet gatherers/devs, Fable for design/diagnosis/verdicts; heavy flows
   sequenced; orchestrator re-verifies fan-out results from the journal.
8. stdlib-first; heavy deps behind extras; full backtest ≤15 min or add indexes; every
   experiment = script + registry entry + reproducible data.
9. Nothing deprecated until its successor is proven (harness + regression suite); every
   material change → changelog; conformal tables carry code fingerprints.
10. Secrets never in git.

## Skills disposition (updated)

| Skill | Disposition | Phase |
|---|---|---|
| `condo-resale-valuation` | SHIPPED; frozen (backlog gated) | done |
| `value-a-property` | superseded; IS corroboration reference | done |
| `landed-investment-analysis` | beta/strategy framing kept; land-psf pricing core re-based on LV1 | L4 |
| `landed-property-due-diligence` | checklist survives AS the L4 verification layer (referenced) | L4 |
| `landed-area-research` / `screen-landed-listings` | unchanged (area / listing layers) | — |
| `read-investment-suite` / `harvest-scrolling-android-table` | rewrite parked with R4 | parked |
| `new-launch-research` | replaced when R7 unparks | parked |
| `condo-investment-analysis` / `property-buy-sell-advisory` | strategy layer; re-base post-ops | parked |
| `property-report-review` | unchanged — the acceptance gate for L4 | active |

## Mandate coverage — landed programme

| Mandate (Landed A–F) | Where |
|---|---|
| A value geography | L1 pooling benchmarks + L2c (validated via retrieval only) |
| B comparable selection | L1 LB1–LB4 + L2c |
| C nonlinear land value | L2a (the expected-mandatory module) |
| D plot geometry | L4 case-tier + verification list — bulk-unobservable, DECLARED, never invented |
| E improvement contribution | L2e bounds + L3 condition hook |
| F redevelopment optionality | L4 verification-gated language, never priced as fact |

## Honest limits (landed-specific)

- **Bundle identification:** URA price = land + building, not decomposable in bulk → an
  irreducible error band the skill must publish (L1 noise floor). Landed's bar will sit
  structurally above condo's 3.7% — that is honesty, not failure.
- **Geometry blindness:** frontage/shape/corner absent from every bulk source → the bulk
  model carries declared geometry noise; case tier (site/INLIS/photos) resolves it per deal.
- **GCB/luxury detached:** thin and idiosyncratic → wide bands + case protocol, possibly
  scope-limited "indicative".
- **FH-dominated slow market in a 5y window:** regime conclusions scoped to 2021–2026.
- **Same-plot matcher** may err on subdivisions/re-surveys — spot-check discipline.
- Session estimate: **~4.5–6 sessions to a shipped landed skill** (infrastructure reuse is
  why this is less than condo's path).
