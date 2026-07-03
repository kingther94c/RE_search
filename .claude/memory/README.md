# Agent memory (snapshot)

Versioned snapshot of the Claude Code **agent memory** for the RE_search + mobile_bridge
work — the durable, cross-session context the assistant accumulates (who the user is, how
work should be run, project gotchas, source-of-truth rules like Investment Suite / SG-official
data being Tier-1 ground truth).

- **Canonical live copy:** `~/.claude/projects/D--projects-git-projects-mobile-bridge/memory/`
  (both repos share one memory keyed to the mobile_bridge project path).
- **This directory is a mirror**, committed here because the project is private. It is updated
  by hand, so it may lag the live copy — treat the live copy as source of truth if they differ.
- `MEMORY.md` is the index (one line per memory); each `*.md` is a single fact with frontmatter
  (`type: user | feedback | project | reference`). Files cross-link with `[[name]]`.

The same snapshot is mirrored in the mobile_bridge repo.
