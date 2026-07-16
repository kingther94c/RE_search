# Program roadmap v1 — research-to-skill (R0–R8)

_2026-07-15 · planned on Fable 5 · status: ACTIVE v1. This is the operating document for
every future session: pick the current phase, check its gate, work its plan. Amend via
changelog, not silently._

## The architectural pivot (what "大刀阔斧" means, precisely)

1. **The core of valuation moves to data.** Methods are developed and judged on the URA
   caveat spine via the walk-forward harness (`researcher/backtest`) — not authored as
   craft and defended by narrative.
2. **Investment Suite is repositioned, not abandoned.** It stops being the center of the
   condo skill and becomes (a) the **calibration layer** — exact floor, stack, rents,
   realised repeat pairs that URA structurally lacks (URA has no unit ids, floor bands
   only, month-granular dates) — and (b) **live enrichment** at production time. Because
   IS's depth is gated on extraction quality, a guided-harvest skill rewrite is a
   first-class work-line (R4), per the user's own diagnosis: "the bottleneck is that no
   good skill guides the search."
3. **Existing skills are candidates and adapters, not the spec.** The `value-a-property`
   grid enters the leaderboard as candidate C1. Landed/new-launch skills keep their
   verification checklists; their valuation cores get replaced by whatever survives.
4. **Nothing is deleted until beaten.** Deprecating an incumbent requires its successor
   to beat it on the harness AND pass the regression suite (guardrail 9).

## Status & priority (updated 2026-07-16)

> **PRIORITY PIVOT (user decision 2026-07-16): LANDED FIRST.** Condo and new-launch pause —
> development AND iteration — and move to the backlog below. **R6 is the active phase.**

| Phase | Status | Gate outcome |
|---|---|---|
| R0 data foundation | **DONE** | G0 PASS (136,436 caveats / 61 months / 61k condo subjects; EXP-0002) |
| R1 condo baseline | **DONE** | Bar = 4.1% median APE (C1≈B3). **G1 amended, on the record:** the median rule opened nothing; tail + interval calibration + same-project dependency became the R3 targets (EXP-0003) |
| R2 bake-offs | **FOLDED into R3/EXP-0007** | full bake-offs skipped by evidence (same-project dominates); elasticity & floor-premium re-fits delivered the 2c substance; 2a/2b remain unopened — reopen only on demonstrated error mass |
| R3 engine v2 | **DONE** | G3 MET (V2 = C1 + lease-aware fallback + conformal; 3.71% median / 100% cover / ~82-85% held-out interval; EXP-0004/5/6) |
| R4 IS calibration bridge | **PARKED** (was next; superseded by the pivot) | — |
| R5 condo skill | **SHIPPED** | G5 PASS 8.7/10 (4 hostile rounds; EXP-0007/0008). **Sequence deviation, on the record:** shipped BEFORE R4 with IS corroboration as a mandatory MANUAL step |
| **R6 landed** | **← ACTIVE** | see kickoff below |
| R7 new-launch | **PARKED** | — |
| R8 operations | **NOT STARTED** | snapshot archive exists; monthly refresh runbook pending |

Reality check vs estimates: R0–R5 (condo line) took ~2.5 sessions vs the 6–10 estimated —
gates and evidence-driven skips (G1, R2) did the shortening, as designed.

### Condo & new-launch backlog (frozen 2026-07-16 — nothing here ships without its gate)
1. Apply the **fitted-but-deferred constants** (EXP-0008): FLOOR_PP 0.004, CCR elasticity
   −0.016 → recalibrate conformal (fingerprint enforces this) → re-verify leaderboard.
2. **R4 IS bridge**: guided-harvest skill v2 + URA↔IS reconciliation + unit/stack premiums —
   automates the manual IS-corroboration step the condo skill mandates on hard cases.
3. Hard-case blend rule (50/50 toward fresh print) — validate or bound it on a backtest slice.
4. Listing evidence (MONITOR tier), strategy-layer re-basing (R8 items).
5. R7 new-launch programme (premium persistence + developer ladder are URA-backtestable).

## North star (mandate, condensed)

> For a specific Singapore property, using only information available at the valuation
> date: the most reliable estimate of worth, the explanation, quantified uncertainty,
> and actionable buyer/seller price guidance. **Defensible + transparent + empirically
> validated + actionable** — not "the most sophisticated AVM we can build."

The mandate's 10-point acceptance standard maps to phases as follows: (1) documented
methodology → registry, all phases; (2) known assumptions → feature evidence; (3)
benchmark comparison → R1; (4) time-consistent OOS validation → R1–R3; (5) error slices
→ R1/R2; (6) honest uncertainty → R3; (7) explainable from observable evidence → R3
anchor traces + R5 hostile review; (8) fact/assumption/judgement separation → guardrail
6; (9) buyer/seller guidance separated from fair value → R5/R7 skill specs; (10)
converged refinement → the gates + R8 re-validation cadence.

## Phase overview

| Phase | Focus | Est. sessions | Hard dependency | Parallel notes |
|---|---|---|---|---|
| R0 | Data foundation completion (real pull + audit) | 1 | — | — |
| R1 | Condo baseline: first honest leaderboard | 1–2 | G0 | — |
| R2 | Error-driven method bake-offs | 2–4 | G1 | interleaves with R4 |
| R3 | Multi-anchor + ensemble + uncertainty (engine v2) | 1–2 | G2 | interleaves with R4 |
| R4 | IS calibration bridge + guided-harvest skill v2 | 2–3 | G0 | emulator-bound; runs alongside R2/R3 |
| R5 | `condo-resale-valuation` skill v1 ship | 1–2 | G3 + G4 | — |
| R6 | Landed programme | 2–3 | G0 (6c can start after G1) | bulk parts pre-startable |
| R7 | New-launch programme | 2 | R3 engine for 7a | — |
| R8 | Operationalization (living system) | 0.5 + ongoing | G5 | — |

Total ≈ **12–18 sessions**; gates can shorten it (a gate that says "simple already wins"
skips work — that is a success, not a failure).

---

## R0 — Data foundation completion

**Research direction.** None — engineering + audit. Make the spine trustworthy before a
single conclusion is drawn.

**Plan.**
1. Full 4-batch pull (batch 1 alone = 20,548 caveats / 292 projects, 2021-07..2026-07;
   expect ~60–90k total — verify, don't assume).
2. Coverage & anomaly audit: months × segment × property-type counts; project-count
   sanity vs the known universe (~2–3k active projects); psf outlier scan (flag <$500,
   >$6,500); duplicate detection.
3. Exclusion rules, documented: `no_of_units > 1` (bulk/en-bloc deals) out of subjects
   AND comps; `typeOfArea='Land'` rows inside condo developments (townhouses) bucketed
   as landed; EC already excluded from the private-condo universe.
4. Caveat-lag sensitivity: leaderboard at 42/56/70 days — ranking must be stable.
5. Perf pass: month/project indexes if the full run exceeds ~15 min (stdlib-first;
   heavy deps only behind pyproject extras).
6. Snapshot versioning decision: gzip the normalized store (~5–10 MB) vs pinned
   regeneration recipe + cache. Either way, backtests must be reproducible.
7. `data_sources.md` in the registry: every source's fields, publication lag, terms
   (URA requires attribution), refresh cadence, rolling-window implications.

**Guardrails.** Verify-before-trust on every field (the smoke test already caught
landed spellings and the EC contamination). No analytical conclusions in R0.

**Deliverables.** Populated store · audit report (EXP-0002) · data dictionary ·
exclusion rules.

**Gate G0.** ≥48 usable months; ≥20k resale-condo subjects; ≥800 projects; test suite
green; exclusions documented. Fail → escalate data strategy (e.g. REALIS export) before
any research proceeds.

---

## R1 — Condo baseline: the first honest leaderboard

**Research direction.** What accuracy do *simple, practically-knowable* methods already
achieve; where exactly do they fail; and does the existing craft engine actually beat
them?

**Plan.**
1. Port the `value-a-property` adjustment grid to URA data as **C1_grid_adapted**
   (PPI time adjustment, floor-band midpoint, size elasticity −0.08) — the mandate's
   "treat existing skills as candidate baselines," made literal.
2. Walk-forward B1–B5 + C1 over all eligible resale-condo subjects. Subject window
   starts ≥18 months into the data so early subjects aren't history-starved.
3. Slice per the mandate: segment, district, quantum band, size band, floor band,
   tenure, project liquidity (same-project comp count), lease age, market regime
   (2022 run-up / 2023–24 cooling measures / 2024–26), plus decline analysis (when do
   B1/B2 refuse to answer?).
4. **Set THE BAR:** best-benchmark median APE, overall and per major slice, written
   into the registry. Every later method is measured against this number.
5. Bilingual HTML leaderboard report for Kelvin (deliverables builder).

**Guardrails.** Fit nothing in R1 (no tuning on the full set); leakage checklist
(EXP-0001 notes 1–4) executed and signed in the registry entry; lag-stability from R0
carries over.

**Deliverables.** EXP-0003 leaderboard + slices + the bar · decision memo naming which
R2 bake-offs open, with the error evidence that opens them.

**Gate G1.** Leaderboard reproducible and lag-stable. Slices with median APE >1.5× the
liquid-slice bar open the corresponding R2 modules. If nothing exceeds 1.5×, skip
straight to R3 with benchmarks as the engine core — a legitimate outcome.

---

## R2 — Error-driven method bake-offs (only what G1 opened)

**Research direction.** Four pre-scoped modules, each run as the mandate's 10-step loop,
each ending in a verdict (ACCEPT / ACCEPT-WITH-SCOPE / MONITOR / REJECT → graveyard).

- **2a Time adjustment** (shared M2): PPI-ratio vs stratified hedonic time effects vs
  fitted local trend (port of the trend ladder) vs hierarchical shrinkage (parent index
  + local relative value). Note: clean repeat-sales is IMPOSSIBLE on URA (no unit ids)
  — approximate via project+area+floor-band fuzzy pairs and measure the precision of
  that matching; true repeat pairs come from IS in R4.
- **2b Comparable retrieval + geography** (shared M1 + condo A): rule hierarchy vs
  weighted similarity vs geography-graph neighbours. Geography candidates (official
  hierarchy prior / price-co-movement clustering / substitutability KNN) are validated
  **through retrieval improvement**, never on clustering scores — exactly as the
  mandate demands. Every geography artifact must be as-of rebuildable (rolling
  re-cluster); full-history clusters are banned from the harness.
- **2c Comparable adjustment** (condo B): floor-band curve (linear vs spline vs
  per-band); size elasticity fitted per segment vs the global −0.08; lease-decay curve
  (empirical, not assumed 15%); TOP-cohort effect. Explicit transparent forms
  preferred; an ML residual adjuster runs as challenger only.
- **2d Hedonic/ML AVM anchor** (condo D): transparent hedonic (log-psf, splines) vs
  mixed-effects with project random effects (partial pooling) vs gradient boosting
  (extras-gated dependency). Features include an **as-of amenity table** — MRT station
  openings are dated (TEL stages 2019–2024), so MRT distance can be time-correct;
  school distances stay time-invariant with a labelled caveat.

**Plan.** Open only G1-flagged modules, sequenced by error mass (expected: 2a + 2b
first). Each module: hypothesis → ≥3 materially different methods → benchmark →
walk-forward → slices → counterexample search → diagnosis → refine → revalidate →
verdict.

**Guardrails.** Forward-chained time folds ONLY — random CV is banned program-wide.
Sonnet fleet for grunt runs, Fable for design/diagnosis/verdicts (budget lesson).
A win must be robust: stable across lag settings and regimes, and not bought with >10%
degradation on any major slice. Every rejection → graveyard with numbers.

**Deliverables.** One EXP entry per module with verdicts · geography registry updated ·
feature-evidence entries (floor/size/lease/age curves with scopes).

**Gate G2.** Every opened module has a verdict. If nothing earns ACCEPT, R3 proceeds on
benchmarks + C1 and the program's honest finding is "simple wins so far."

---

## R3 — Multi-anchor consolidation, ensemble, uncertainty → condo engine v2

**Research direction.** Combine evidence families without pretending independence;
produce calibrated intervals and an explainable confidence score.

**Plan.**
1. Onboard **official rental evidence**: extend `ura.py` to URA's rental service
   (median rents by project, declared publication lag) → rental-implied anchor. Test
   its incremental value AFTER comps + AVM are in (mandate E: downweight if it adds
   little — don't keep it for theoretical completeness).
2. Listing evidence: MONITOR tier only (portal Tier-2, fragile scraping); full
   treatment belongs to the strategy layer post-R5, where asking/DOM data plausibly
   matters more than for fair value.
3. Family consolidation: best-within-family first (from R2), then family-level
   estimates: direct comps · substitute-project transfer · AVM · rental.
4. Ensemble bake-off in mandated order: best single anchor and simple average/median
   (as benchmarks) vs error-weighted vs evidence-state rules (comp count, recency,
   similarity, liquidity) vs stacking (time folds) vs mixture-of-experts. Expected
   winner at current data scale: evidence-state rules. Complexity must earn its keep.
5. Uncertainty: conformal-style intervals from rolling OOS residuals, calibrated per
   liquidity × segment cell; 80% nominal coverage target; confidence score =
   f(data quality, comp similarity, model agreement, liquidity, uniqueness) that maps
   to interval width honestly.
6. Anchor-disagreement analytics: divergence >X% flags "hard case" → production
   escalation path.

**Guardrails.** Anchors share data — measure their correlation; never average
correlated anchors and call it diversification. Ensemble ships only on G3 criteria.

**Deliverables.** Condo engine v2 + EXP entry + calibration tables in the registry.

**Gate G3.** v2 beats the best single anchor on median APE, OR ties within noise while
materially improving P90 / interval calibration. Interval coverage 80% ± 5pp across
major slices. Every estimate decomposable into its anchor trace.

---

## R4 — IS calibration bridge + guided-harvest skill v2 (parallel with R2/R3)

**Research direction.** (a) Systematize extraction of IS's depth — the user-named
bottleneck; (b) quantify what IS adds over URA; (c) estimate the unit/stack premiums
URA structurally cannot see.

**Plan.**
1. **4a Harvest skill rewrite** — `read-investment-suite` v2: goal-conditioned recipes
   ("for a calibration panel: these tabs, these windows, this order"), coverage
   checklist, throughput + failure-mode playbook (emulator windowed-visible), resumable
   harvest state. The bar: a sonnet agent executes the SKILL.md end-to-end unaided.
2. **4b URA↔IS reconciliation:** stratified calibration panel (30–60 projects across
   segment × liquidity × age — NOT the full-history-biased 27-project panel; selection
   pre-registered). Match IS records to URA caveats (project+month+price+area);
   quantify match rate, floor-band→exact-floor distributions, IS-only field value;
   extend the AVM-vs-caveat bias study (known non-directional: −3.4%/+1.4%/+3.7%) to
   panel scale.
3. **4c Unit/stack premiums** (condo C): with exact floors/stacks and realised repeat
   pairs — within-project residuals vs a project-time baseline; partial pooling across
   projects (regional priors); persistence tests (split-half by time; a "stack premium"
   that doesn't persist is transaction noise, per the mandate); floor-curve functional
   forms (linear / spline / view-clearance discontinuity).

**Guardrails.** Panel selection pre-registered (no cherry-picking). IS numbers
timestamped — Est. Val is LIVE, so snapshot discipline. Emulator sessions budgeted and
sequenced (heavy-flow lesson). Calibration factors enter production only via
feature-evidence entries with confidence labels.

**Deliverables.** Skill v2 · calibration panel dataset · reconciliation report (EXP) ·
stack/floor premium models with scope limits.

**Gate G4.** ≥80% IS↔URA match rate on the overlap window; premium estimates pass
persistence tests; harvest skill executed end-to-end by a non-Fable agent on ≥3
projects it hasn't seen.

---

## R5 — `condo-resale-valuation` skill v1 (production ship)

**Research direction.** None new — conversion and reliability engineering.

**Plan.**
1. Author the skill to the mandate's spec: required/optional inputs; source priority
   (URA spine + IS enrichment + official policy facts); market hierarchy; retrieval;
   adjustments; independent anchors; ensemble logic; uncertainty; buyer guidance and
   seller guidance **separated from fair value**; mandatory verification items; output
   format; failure/escalation conditions.
2. **Regression suite:** the mandate's case list (liquid standard · boutique illiquid ·
   unusually large units · penthouse · low-floor road-facing · sea view · old freehold ·
   short remaining lease · …) as executable case files with expected analytical paths,
   anchors to downweight, expected confidence behaviour, known failure modes. Wired to
   rerun on ANY skill update; an update that breaks a previously-green case does not
   ship.
3. Field trial: ≥2 real properties end-to-end; hostile review (property-report-review)
   to PASS ≥8/10.
4. Execute disposition: `value-a-property` marked superseded (kept as engine-room
   reference until G5 sign-off).

**Guardrails.** Ship scope-limited first — default recommendation: liquid private
condos with ≥N same-project comps; boutique/penthouse cases run in "wide-band +
escalation" mode. No capability claims beyond validated scope.

**Deliverables.** The skill · regression suite · bilingual launch report · changelog.

**Gate G5 (ship bar).** Beats the best benchmark overall AND on ≥70% of major slices;
no major slice >1.3× worse than its benchmark; regression suite green; field-trial
PASS; interval calibration from G3 holds on trial cases.

---

## R6 — Landed programme ← ACTIVE (kickoff grounded 2026-07-16)

**Data reality (measured on the pulled store — shapes every design choice below):**
- **12,849 landed caveats / 12,115 resale subjects** (~199/mo island-wide) — island-level
  walk-forward is viable; per-street it is NOT: **1,072 streets, median 5 caveats/street
  over 5 years** (p90 = 30). Partial pooling toward enclave/planning-area is MANDATORY,
  not optional; a "street median" benchmark will mostly decline.
- **11,236 `type_of_area='Land'` rows (87%): psf = LAND psf, area = land area** (p50 2,640
  sqft, p95 7,622). The remaining 1,613 strata-landed (cluster housing) trade on strata
  area — a SEPARATE bucket, do not mix (R6a decision, audit item: 15 stray 'Apartment'
  rows inside the landed slice need a rule).
- Tenure: 68% freehold + 14% 999yr — tenure splits are viable. Segment: OCR 8,593 /
  RCR 2,484 / CCR 1,772. Type: Terrace 6,003 / Semi-D 3,648 / Detached 1,570.
- **First moves:** 6a landed store slice + hygiene (strata-landed split, Apartment rows,
  psf-band for land-psf ≠ condo band) → landed benchmarks (enclave/planning-area median
  land-psf time-adjusted, nearest-street transfer, type×tenure pools) → walk-forward
  leaderboard = the landed bar → 6c land-value curve (price = f(land area), bulk-testable).
  Reuse the harness as-is; only benchmarks and hygiene are landed-specific.

**Research direction.** Plot-first valuation where the quant loop is thinner. What can
bulk URA landed caveats actually validate (land-value curves, time adjustment, enclave
effects) — and what must remain case-based discipline (geometry, improvement,
redevelopment)?

**Plan.**
1. **6a Spine:** landed store slice (`typeOfArea='Land'` + landed types; area = LAND
   area, so psf = land-psf — consistent with the existing land-psf craft). Enclave /
   street keying from street names + SVY21 coords.
2. **6b Benchmarks + walk-forward:** street/enclave median land-psf (time-adjusted) ·
   planning-area fallback · nearest-street transfer. Publish an honest achievable-
   accuracy statement (median APE likely 8–12%; wide intervals are the CORRECT output
   here, not a failure).
3. **6c Nonlinear land value** (bulk-testable; can pre-start after G1): price = f(land
   area) by type × tenure × region — linear-psf vs log-log vs spline vs piecewise;
   marginal-sqft value curves; a verdict on the scope where "average land psf" is
   admissible (the mandate's explicit question, answered with data).
4. **6d Improvement & optionality (case tier):** residual = price − land-model →
   improvement-contribution classes; rebuild-probability framing (move-in / reno / A&A
   / rebuild as probability-weighted buyer use cases); redevelopment optionality stays
   a verification-gated checklist (URA Master Plan GPR/height from official sources) —
   never priced as fact before planning constraints are verified.
5. **6e Skill + refactor:** `landed-valuation` skill (plot-first per mandate spec);
   existing landed trio refactored — checklists survive, valuation cores swapped;
   regression cases (small terrace / GCB / corner / irregular plot / rebuild candidate
   / recently rebuilt).

**Guardrails.** n is small: mandatory partial pooling toward parent geographies;
per-street conclusions require a minimum-n; case regression carries equal weight to the
backtest in this programme; geometry/condition factors only from feature-evidence
entries — otherwise "unresolved → widen band or ask."

**Deliverables.** Landed leaderboard · land-curve study (EXP) · skill · regression suite.

**Gate G6.** Beats the naive enclave-median benchmark; achievable-accuracy statement
published; the skill REFUSES (escalates to case protocol) on out-of-scope plots rather
than guessing.

---

## R7 — New-launch programme

**Research direction.** Separation of quantities — now with real empirics. **Upgrade to
the earlier position** ("mostly case-based"): the 5-year window contains 2021–22
launches that TOP'd and resold by 2024–26, and URA new-sale caveats ARE in the data →
newness-premium persistence and developer price ladders are directly measurable. The
final fair-value synthesis remains judgement-labelled; its components get backtests.

**Plan.**
1. **7a Resale-equivalent value:** condo engine v2 on the substitute resale set (nearby
   recent-TOP + same buyer-market projects); new-vs-resale matched pairs.
2. **7b Premium persistence (the natural experiment):** launch prices (new-sale
   caveats) vs same-project post-TOP resales, controlled for market movement (index)
   and floor-band/size mix → classify durable project-quality premium vs evaporating
   launch premium.
3. **7c Developer price ladder:** per-project new-sale caveat timelines, mix-controlled;
   onboard URA's monthly developer-sales survey (declared publication lag) for
   sell-through; test whether sell-through has incremental predictive power AFTER mix +
   market controls (the mandate's causality warning, implemented).
4. **7d Unit relative value:** the developer's own sold-price grid + IS stack data →
   a two-unit comparison framework ("which of these two available units is better value
   at list") — often the commercially decisive output.
5. Skill v1: must output the five separated quantities — resale-equivalent FV ·
   sustainable project premium · unit adjustment · expected developer execution price ·
   quoted-price gap — and must be able to say "the developer can sell at X, and X is
   above underlying fair value."

**Guardrails.** Never conflate pricing power with fair value. Premium components carry
durability evidence labels. Ladder models tested against mix-shift confounds. Case
regression on live launches: first weekend / high sell-through / heavy unsold inventory.

**Deliverables.** Premium-persistence study (EXP) · ladder study · skill · regression cases.

**Gate G7.** The five quantities separately reported and reconciled on ≥3 live
launches; every premium claim carries cohort evidence; hostile review PASS.

---

## R8 — Operationalization: the living system

**Plan.** Monthly refresh runbook: pull → audit-lite → rolling re-validation → drift
report vs frozen baseline; alarm when the engine degrades vs benchmarks on fresh
months. Quarterly registry review (MONITOR verdicts re-tested). Strategy-layer refresh:
`property-buy-sell-advisory` and `condo-investment-analysis` re-based on v2 valuations,
with the factor/beta work rebuilt as-of before it re-enters. Memory/registry sync.

**Guardrails.** The rolling URA window silently DROPS old months — archive snapshots so
past backtests stay reproducible. Changelog for every material change. No skill edit
ships without its regression rerun.

**Deliverables.** Refresh runbook (scheduled) · drift dashboard (simple) · quarterly
review template.

---

## Cross-cutting guardrails (all phases)

1. **As-of firewall everywhere.** All research reads through `store.as_of`. Any new
   source declares its publication lag BEFORE entering the store.
2. **Time-forward validation only.** Forward-chained folds; random K-fold is banned.
   Full-history artifacts (enriched panels, clusters, embeddings) are banned from the
   harness unless as-of rebuilt.
3. **Benchmark discipline + graveyard-first.** Read the graveyard before proposing.
   No method advances on in-sample results or intuition. Every verdict logged.
4. **Simplicity preference.** The complex method must beat the simple one robustly
   (stability across regimes and slices, better tails, or better calibration) — or the
   simple one ships.
5. **No fabricated adjustments.** An uncalibrated factor is "unresolved" → wider
   interval or an information request. Never a made-up percentage.
6. **Label epistemic status** in every report: verified fact · empirical finding ·
   professional convention · hypothesis · open question · judgement.
7. **Fleet budget.** Sonnet gatherers ×3–4 for harvest/grunt runs; Fable for synthesis,
   diagnosis, verdicts, hostile critique. Heavy workflows sequenced, not exploded.
8. **Engineering discipline.** stdlib-first; heavy deps behind pyproject extras; full
   backtest run ≤15 min or add indexes; every experiment = script + registry entry +
   reproducible data (snapshot or pinned recipe).
9. **Nothing deprecated until its successor is proven** (harness + regression suite).
   Every material change → changelog entry.
10. **Secrets never in git.** Access keys live in env or `research/.secrets/`
    (gitignored). A private repo is NOT a secret store.

## Existing skills — disposition

| Skill | Disposition | Phase |
|---|---|---|
| `value-a-property` | candidate C1 in the leaderboard; superseded by `condo-resale-valuation` at G5 | R1 → R5 |
| `read-investment-suite` | rewritten as guided-harvest v2 (goal-conditioned recipes) | R4a |
| `harvest-scrolling-android-table` | kept as low-level primitive under v2 | R4a |
| `condo-investment-analysis` | strategy layer; re-based on engine v2 + as-of factor rebuild | R8 |
| `property-buy-sell-advisory` | strategy layer; re-based on v2 valuations | R8 |
| `landed-area-research` | checklists kept; valuation core replaced | R6e |
| `landed-property-due-diligence` | verification checklist survives; pricing sections re-based | R6e |
| `landed-investment-analysis` | beta/asymmetric-capture read kept as prior; land-psf method superseded by 6c curves | R6e |
| `screen-landed-listings` | becomes the listing-evidence adapter (Tier-2) | R3 / R6 |
| `new-launch-research` | replaced by `new-launch-valuation` (research steps absorbed) | R7 |
| `property-report-review` | kept; extended with registry-consistency checks (report claims must match feature evidence) | R5+ |

## Mandate coverage map

| Mandate element | Where |
|---|---|
| Shared M1 value geography | R2b (validated via retrieval) + geography registry; landed variant R6a/6b |
| Shared M2 time adjustment | R2a; landed R6b |
| Shared M3 evidence families | R3 |
| Condo A retrieval / B adjustment / C unit-stack / D AVM / E rental / F listing | R2b / R2c / R4c / R2d / R3 / R3-MONITOR + strategy layer |
| New launch A–D | R7a–d |
| Landed A–F | R6a (A) · R6b (B) · R6c (C) · R6d (D, E, F — case tier) |
| Ensemble research | R3 |
| Validation protocol | R0/R1 + every gate |
| Benchmark discipline | guardrail 3 + R1's bar |
| Iterative research loop | R2 / R4 / R6 / R7 method work |
| Skill production spec | R5 / R6e / R7.5 |
| Reliability regression suite | R5.2, R6e, R7.5 + guardrail 9 rerun rule |
| Research artifacts | the registry (live since Module 0) |

## Program-level risks & honest limits

- **URA granularity bounds precision:** month-only dates, floor bands, no unit ids —
  time precision and unit precision have hard floors without IS (hence R4).
- **Rolling 5-year window:** no 2018-cooling or COVID-crash regime in transaction data;
  regime conclusions are scoped to observed regimes (2021–2026). SingStat indices give
  longer context, but not at transaction level. Archive snapshots from day one (R8).
- **New-launch fair value has no direct OOS truth.** We backtest its components
  (premium persistence, ladder) and label the synthesis as judgement. No pretending.
- **Landed accuracy floor is structurally higher.** The skill's value is discipline +
  verification + honest bands, not false precision.
- **Key-person risk:** IS account + emulator are single-path; harvest skill v2 reduces
  the bus factor.
- **Session budget:** 12–18 sessions estimated. Gates exist to shorten, not lengthen:
  every "simple wins" verdict skips a bake-off.
