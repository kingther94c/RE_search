# Architecture & boundaries

## The one rule

**Data acquisition is Claude-driven and tool-agnostic.** A skill describes *method*
("find A/B/C, cross-check, then compare/analyse"); *how* the bytes arrive is decided
at run time — `WebFetch`/`WebSearch` for the web, the `research/lib/mbx.py` adb harness
for an Android app, an API when one exists. No skill hard-requires a specific tool.

## Layers (2026-07-18 layout)

| Layer | Path | Depends on | Job |
|---|---|---|---|
| **Skills** | `.claude/skills/` (canonical) → `.agents/skills/` (generated Codex mirror: `python tools/sync_agents_skills.py`) | nothing (pure playbooks) | the durable asset — method, auto-discovered by Claude |
| **Engine** | `researcher/engine/` | `researcher/backtest` (point methods + store) | the PRODUCTION valuation surface: engine v2 (condo) + LV1 (landed), conformal tables + sha1 fingerprints |
| **Lab** | `researcher/backtest/` | stdlib | walk-forward harness, benchmarks/candidates/anchors, the as-of TransactionStore (URA spine, committed-snapshot fallback) |
| **Domain** | `researcher/{landed,newlaunch,factors,sources}/`, `researcher/tax.py` | stdlib (+ store where noted) | street comps & DD, new-launch math, factor panels, official-data adapters, THE one BSD/ABSD/SSD implementation |
| **Legacy** | `researcher/legacy/`, `deliverables/legacy/` | frozen | the runnable engine-v1 condo chain — the `value-a-property` craft reference; bug-fix only |
| **Harness** | `research/lib/` (mbx + harvesters), `research/tools/` (doctor, conformal stampers, audits) | `adb` on PATH | Tier-1 extraction from the Investment Suite app + the sanctioned recalibration path |
| **Records** | `research/registry/` (methodology + EXP log), `research/experiments/` (frozen EXP scripts), `research/data/` (harvest dumps), `research/captures/` (audit trail + parser fixtures) | — | the evidence base; start any session at `research/registry/01_roadmap.md` |
| **Output** | `deliverables/` | researcher + research/data | report builders; ALL output routes through `report_out.py` to the gitignored `reports/` AND the Drive library |

## Dependency direction

```
.claude/skills → researcher/engine → researcher/backtest (methods, store)
              → researcher/{landed,newlaunch,factors,tax}
              → research/lib (adb harvest) → research/data
              → deliverables (render)      → reports/ + Drive
```

- **Fingerprint guard:** the conformal tables in `researcher/engine/` are sha1-locked to
  the point-method sources in `researcher/backtest/` (`researcher/engine/fingerprint.py`).
  Touch those files → recalibrate via `research/tools/analyze_r3.py` /
  `analyze_landed.py`; tests enforce it.
- **mobile_bridge** (separate repo) is the **emulator host**: the mb_play AVD,
  `scripts\start_emulator.ps1`, and the device-profile truth (its `AGENTS.md`;
  currently Pixel 6 portrait 1080x2400) live there, plus the PropertyGuru explorer.
  There is **no code dependency** in either direction; `research/tools/doctor.py`
  shells out to its start script (override with `MBX_EMULATOR_CMD`). Investment
  Suite harvesting is owned by THIS repo — mobile_bridge's old Appium bridge and IS
  explorer are retired in its `legacy/`.
- **Memory:** `.claude/memory/` here is the canonical tracked research-program journal
  (mobile_bridge keeps only bridge facts). It is not auto-loaded into context — read
  `MEMORY.md` or start at the roadmap.
- New heavy deps (web scraping, NLP for 小红书) go behind `pyproject.toml` extras with
  import guards, so a plain user never pulls them unintentionally.
