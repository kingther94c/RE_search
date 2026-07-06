---
name: multiagent-budget-lessons
description: "How to run Kelvin's 'pull a team' workflows without burning the session limit — fleet sizing, model tiers, cache reality"
metadata: 
  node_type: memory
  type: feedback
  originSessionId: 05a8a0f6-1bf9-4533-9ace-a43bc7336084
---

On 2026-07-02 two big Fable-tier fan-outs (6-finder review + 7-researcher refresh, all
parallel) hit the **session usage limit** mid-flight: ~1.18M subagent tokens, 20/22 agents
died, the whole research wave was lost. The lean re-run (4 sonnet gatherers) finished in
~280K tokens with better output discipline.

**Why:** worker-agent fan-outs share no prompt cache (each is a fresh context re-reading the
same files/web), simultaneous starts each pay the cold prefix, and `TaskOutput` blocking >5min
expires the main-loop cache too.

**How to apply (Kelvin wants teams — size them like this):**
- Gatherers/researchers: `model: 'sonnet'`, 3-4 per workflow with MERGED dimensions; cap
  searches per agent (~8-12) in the prompt. Fable only for synthesis (main loop) and the
  hostile-analyst reviewer.
- Reviews of my own code/docs: do in main loop (cache-friendly) instead of spawning finders,
  unless the surface is genuinely large.
- Sequence heavy workflows; don't run two big ones concurrently on a limited session.
- Structured-output schemas + "every claim needs a source URL" keeps sonnet gatherers honest;
  synthesis stays with me so judgment isn't delegated.
- Check the limit-reset time before launching a wave (failures say "resets HH:MM").
- **Digest/data patches: always write a .py file and run it — never inline python -c with
  regex inside bash double quotes.** Bash eats `\$` → `$` becomes a regex end-anchor and
  substitutions silently no-op (cost a full review round on 2026-07-03: three stale 点估
  bases survived because the sed-style patch never matched).
See [[kelvin-user]], [[landed-research-capability]].
