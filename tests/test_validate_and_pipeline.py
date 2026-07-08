"""Digest gates + condo-valuation pipeline: the simple-model happy path.

The pipeline test walks exactly the route a mechanical agent takes:
--init skeleton -> fill subject -> run (gates fail on TODOs, numbers computed)
-> fill narrative -> run again (all gates pass)."""
import copy
import json
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from researcher.valuation import validate_digest  # noqa: E402

DIGEST = os.path.join(ROOT, "researcher", "valuation", "spottiswoode_1803_digest.json")
TMP = os.path.join(ROOT, "researcher", "valuation", "_tmptest_digest.json")


def _load():
    return json.load(open(DIGEST, encoding="utf-8"))


def test_gates_pass_on_the_accepted_digest():
    results = validate_digest.check(_load())
    fails = [r for r in results if not r["ok"]]
    assert not fails, fails


def test_gate_catches_stale_price_base():
    d = _load()
    d["summary"] += " 点估 S$1,999,000。"
    bad = [r for r in validate_digest.check(d) if not r["ok"]]
    assert any(r["gate"] == "single-estimate-base" for r in bad)


def test_gate_catches_stale_psf_base():
    d = _load()
    d["risks"] = list(d["risks"]) + ["旧文案残留：点估 ~S$2,269 psf 云云"]
    bad = [r for r in validate_digest.check(d) if not r["ok"]]
    assert any(r["gate"] == "single-estimate-base" for r in bad)


def test_gate_catches_markdown_and_todo():
    d = _load()
    d["catalysts"] = list(d["catalysts"]) + ["**加粗残留**", "TODO：补写"]
    bad = {r["gate"] for r in validate_digest.check(d) if not r["ok"]}
    assert "no-markdown-asterisks" in bad and "no-todo-placeholders" in bad


def test_gate_catches_broken_arithmetic():
    d = copy.deepcopy(_load())
    d["valuation"]["estimate_price"] = 1_500_000  # no longer psf*sqft
    bad = {r["gate"] for r in validate_digest.check(d) if not r["ok"]}
    assert "price=psf*sqft" in bad


def _pipeline(*extra):
    return subprocess.run(
        [sys.executable, "-m", "researcher.pipelines.condo_valuation", "spottiswoode",
         "--digest-slug", "_tmptest", "--asof", "2026-07-03", "--no-report", *extra],
        capture_output=True, text=True, encoding="utf-8", cwd=ROOT,
        env={**os.environ, "PYTHONIOENCODING": "utf-8"})


def test_pipeline_end_to_end_simple_model_path():
    try:
        # 1. skeleton
        r = _pipeline("--init", "--force")
        assert r.returncode == 0, r.stdout + r.stderr
        d = json.load(open(TMP, encoding="utf-8"))
        assert "TODO" in d["summary"]

        # 2. fill subject only -> numbers computed, gates fail on TODOs
        d["subject"].update({"name": "#18-03 Spottiswoode Suites（743 sqft 紧凑 3BR）",
                             "unit": "#18-03", "size_sqft": 743, "floor": 18,
                             "bedrooms": 3, "tenure": "Freehold"})
        json.dump(d, open(TMP, "w", encoding="utf-8"), ensure_ascii=False)
        r = _pipeline()
        assert r.returncode == 1
        assert "no-todo-placeholders" in r.stdout
        d = json.load(open(TMP, encoding="utf-8"))
        v = d["valuation"]
        assert len(d["comps_table"]) == 37          # three-surface regression
        assert 2100 <= v["estimate_psf"] <= 2400
        assert v["triangulation"]["freshest_same_spec"]["psf"] == 2330  # the twin
        assert d["pipeline"]["trend"]["method"].startswith("cross-unit 3BR")

        # 3. fill narrative -> everything green
        def unTODO(o):
            if isinstance(o, dict):
                return {k: unTODO(x) for k, x in o.items()}
            if isinstance(o, list):
                return [unTODO(x) for x in o]
            if isinstance(o, str) and "TODO" in o:
                return o.replace("TODO", "已填写")
            return o

        d = unTODO(d)
        d["summary"] = f"点估 S${v['estimate_price']:,.0f}（{v['estimate_psf']:,} psf）。"
        json.dump(d, open(TMP, "w", encoding="utf-8"), ensure_ascii=False)
        r = _pipeline()
        assert r.returncode == 0, r.stdout + r.stderr
        assert "next: acceptance review" in r.stdout
    finally:
        if os.path.exists(TMP):
            os.remove(TMP)
