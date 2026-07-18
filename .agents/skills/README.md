# Skills

Reusable, **native Claude Code skills** (each a `SKILL.md` with YAML frontmatter, so
Claude auto-discovers them by `description`). Tool-agnostic playbooks: data arrives via
`WebFetch`/`WebSearch` for the web (OneMap, URA, EdgeProp, PUB, SLA…) and the
`research/lib/mbx.py` adb harness for Android apps. A hand-maintained-no-more mirror for
Codex agents lives at `.agents/skills/` — regenerate it with
`python tools/sync_agents_skills.py`, never edit it by hand.

## A · Condo (PropNex Investment Suite + URA spine)

```
read-investment-suite ──▶ harvest-scrolling-android-table ──▶ condo-resale-valuation ──▶ property-buy-sell-advisory
     (extract via UI)          (tables into rows)              (engine v2, validated)          (yield + costs + decision)
                                                                      ▲    corroborate hard cases
                                                                      └─── value-a-property (IS three-surface craft, SUPERSEDED)
                                     condo-investment-analysis = the factor framework layer (beta/alpha, friction hurdle)
```

| Slug | Role |
|---|---|
| [read-investment-suite](read-investment-suite/SKILL.md) | Extract development facts, transactions, rents, per-unit AVMs, realised returns from the Investment Suite app (`research/lib/mbx.py` + harvesters, doctor-gated). |
| [harvest-scrolling-android-table](harvest-scrolling-android-table/SKILL.md) | App-agnostic technique: any scrolling Android table → structured rows. Ref: `research/lib/harvest_sale.py`. |
| [condo-resale-valuation](condo-resale-valuation/SKILL.md) | **The condo valuation skill.** Engine v2 on the URA caveat spine (~3.7% median APE, EXP-0006/0007), conformal bands, bilingual report via `deliverables/build_condo_valuation_report.py`. |
| [property-buy-sell-advisory](property-buy-sell-advisory/SKILL.md) | Value → buy/hold/sell: yield, realised returns, BSD/ABSD/SSD (canonical math: `researcher/tax.py`), financing, catalysts. |
| [condo-investment-analysis](condo-investment-analysis/SKILL.md) | Factor framework (beta first, priced-in checklist, policy overlay, friction-gated alpha). Report: `Factor_Study_Condo_Report.html`. |
| [value-a-property](value-a-property/SKILL.md) | **SUPERSEDED** by condo-resale-valuation. Kept as the IS three-surface craft pipeline (exact floor/twin/AVM-cohort) for corroborating hard cases. Backing chain: `researcher/legacy/`. |

## B · Landed

```
landed-area-research ──▶ screen-landed-listings ──▶ landed-valuation (engine LV1)
   (area report + benchmark)   (PropertyGuru → rank)      └▶ landed-property-due-diligence (per-house DD + go/no-go)
                                     landed-investment-analysis = the framework layer (asymmetric capture, rebuild economics)
```

| Slug | Role |
|---|---|
| [landed-area-research](landed-area-research/SKILL.md) | Desktop-first AREA research (school 1km zone / estate): zoning, transactions, hazards → area report (`deliverables/build_landed_area_report.py`) + shortlist. |
| [screen-landed-listings](screen-landed-listings/SKILL.md) | Live for-sale listings (WebSearch primary; PropertyGuru app route = mobile_bridge's explorer) → rank via `researcher/landed/screen.py`. |
| [landed-valuation](landed-valuation/SKILL.md) | **The landed valuation skill.** Engine LV1 on URA land caveats, land-psf discipline, street-alias evidence rule; reports via `deliverables/build_landed_full_report.py` (default) / `build_landed_valuation_report.py`. |
| [landed-property-due-diligence](landed-property-due-diligence/SKILL.md) | Specific-house DD: plot/title/rebuild/hazards → score + go/no-go via `researcher/landed/{dd,scorecard}.py`, report via `deliverables/build_landed_dd_report.py`. |
| [landed-investment-analysis](landed-investment-analysis/SKILL.md) | Factor framework for landed (owns the canonical rebuild-cost range). Report: `Factor_Study_Landed_Report.html`. |

## C · New launch + meta

| Slug | Role |
|---|---|
| [new-launch-research](new-launch-research/SKILL.md) | 新盘 research: identity → verify → price positioning → thesis. Tools: `researcher/newlaunch/{scorecard,pricing}.py` (tax math from `researcher/tax.py`); report via `deliverables/build_newlaunch_report.py`. |
| [property-report-review](property-report-review/SKILL.md) | Hostile-analyst acceptance review of any report — PASS/REVISE loop before delivery. |

## Backing code & data

- `research/lib/` (adb harness + harvesters) · `research/tools/` (doctor, conformal
  stampers, audits) · `research/data/` (harvest dumps) · `research/registry/` (methodology
  + experiment log — start at `01_roadmap.md`)
- `researcher/engine/` (production valuation: engine v2 + LV1 + conformal tables) ·
  `researcher/backtest/` (walk-forward lab) · `researcher/tax.py` (the one BSD/ABSD/SSD
  implementation) · `researcher/landed/` · `researcher/newlaunch/` · `researcher/factors/` ·
  `researcher/legacy/` (v1 condo chain, craft reference)
- `deliverables/` — report builders; every report goes to BOTH the gitignored `reports/`
  and `G:\My Drive\004 RES\REsearch_Reports` via `deliverables/report_out.py`.
- The separate **mobile_bridge** repo = emulator host (mb_play AVD, device-profile truth
  in its `AGENTS.md`) + the PropertyGuru explorer. Investment Suite harvesting lives HERE.
