"""Skills must not rot: every repo path a SKILL.md names must exist, and the
.agents mirror must match .claude/skills.

The 2026-07-18 refactor moved a lot of code; these tests are what keeps the
playbooks honest through the NEXT move. Path extraction is deliberately narrow —
backtick-quoted repo paths with known top-level prefixes — so prose and URLs
don't produce false positives.
"""
import os
import re
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SKILLS = os.path.join(ROOT, ".claude", "skills")

# `...`-quoted tokens that look like repo paths under these roots
_PATH_RE = re.compile(
    r"`((?:researcher|research|deliverables|tools|tests)/[A-Za-z0-9_\-./{}]+)`")
# {a,b,c} brace groups expand to each alternative
_BRACE_RE = re.compile(r"\{([^}]*)\}")


def _expand(path: str) -> list[str]:
    m = _BRACE_RE.search(path)
    if not m:
        return [path]
    out = []
    for alt in m.group(1).split(","):
        out.extend(_expand(path[:m.start()] + alt.strip() + path[m.end():]))
    return out


def _skill_files():
    for dirpath, _dirs, files in os.walk(SKILLS):
        for fn in files:
            if fn.endswith(".md"):
                yield os.path.join(dirpath, fn)


# gitignored, created-at-runtime locations a skill may legitimately name
_RUNTIME_PREFIXES = ("research/.secrets/", "reports/")


def test_every_referenced_repo_path_exists():
    missing = []
    for md in _skill_files():
        text = open(md, encoding="utf-8").read()
        for raw in _PATH_RE.findall(text):
            for path in _expand(raw):
                # trim trailing punctuation-ish leftovers
                path = path.rstrip("./")
                if path.startswith(_RUNTIME_PREFIXES):
                    continue
                if not os.path.exists(os.path.join(ROOT, path)):
                    missing.append(f"{os.path.relpath(md, ROOT)} -> {path}")
    assert not missing, "skills reference nonexistent paths:\n  " + "\n  ".join(missing)


def test_agents_mirror_matches_claude_skills():
    sys.path.insert(0, os.path.join(ROOT, "tools"))
    try:
        from sync_agents_skills import in_sync
    finally:
        sys.path.pop(0)
    assert in_sync(), (
        ".agents/skills has drifted from .claude/skills — run "
        "`python tools/sync_agents_skills.py` and commit both trees")
