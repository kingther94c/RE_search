"""地址 -> 全面报告 的接缝测试(纯逻辑,不联网)。

接缝上最容易出错、也最贵的两件事,都锁在这里:
  1. 地址的路名 != URA 的街道,解析不出来必须**拒答**,不能猜(GY-0006);
  2. 别名解析出来的桶混着别的路,**议价门槛不能用**(实测:19 Cardiff Grove 的桶门槛
     「积极买入 < S$3.87M」,而本路原装房成交在 S$3.25-3.58M —— 照它买会买贵)。
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pytest  # noqa: E402

from deliverables.build_landed_full_report import (_merged_alerts,  # noqa: E402
                                                   _suppress_reason_zh)
from researcher.landed import street_alias  # noqa: E402
from researcher.landed.comps import street_comps  # noqa: E402

_HAS = lambda s: bool(street_comps(s))


# ------------------------------------------------------------- 街道解析
def test_direct_street_resolves_to_itself():
    r = street_alias.resolve("LOYANG RISE", _HAS)
    assert r["ura_street"] == "LOYANG RISE" and r["basis"] == "direct"


def test_cardiff_grove_resolves_to_its_evidenced_parent():
    """引擎昨天对这个地址 street_not_found 拒答;它的成交一直在 ALNWICK ROAD 桶里。"""
    r = street_alias.resolve("CARDIFF GROVE", _HAS)
    assert r["ura_street"] == "ALNWICK ROAD" and r["basis"] == "alias"
    assert "16 of 17" in r["evidence"]          # 别名必须带证据,不能是拍脑袋


def test_loyang_view_resolves_to_its_parent():
    r = street_alias.resolve("LOYANG VIEW", _HAS)
    assert r["ura_street"] == "LOYANG RISE" and r["basis"] == "alias"


def test_unknown_road_refuses_instead_of_guessing():
    """GY-0006:最近质心解析会把 19 Cardiff Grove 配到 158m 外**另一个屋苑**的 CHUAN DRIVE
    (真母路 ALNWICK ROAD 排第 17、710m 外)。错的母路会用别的屋苑的可比、以满置信度定价 ——
    比拒答更糟。所以未知路必须返回 None。"""
    r = street_alias.resolve("NO SUCH ROAD AT ALL", _HAS)
    assert r["ura_street"] is None and r["basis"] == "unresolved"
    assert "GY-0006" in r["evidence"]           # 拒答要告诉人怎么正确解决


def test_alias_requires_evidence_string():
    """别名必须带证据(英中双语 —— 报告主体是中文,证据串会被直接印出来)。"""
    for road, a in street_alias.ALIASES.items():
        assert a["street"] and len(a["evidence"]) > 40, f"{road} 的别名没有证据串"
        assert "EXP-" in a["evidence"], f"{road} 的证据没有指向实验记录"
        assert len(a.get("evidence_zh", "")) > 30, f"{road} 缺中文证据串(主体中文)"
        assert "EXP-" in a["evidence_zh"]


def test_resolve_returns_chinese_evidence_on_every_branch():
    for road in ("LOYANG RISE", "CARDIFF GROVE", "NO SUCH ROAD AT ALL"):
        r = street_alias.resolve(road, _HAS)
        assert r.get("evidence_zh"), f"{road}: {r['basis']} 分支缺 evidence_zh"


# ------------------------------------------------------------- 报告层护栏
def _v(conf=75, n=201, hard=False, spread=0.05):
    return {"fair_value": {"confidence": conf, "n_street_comps": n},
            "method_disagreement": {"hard_case": hard, "spread_rel": spread}}


def test_alias_suppresses_guidance_even_when_the_engine_is_happy():
    """引擎不知道街道是别名来的(它只看到一个正常的街道),所以这道闸只能在报告层。
    conf 75 / n=201 / 不 hard —— 引擎会照常给门槛,报告必须拦下。
    理由措辞在 EXP-0019 后升级为**少数份额**这个实测驱动(不再是笼统的「混路」)。"""
    why = _suppress_reason_zh(_v(), 1839.57, basis="alias")
    assert "别名解析" in why and "少数份额" in why and "多数派" in why


def test_direct_street_keeps_the_engine_s_own_reasons():
    """直连街道时,抑制原因仍应是引擎的那几条,不能被别名规则劫持。"""
    assert "8k" in _suppress_reason_zh(_v(), 9000, basis="direct")
    assert "pooled" in _suppress_reason_zh(_v(n=0), 2000, basis="direct")
    assert "hard case" in _suppress_reason_zh(_v(hard=True, spread=0.33), 2000, basis="direct")
    assert "置信度" in _suppress_reason_zh(_v(conf=40), 2000, basis="direct")


@pytest.mark.parametrize("area,basis,want", [
    (9000, "alias", "别名解析"),      # 别名优先:它使门槛在原则上失效,而非只是不准
    (9000, "direct", "8k"),
])
def test_alias_reason_outranks_the_others(area, basis, want):
    assert want in _suppress_reason_zh(_v(), area, basis=basis)


# ------------------------------------------------------------- F1:判断层 alerts 合并
def _g_with_digest(alerts):
    """最小 g:val=None → 自动清单只剩 3 条普适项(BCA / 法定 / 积水)。"""
    return {"dd": {"neighbours": [], "schools_primary": [], "street": "X"},
            "val": None, "land_area": 1600,
            "resolve": {"basis": "direct", "ura_street": "X"},
            "digest": {"dd3_alerts": alerts}}


_AUTHORED = [
    {"item": "BCA approved architectural & structural plans",
     "item_zh": "BCA 批准的建筑与结构图纸(人写版)", "why": "en", "why_zh": "中文理由",
     "seller_gated": True, "who_zh": "业主", "when_zh": "OTP 前"},
    {"item": "Defects and build quality (the turnkey archetype's main risk)",
     "item_zh": "缺陷与施工质量(turnkey 原型的主要风险)", "why_zh": "房龄约 6-7 年……",
     "seller_gated": False},
    {"item": "Fair value — deliberately NOT stated",
     "item_zh": "公允价值 —— 刻意不给出", "why_zh": "……估值引擎是另一条在建赛道。",
     "seller_gated": False},
]


def test_merged_alerts_keeps_the_authored_only_item():
    """第一版把 8 条 authored alerts 静默丢弃 —— 丢掉的里面有 archetype 指名的头号风险
    (turnkey 缺陷),自动规则永远推不出来。合并后它必须在,且标「人写」。"""
    out = _merged_alerts(_g_with_digest(_AUTHORED))
    defects = [a for a in out if "缺陷与施工质量" in a["title"]]
    assert defects and defects[0]["src"] == "authored"


def test_merged_alerts_prefers_authored_over_matching_auto():
    """同主题(BCA)只出现一次,用人写版(它是为这个地址写的)。"""
    out = _merged_alerts(_g_with_digest(_AUTHORED))
    bca = [a for a in out if "BCA" in a["title"]]
    assert len(bca) == 1
    assert bca[0]["src"] == "authored" and "人写版" in bca[0]["title"]
    assert bca[0]["gated"] is True
    assert "业主" in bca[0]["meta"]              # who/when 元信息随人写条目带出


def test_merged_alerts_annotates_the_superseded_item_instead_of_dropping_it():
    """digest 写于引擎接入之前,「刻意不给估值」一条已被本报告推翻 —— 不删也不照登,
    显式标注「已被本报告取代」,读者能看见判断的时间线。"""
    out = _merged_alerts(_g_with_digest(_AUTHORED))
    sup = [a for a in out if a["src"] == "superseded"]
    assert len(sup) == 1 and "公允价值" in sup[0]["title"]
    assert "已被本报告取代" not in sup[0]["why"]          # 注记在 sup 字段,不污染原文
    assert "估值引擎接入之前" in sup[0]["sup"]


def test_merged_alerts_without_digest_is_the_auto_list():
    out = _merged_alerts(_g_with_digest([]))
    assert all(a["src"] == "tool" for a in out) and len(out) == 3


# 注:「SSD 与买入成本孰大」的叙述函数及其两条测试已随 SSD 时钟一并删除(2026-07-18,
# 用户裁定):landed 按自住/长持读,4 年内退出这个前提不存在,比较孰大没有决策含量。
# SSD 的税率算术仍由 tests/test_landed_costs.py 锁着(它守的是 costs.py 的表本身)。
