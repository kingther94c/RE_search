"""report_out: reports land in the MAIN checkout's gitignored reports/ AND on the Drive.

The load-bearing test is `test_reports_dir_resolves_to_main_checkout_from_a_worktree`:
report_out originally derived the repo root from __file__, so a builder run inside a
linked worktree wrote reports into `<worktree>/reports` — a git-excluded, disposable
directory the user never looks in, and which dies when the worktree is cleaned up.
"""
import glob
import os

from deliverables import report_out

_DELIVERABLES = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "deliverables")


def _fake_worktree(tmp_path):
    """A linked worktree nested under its main checkout, as `git worktree add` leaves it:
    main/.git is a real dir; worktree/.git is a FILE pointing into main/.git/worktrees/."""
    main = tmp_path / "RE_search"
    gitdir = main / ".git" / "worktrees" / "wt1"
    gitdir.mkdir(parents=True)
    wt = main / ".claude" / "worktrees" / "wt1"
    wt.mkdir(parents=True)
    return main, wt, gitdir


def test_reports_dir_resolves_to_main_checkout_from_a_worktree(tmp_path):
    main, wt, gitdir = _fake_worktree(tmp_path)
    # git writes the pointer with forward slashes even on Windows
    (wt / ".git").write_text(f"gitdir: {gitdir.as_posix()}", encoding="utf-8")
    assert report_out._main_repo_root(str(wt)) == str(main)


def test_worktree_gitdir_may_be_relative(tmp_path):
    """git is allowed to store the pointer relative to the worktree."""
    main, wt, gitdir = _fake_worktree(tmp_path)
    (wt / ".git").write_text(f"gitdir: {os.path.relpath(gitdir, wt)}", encoding="utf-8")
    assert report_out._main_repo_root(str(wt)) == str(main)


def test_main_checkout_resolves_to_itself(tmp_path):
    """A normal clone has a real .git DIRECTORY — the root is the checkout itself."""
    repo = tmp_path / "RE_search"
    (repo / ".git").mkdir(parents=True)
    assert report_out._main_repo_root(str(repo)) == str(repo)


def test_unreadable_or_odd_pointer_falls_back_to_the_checkout(tmp_path):
    """Never raise on a stray .git file — degrade to the local checkout."""
    repo = tmp_path / "loose"
    repo.mkdir()
    (repo / ".git").write_text("not a gitdir pointer", encoding="utf-8")
    assert report_out._main_repo_root(str(repo)) == str(repo)
    bare = tmp_path / "nogit"
    bare.mkdir()
    assert report_out._main_repo_root(str(bare)) == str(bare)


def test_live_reports_dir_is_the_main_checkout_not_a_worktree():
    """The real module-level constant: never inside .claude/worktrees/."""
    assert os.path.basename(report_out.REPORTS_DIR) == "reports"
    assert os.path.join(".claude", "worktrees") not in report_out.REPORTS_DIR


def test_every_builder_routes_through_report_out():
    """No builder may re-derive the destination. build_landed_valuation_report.py (then build_landed_v2_report.py) shipped with a
    copy-pasted `_reports_dir()` that fell back to the TRACKED deliverables/ — the exact
    defect the rule exists to kill. Catch the next copy-paste here, not in git history."""
    builders = sorted(glob.glob(os.path.join(_DELIVERABLES, "build_*.py")))
    assert builders, "no builders found — did the glob break?"
    offenders = []
    for path in builders:
        src = open(path, encoding="utf-8").read()
        name = os.path.basename(path)
        if "report_out" not in src:
            offenders.append(f"{name}: does not import report_out")
        # naming the Drive in a docstring is fine; resolving it in code is the offence
        if 'os.environ.get("RESEARCH_REPORTS_DIR"' in src:
            offenders.append(f"{name}: re-derives the reports dir")
    assert not offenders, "builders must call report_out.write_report(): " + "; ".join(
        offenders)


def test_write_report_writes_repo_copy_and_syncs(tmp_path, monkeypatch):
    drive = tmp_path / "drive"
    drive.mkdir()
    repo_reports = tmp_path / "reports"
    monkeypatch.setattr(report_out, "REPORTS_DIR", str(repo_reports))
    monkeypatch.setenv("RESEARCH_REPORTS_DIR", str(drive))

    res = report_out.write_report("x_Report.html", "<html>hi</html>")
    assert (repo_reports / "x_Report.html").read_text(encoding="utf-8") == "<html>hi</html>"
    assert (drive / "x_Report.html").read_text(encoding="utf-8") == "<html>hi</html>"
    assert res.drive_path and "synced" in res.summary()


def test_report_still_written_when_the_drive_is_missing(tmp_path, monkeypatch):
    """An unmounted Drive must never skip the report, and never divert it elsewhere."""
    repo_reports = tmp_path / "reports"
    monkeypatch.setattr(report_out, "REPORTS_DIR", str(repo_reports))
    monkeypatch.setenv("RESEARCH_REPORTS_DIR", str(tmp_path / "nope" / "gone" / "away"))

    res = report_out.write_report("y_Report.html", "<html>hi</html>")
    assert (repo_reports / "y_Report.html").exists()
    assert res.drive_path is None
    assert "NOT synced" in res.summary()


def test_sync_pending_catches_up_after_a_remount(tmp_path, monkeypatch):
    drive = tmp_path / "drive"
    repo_reports = tmp_path / "reports"
    repo_reports.mkdir()
    (repo_reports / "a.html").write_text("A", encoding="utf-8")
    (repo_reports / "b.html").write_text("B", encoding="utf-8")
    monkeypatch.setattr(report_out, "REPORTS_DIR", str(repo_reports))
    monkeypatch.setenv("RESEARCH_REPORTS_DIR", str(drive))

    assert report_out.sync_pending() == ["a.html", "b.html"]
    assert (drive / "a.html").read_text(encoding="utf-8") == "A"
