"""买入/持有/退出的成本栈 —— BSD · ABSD · SSD,以及 SSD 时钟。

为什么它必须在报告里:估值告诉你房子值多少,成本栈告诉你**这笔交易**要多少。在短持有期上
它压倒一切 —— 一笔 S$4.25M 的成交,第一年内卖出的 SSD 是 **16% ≈ S$680k**,比报告里其它
所有成本项加起来还大。一份只有估值和 DD、没有成本栈的 landed 报告是不完整的。

税率是**会变的**,而且这里的数字会被人拿去做决策 —— 所以每张表都带 `source` / `effective` /
`verify_at`,报告必须把生效日印出来。本模块只做**算术**,不做建议。

**这是全仓库唯一的 BSD/ABSD/SSD 实现**(2026-07-18 起):newlaunch/pricing、报告构建器、
skills 全部从这里取数;不要在别处复制税率表。

    from researcher.tax import entry_costs, ssd_clock, PROFILES
    entry_costs(4_250_000, "PR", 2)     -> {'bsd':…, 'absd':…, 'total':…, …}
    ssd_clock(4_250_000)                -> [{'held':'≤1 年','rate':0.16,'amount':680000}, …]

核对记录(2026-07-17):仓库原先在两处把 **PR 第三套 ABSD 写成 30%**
(`researcher/legacy/valuation/dataset.py`、`property-buy-sell-advisory` SKILL)。经 IRAS 与 MAS
2023-04-27 新政三次交叉核对,正确值是 **35%** —— 已一并更正。两个内部来源一致不等于对:
它们同源。
"""
from __future__ import annotations

# ------------------------------------------------------------------ BSD
BSD_TIERS = [(180_000, 0.01), (180_000, 0.02), (640_000, 0.03), (500_000, 0.04),
             (1_500_000, 0.05), (float("inf"), 0.06)]
BSD_META = {"source": "IRAS — Buyer's Stamp Duty (residential)",
            "effective": "2023-02-15",
            "verify_at": "https://www.iras.gov.sg/taxes/stamp-duty/for-property"}

# ------------------------------------------------------------------ ABSD
# 生效 2023-04-27(MAS/MOF/MND)。买家画像以**购入当日**为准。
ABSD_RATES = {
    "SC": {1: 0.00, 2: 0.20, 3: 0.30},
    "PR": {1: 0.05, 2: 0.30, 3: 0.35},
    "FOREIGNER": {1: 0.60, 2: 0.60, 3: 0.60},
    "ENTITY": {1: 0.65, 2: 0.65, 3: 0.65},
    "TRUSTEE": {1: 0.65, 2: 0.65, 3: 0.65},
}
PROFILES = {"SC": "新加坡公民", "PR": "永久居民", "FOREIGNER": "外国人",
            "ENTITY": "公司/实体", "TRUSTEE": "信托"}
ABSD_META = {"source": "IRAS / MAS-MOF-MND 2023-04-27 新政",
             "effective": "2023-04-27",
             "verify_at": "https://www.iras.gov.sg/taxes/stamp-duty/for-property/"
                          "buying-or-acquiring-property/additional-buyer's-stamp-duty-(absd)",
             "note": "夫妻联名等情形有 remission;FTA 国民的外国人身份另有豁免。"
                     "本表只算标准情形。"}

# ------------------------------------------------------------------ SSD
# 2025-07-04 起购入的住宅:持有期 4 年(原 3 年),各档 +4pp。起算以**行使 OTP 之日**为准。
SSD_BANDS = [(1, 0.16), (2, 0.12), (3, 0.08), (4, 0.04)]
SSD_META = {"source": "IRAS / MAS — 2025-07-04 起购入的住宅",
            "effective": "2025-07-04",
            "verify_at": "https://www.iras.gov.sg/taxes/stamp-duty/for-property/"
                         "selling-or-disposing-property/seller's-stamp-duty-(ssd)",
            "note": "无过渡期;起算日 = 行使 OTP 之日。按**卖出价**计。"}


def bsd(price: float) -> float:
    duty, rem = 0.0, float(price)
    for band, rate in BSD_TIERS:
        take = min(rem, band)
        duty += take * rate
        rem -= take
        if rem <= 0:
            break
    return duty


def absd(price: float, profile: str, count: int = 1) -> float:
    p = (profile or "SC").upper()
    if p not in ABSD_RATES:
        raise ValueError(f"未知买家画像 {profile!r};可选:{sorted(ABSD_RATES)}")
    return float(price) * ABSD_RATES[p][min(max(int(count), 1), 3)]


def ssd_rate(holding_years: float) -> float:
    for yrs, rate in SSD_BANDS:
        if holding_years <= yrs:
            return rate
    return 0.0


def ssd(price: float, holding_years: float) -> float:
    return float(price) * ssd_rate(holding_years)


def entry_costs(price: float, profile: str = "SC", count: int = 1,
                legal: float = 3_500.0) -> dict:
    """买入侧现金成本。中介佣金不含 —— landed 买方通常不付佣(卖方付),写死一个数会造成误导。"""
    b, a = bsd(price), absd(price, profile, count)
    return {"price": price, "profile": profile, "count": count,
            "bsd": round(b), "absd": round(a), "legal": round(legal),
            "absd_rate": ABSD_RATES[profile.upper()][min(max(int(count), 1), 3)],
            "total": round(b + a + legal),
            "total_pct": round((b + a + legal) / price, 4)}


def ssd_clock(price: float) -> list[dict]:
    """卖出侧:持有多久、SSD 多少。短持有期上这一项主导整个成本结构。"""
    out = [{"held": f"≤{y} 年", "rate": r, "amount": round(price * r)}
           for y, r in SSD_BANDS]
    out.append({"held": ">4 年", "rate": 0.0, "amount": 0})
    return out


def breakeven_gain_pct(price: float, profile: str = "SC", count: int = 1,
                       holding_years: float = 5.0, agent_pct: float = 0.02) -> float:
    """卖出价需要比买入价高多少,才刚好覆盖买入成本 + SSD + 中介佣金(不含持有成本/利息)。

    近似解:exit*(1 - ssd_rate - agent) = price + entry_total  ->  exit/price - 1
    """
    entry = entry_costs(price, profile, count)["total"]
    r = next((rate for y, rate in SSD_BANDS if holding_years <= y), 0.0)
    net = 1.0 - r - agent_pct
    if net <= 0:
        return float("inf")
    return ((price + entry) / net) / price - 1.0
