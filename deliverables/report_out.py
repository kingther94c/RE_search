r"""Where every RE_search HTML report goes. ONE place — builders must not re-derive it.

The rule (user instruction 2026-07-16, supersedes "Drive with a deliverables/ fallback"):

  1. **The repo copy is canonical and always written**: `reports/` at the repo root,
     which is GITIGNORED. Reports are regenerable artifacts, not source — the old
     fallback wrote them into the TRACKED `deliverables/` folder, so a run with the
     Google Drive unmounted silently committed a 60 KB HTML blob (that is how
     seletar_green_walk_14_DD_Report.html ended up in git).
  2. **Then sync to the Drive**: `G:\My Drive\004 RES\REsearch_Reports` — the
     user-facing library. Override with env `RESEARCH_REPORTS_DIR`.

Both destinations, every time — not either/or. If the Drive is unmounted the repo copy
still lands and `write_report` says so in its return value; the caller/user can re-sync
later with `sync_pending()`. A missing Drive is never a reason to skip the report, and
never a reason to write into a tracked folder.

    from deliverables.report_out import write_report
    res = write_report("cardiff_grove_19_Landed_Valuation_Report.html", html)
    print(res.summary())        # -> "wrote reports/<name> (61 KB); synced to G:\..."
"""
from __future__ import annotations

import os
import shutil
from dataclasses import dataclass

_HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(_HERE)
#: repo-local, gitignored — always written
REPORTS_DIR = os.path.join(REPO, "reports")
#: user-facing library on the Google Drive
DRIVE_DIR_DEFAULT = r"G:\My Drive\004 RES\REsearch_Reports"


def drive_dir() -> str:
    """The Drive destination (env override wins). Not guaranteed to exist."""
    return os.environ.get("RESEARCH_REPORTS_DIR") or DRIVE_DIR_DEFAULT


def drive_available(path: str | None = None) -> bool:
    """True when the destination exists or its parent does (so we may create it)."""
    d = path or drive_dir()
    return os.path.isdir(d) or os.path.isdir(os.path.dirname(d) or os.sep)


@dataclass
class ReportPaths:
    name: str
    repo_path: str
    drive_path: str | None      # None when the Drive was unreachable
    size_kb: float

    def summary(self) -> str:
        s = f"wrote {self.repo_path}  ({self.size_kb:.0f} KB)"
        if self.drive_path:
            return s + f"\n  synced -> {self.drive_path}"
        return (s + f"\n  NOT synced: {drive_dir()} unreachable — re-run "
                "`python -m deliverables.report_out --sync` once the Drive is mounted")


def write_report(name: str, html: str) -> ReportPaths:
    """Write an HTML report to the repo's gitignored reports/ AND sync it to the Drive.

    Returns both paths; `drive_path` is None when the Drive is unreachable (the repo
    copy is still written — reports are never skipped, and never land in a tracked dir).
    """
    os.makedirs(REPORTS_DIR, exist_ok=True)
    repo_path = os.path.join(REPORTS_DIR, name)
    with open(repo_path, "w", encoding="utf-8", newline="\n") as f:
        f.write(html)
    size_kb = len(html.encode("utf-8")) / 1024

    drive_path = None
    d = drive_dir()
    if drive_available(d):
        try:
            os.makedirs(d, exist_ok=True)
            drive_path = os.path.join(d, name)
            shutil.copyfile(repo_path, drive_path)
        except OSError:
            drive_path = None
    return ReportPaths(name, repo_path, drive_path, size_kb)


def sync_pending() -> list[str]:
    """Copy every report in reports/ to the Drive. Use after mounting a missing Drive.
    Returns the names copied."""
    d = drive_dir()
    if not drive_available(d) or not os.path.isdir(REPORTS_DIR):
        return []
    os.makedirs(d, exist_ok=True)
    done = []
    for name in sorted(os.listdir(REPORTS_DIR)):
        src = os.path.join(REPORTS_DIR, name)
        if os.path.isfile(src):
            shutil.copyfile(src, os.path.join(d, name))
            done.append(name)
    return done


if __name__ == "__main__":
    import sys
    if "--sync" in sys.argv:
        names = sync_pending()
        print(f"synced {len(names)} report(s) -> {drive_dir()}"
              if names else f"nothing to sync ({drive_dir()} reachable? "
                            f"{drive_available()})")
    else:
        print(f"repo reports dir : {REPORTS_DIR}  (gitignored)")
        print(f"drive dir        : {drive_dir()}  (available: {drive_available()})")
