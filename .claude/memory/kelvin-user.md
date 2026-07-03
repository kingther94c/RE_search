---
name: kelvin-user
description: Who the user is and how they like work run on this project
metadata: 
  node_type: memory
  type: user
  originSessionId: 00e62779-5c6e-4a94-8f62-60034e67882f
---

User is **Kelvin** (kingther94c@gmail.com). Prefers replies in Chinese (中文).

Working style on this project: wants work done end-to-end and actually runnable +
tested (not just scaffolded); explicitly asked to "pull a team" (multi-agent/workflow
orchestration is welcome here). Values: reliability, explicit waits, clean abstractions,
app-specific selectors kept isolated. See [[android-read-bridge]], [[git-default-main]].

**Git workflow (updated 2026-07-03, supersedes the old worktree-isolation preference):**
commit & push **directly to `main`** — both local and remote — as the default; no feature
branches, no worktree isolation. The earlier "isolate in a worktree" note was for a
concurrent codex process that is no longer a concern. See [[git-default-main]].
