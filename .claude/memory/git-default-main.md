---
name: git-default-main
description: "Kelvin's default git workflow for mobile_bridge + RE_search: commit & push directly to main (local + remote), no feature branches"
metadata: 
  node_type: memory
  type: feedback
  originSessionId: 05a8a0f6-1bf9-4533-9ace-a43bc7336084
---

For both **mobile_bridge** and **RE_search**, the default is to **commit and push directly to
`main`** — keeping local `main` and `origin/main` in sync — with no feature branch and no
git-worktree isolation.

**Why:** Kelvin said so explicitly on 2026-07-03 ("两边都推到local和remote main,记住这是以后的默认,
并且移动到main上"). The earlier worktree-isolation preference existed only to avoid clashing with a
concurrent `codex/*` process on the main checkout; that process is no longer running, so the
isolation is unnecessary overhead.

**How to apply:**
- Do the work on `main` and `git push origin main` when a unit of work is done — don't ask each
  time (this is standing authorization for these two repos). This overrides the generic "if on the
  default branch, branch first" default.
- If a session is forced into a worktree/feature branch (as on 2026-07-03), fast-forward `main` to
  the branch in the main checkout and push, then delete the now-merged remote branch — leave `main`
  as the only remote head.
- Remotes: github.com/kingther94c/mobile_bridge and github.com/kingther94c/RE_search.
See [[kelvin-user]], [[android-read-bridge]].
