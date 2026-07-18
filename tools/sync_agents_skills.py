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

import filecmp
import os
import shutil
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, ".claude", "skills")
DST = os.path.join(ROOT, ".agents", "skills")


def _read_lf(path: str) -> bytes:
    with open(path, "rb") as f:
        return f.read().replace(b"\r\n", b"\n")


def sync() -> list[str]:
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
                os.makedirs(os.path.dirname(dst_p), exist_ok=True)
                with open(dst_p, "wb") as f:
                    f.write(data)
                changes.append(f"write {rel}")
    # prune anything in the mirror that no longer exists in the source
    if os.path.isdir(DST):
        for dirpath, _dirnames, filenames in os.walk(DST, topdown=False):
            rel_dir = os.path.relpath(dirpath, DST)
            for fn in filenames:
                rel = os.path.normpath(os.path.join(rel_dir, fn))
                if rel not in wanted:
                    os.remove(os.path.join(dirpath, fn))
                    changes.append(f"delete {rel}")
            if not os.listdir(dirpath) and os.path.normpath(rel_dir) != ".":
                os.rmdir(dirpath)
    return changes


def in_sync() -> bool:
    """True when the mirror byte-matches the source modulo CRLF (used by the test)."""
    for dirpath, _dirnames, filenames in os.walk(SRC):
        rel_dir = os.path.relpath(dirpath, SRC)
        for fn in filenames:
            rel = os.path.join(rel_dir, fn)
            dst_p = os.path.join(DST, rel)
            if not os.path.exists(dst_p):
                return False
            if _read_lf(os.path.join(SRC, rel)) != _read_lf(dst_p):
                return False
    for dirpath, _dirnames, filenames in os.walk(DST):
        rel_dir = os.path.relpath(dirpath, DST)
        for fn in filenames:
            if not os.path.exists(os.path.join(SRC, rel_dir, fn)):
                return False
    return True


if __name__ == "__main__":
    changed = sync()
    for c in changed:
        print(" ", c)
    print(f"{len(changed)} change(s); mirror {'OK' if in_sync() else 'STILL DIVERGED?!'}")
    sys.exit(0)
