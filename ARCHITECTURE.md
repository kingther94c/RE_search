# Architecture & boundaries

## The one rule

**Data acquisition is Claude-driven and tool-agnostic.** A skill describes *method*
("find A/B/C, cross-check, then compare/analyse"); *how* the bytes arrive is decided
at run time — `WebFetch`/`WebSearch` for the web, the `research/mbx.py` adb harness for
an Android app, an API when one exists. No skill hard-requires a specific tool.

## Layers

| Layer | Path | Depends on | Job |
|---|---|---|---|
| **Skills** | `.claude/skills/` | nothing (pure playbooks) | the durable asset — method, auto-discovered by Claude |
| **Brain** | `researcher/` | stdlib (+ optional adapters) | analysis & pipelines (valuation engine, sources, pipelines) |
| **Harness** | `research/` | `adb` on PATH | exploration / data harvest (`mbx.py`, `harvest_sale.py`) |
| **Output** | `deliverables/` | `researcher/` + `research/captures/` | reports & briefs |

## Dependency direction

```
.claude/skills  →  researcher  →  research(adb)        (and → web via Claude's WebFetch)
                         ⌙→  (optional) mobile_bridge   # only if a skill wants the tested Appium path
```

- `RE_search → mobile_bridge`, **never** the reverse. Today there is **no code dependency**:
  `research/mbx.py` shells out to `adb` directly. `mobile_bridge` is a *separate repo* and an
  *optional* tool, not a parent.
- New heavy deps (web scraping, NLP for 小红书 / Xiaohongshu) go behind `pyproject.toml` extras
  with import guards, so a plain user never pulls them unintentionally.

## When to split further

Extract a standalone `claude-researcher-skills` **plugin** repo once you have **≥2 working data
sources** *and* **≥6 calibrated, device-agnostic skills**. Until then, one repo.
