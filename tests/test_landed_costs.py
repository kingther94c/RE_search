"""成本栈的算术 —— 这些数字会被人拿去做决策,所以每条都对着公开的 worked example 锁死。"""
from __future__ import annotations

import pytest

from researcher.tax import (ABSD_RATES, absd, bsd, breakeven_gain_pct,
                                     entry_costs, ssd, ssd_clock)


def test_bsd_matches_the_published_worked_example():
    """property-buy-sell-advisory SKILL 的 worked example:S$1.686M -> ~S$53,900。"""
    assert bsd(1_686_000) == pytest.approx(53_900, abs=200)


def test_bsd_bands_are_progressive_and_continuous():
    assert bsd(180_000) == pytest.approx(1_800)                  # 全在 1% 档
    assert bsd(360_000) == pytest.approx(1_800 + 3_600)          # + 2% 档
    for p in (179_999, 360_001, 1_000_001, 1_500_001, 3_000_001):
        assert bsd(p + 1) > bsd(p)                               # 单调
    assert bsd(0) == 0


def test_absd_pr_third_property_is_35_not_30():
    """仓库原先两处写 30%(dataset.py + advisory SKILL)。经 IRAS/MAS 2023-04-27 新政三次
    交叉核对为 **35%**。两个内部来源一致不等于对 —— 它们同源。这条测试就是那次更正的锚。"""
    assert ABSD_RATES["PR"][3] == 0.35
    assert absd(1_000_000, "PR", 3) == pytest.approx(350_000)


def test_absd_table_against_the_published_worked_example():
    """SKILL 的 worked example:S$1.686M 上,SC 二套 ~S$337k;外国人 ~S$1.01M。"""
    assert absd(1_686_000, "SC", 2) == pytest.approx(337_200, abs=500)
    assert absd(1_686_000, "FOREIGNER", 1) == pytest.approx(1_011_600, abs=500)


def test_absd_first_home_citizen_is_zero():
    assert absd(5_000_000, "SC", 1) == 0


def test_absd_counts_above_three_clamp_to_the_top_band():
    assert absd(1e6, "SC", 9) == absd(1e6, "SC", 3)


def test_absd_rejects_an_unknown_profile():
    with pytest.raises(ValueError, match="未知买家画像"):
        absd(1e6, "MARTIAN", 1)


def test_ssd_bands_and_the_four_year_cliff():
    """2025-07-04 起购入:4 年期,16/12/8/4。第 4 年后归零 —— 这个悬崖是成本栈里最大的单项。"""
    p = 4_250_000
    assert ssd(p, 0.5) == pytest.approx(p * 0.16)
    assert ssd(p, 1.0) == pytest.approx(p * 0.16)
    assert ssd(p, 1.01) == pytest.approx(p * 0.12)
    assert ssd(p, 4.0) == pytest.approx(p * 0.04)
    assert ssd(p, 4.01) == 0


def test_ssd_clock_dominates_the_cost_stack_on_a_short_hold():
    """报告要讲的那句话,用算术锁住:一年内卖,SSD 比全部买入成本还大。"""
    p = 4_250_000
    entry = entry_costs(p, "SC", 1)["total"]
    year_one = ssd_clock(p)[0]
    assert year_one["amount"] == pytest.approx(p * 0.16)
    assert year_one["amount"] > entry            # 680k vs ~168k


def test_entry_costs_add_up_and_report_a_rate():
    r = entry_costs(4_250_000, "PR", 2)
    assert r["absd_rate"] == 0.30
    assert r["total"] == r["bsd"] + r["absd"] + r["legal"]
    assert 0.30 < r["total_pct"] < 0.35          # PR 二套:ABSD 30% 主导


def test_breakeven_needs_more_gain_inside_the_ssd_window():
    """SSD 窗口内退出,盈亏平衡所需涨幅必须显著更高 —— 这是「买入即 alpha」那句话的算术。"""
    p = 4_250_000
    inside = breakeven_gain_pct(p, "SC", 1, holding_years=1)
    outside = breakeven_gain_pct(p, "SC", 1, holding_years=5)
    assert inside > outside + 0.15
    assert 0.03 < outside < 0.10                 # 出了窗口只剩 BSD+佣金
