---
name: re-search-reports-dir
description: "RE_search research reports must be written to the Google Drive folder G:\\My Drive\\004 RES\\REsearch_Reports"
metadata:
  node_type: memory
  type: project
  originSessionId: 00e62779-5c6e-4a94-8f62-60034e67882f
---

All **RE_search** research reports output to `G:\My Drive\004 RES\REsearch_Reports`
(user instruction 2026-06-30). `deliverables/build_report.py` writes there by default;
env var `RESEARCH_REPORTS_DIR` overrides it, and it falls back to the repo's
`deliverables/` only if the Google Drive isn't mounted. Apply this same destination to
any future report generators added to RE_search. See [[investment-suite-valuation]].
