---
name: re-search-reports-dir
description: "RE_search HTML reports go to BOTH the repo's gitignored reports/ AND G:\\My Drive\\004 RES\\REsearch_Reports — never into a tracked folder"
metadata:
  node_type: memory
  type: project
  originSessionId: 00e62779-5c6e-4a94-8f62-60034e67882f
---

Every **RE_search** HTML report goes to **BOTH** destinations, every run (user instruction
2026-07-16, supersedes the 2026-06-30 "Drive with a `deliverables/` fallback" rule):

1. **`reports/` at the repo root — GITIGNORED**, always written. Canonical local copy.
2. **`G:\My Drive\004 RES\REsearch_Reports`** — the user-facing library. Env
   `RESEARCH_REPORTS_DIR` overrides the destination.

**Never either/or.** If the Drive is unmounted the repo copy still lands and the builder
says it did not sync; `python -m deliverables.report_out --sync` catches up later.

**One implementation:** `deliverables/report_out.py` → `write_report(name, html)`. All 8
builders call it; none re-derives the path. Do the same for any new report generator.

**Why the change:** the old rule fell back to the TRACKED `deliverables/` folder when the
Drive was missing, so reports got silently committed (a 60 KB
`seletar_green_walk_14_DD_Report.html` blob is in git history because of this). Reports
are regenerable artifacts, not source. `.gitignore` now blocks `reports/` and
`deliverables/*.html`. See [[investment-suite-valuation]].
