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

from deliverables.build_landed_full_report import _suppress_reason_zh  # noqa: E402
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
    for road, (street, why) in street_alias.ALIASES.items():
        assert street and len(why) > 40, f"{road} 的别名没有证据串"
        assert "EXP-" in why, f"{road} 的证据没有指向实验记录"


# ------------------------------------------------------------- 报告层护栏
def _v(conf=75, n=201, hard=False, spread=0.05):
    return {"fair_value": {"confidence": conf, "n_street_comps": n},
            "method_disagreement": {"hard_case": hard, "spread_rel": spread}}


def test_alias_suppresses_guidance_even_when_the_engine_is_happy():
    """引擎不知道街道是别名来的(它只看到一个正常的街道),所以这道闸只能在报告层。
    conf 75 / n=201 / 不 hard —— 引擎会照常给门槛,报告必须拦下。"""
    why = _suppress_reason_zh(_v(), 1839.57, basis="alias")
    assert "别名解析" in why and "不是本路的分布" in why


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
