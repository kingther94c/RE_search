"""Regenerate .agents/skills (the Codex-agent mirror) from .claude/skills.

.claude/skills is canonical. The mirror used to be maintained by hand-dual-commits
and drifted twice (stale wording 2026-07-16; two skills + README never mirrored).
Now: edit .claude/skills only, then run

    python tools/sync_agents_skills.py

which makes .agents/skills an exact, LF-normalized copy (adds, updates, AND
deletes). CI-less repo, so the honesty check is tests/test_skills_references.py,
which fails when the two trees differ.
"""
from __future__ import annotations

import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, ".claude", "skills")
DST = os.path.join(ROOT, ".agents", "skills")


def _read_lf(path: str) -> bytes:
    with open(path, "rb") as f:
        return f.read().replace(b"\r\n", b"\n")


def sync(dry_run: bool = False) -> list[str]:
    """Return the change list; apply it unless dry_run.

    There is deliberately ONE definition of "in sync" — the checker is this same
    walk with dry_run=True, so the fixer and the checker can never disagree.
    """
    changes: list[str] = []
    wanted: set[str] = set()
    for dirpath, _dirnames, filenames in os.walk(SRC):
        rel_dir = os.path.relpath(dirpath, SRC)
        for fn in filenames:
            rel = os.path.normpath(os.path.join(rel_dir, fn))
            wanted.add(rel)
            src_p = os.path.join(SRC, rel)
            dst_p = os.path.join(DST, rel)
            data = _read_lf(src_p)
            if not os.path.exists(dst_p) or _read_lf(dst_p) != data:
                changes.append(f"write {rel}")
                if not dry_run:
                    os.makedirs(os.path.dirname(dst_p), exist_ok=True)
                    with open(dst_p, "wb") as f:
                        f.write(data)
    # prune anything in the mirror that no longer exists in the source
    if os.path.isdir(DST):
        for dirpath, _dirnames, filenames in os.walk(DST, topdown=False):
            rel_dir = os.path.relpath(dirpath, DST)
            for fn in filenames:
                rel = os.path.normpath(os.path.join(rel_dir, fn))
                if rel not in wanted:
                    changes.append(f"delete {rel}")
                    if not dry_run:
                        os.remove(os.path.join(dirpath, fn))
            if not dry_run and not os.listdir(dirpath) \
                    and os.path.normpath(rel_dir) != ".":
                os.rmdir(dirpath)
    return changes


def in_sync() -> bool:
    """True when the mirror byte-matches the source modulo CRLF (used by the test)."""
    return not sync(dry_run=True)


if __name__ == "__main__":
    changed = sync()
    for c in changed:
        print(" ", c)
    print(f"{len(changed)} change(s); mirror {'OK' if in_sync() else 'STILL DIVERGED?!'}")
    sys.exit(0)
