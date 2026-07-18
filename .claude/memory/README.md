# Agent memory — the research program journal (canonical)

**This directory is the ONE tracked home of the research-program journal** (since
the 2026-07-18 refactor): valuation experiment state, skills state, data-trust
rules, user preferences, cross-repo gotchas. It is maintained **directly in this
repo** by whichever session changes program state — there is no "sync from a live
copy" ritual anymore.

History: the journal used to be hand-mirrored across three places (this repo, the
mobile_bridge repo, and the live per-project store keyed to the mobile_bridge
path). The copies forked in both directions and mobile_bridge's git history
became a memory-sync changelog. mobile_bridge now keeps only bridge/emulator
facts (`mobile_bridge/.claude/memory/`); everything else lives here.

Two caveats to remember:

- Repo-tracked memory is **NOT auto-loaded into Claude's context** — only the
  live per-project store under `~/.claude/projects/` is. Sessions that need the
  journal should read `MEMORY.md` here (or start at
  `research/registry/01_roadmap.md`, which the journal links).
- `MEMORY.md` is the index (one line per memory); each `*.md` is a single fact
  with frontmatter (`type: user | feedback | project | reference`). Files
  cross-link with `[[name]]`.
