# RE_search — 跨源研究 agent / cross-source research agent

积累**可复用的 skills**(知道*怎么找数据*、*怎么比较*、*怎么分析*),在多个数据源上工作。
核心理念:**数据靠 Claude 用现成能力去拿**——网页用 `WebFetch`/`WebSearch`,安卓 App 用
`research/mbx.py`(adb UI 自动化)——**不绑定某个固定 tool**。skills 是核心资产,放在
`.claude/skills/`,Claude 会自动发现并调用。

> Accumulate reusable **skills** (how to *find*, *compare*, *analyse* data) across data sources.
> Data is gathered by Claude with whatever is available — `WebFetch`/`WebSearch` for the web, the
> `research/mbx.py` adb harness for Android apps — **no fixed tool required**. Skills are the core
> asset and live in `.claude/skills/` (auto-discovered).

## 首个案例 / first worked example

新加坡 **Spottiswoode Suites #18-03**(永久地契 743 sqft 三房)估值 —— 数据通过 UI 自动化从
PropNex Investment Suite 读出,独立可比成交模型得出公允价 **S$1.686M ($2,269 psf)**。报告:
[`deliverables/Spottiswoode_18-03_Valuation_Report.html`](deliverables/Spottiswoode_18-03_Valuation_Report.html)。

## 布局 / layout

```
.claude/skills/        ★ 核心资产:原生 Claude Code skills(带 frontmatter,自动发现)
  read-investment-suite/ harvest-scrolling-android-table/
  value-a-property/ property-buy-sell-advisory/
researcher/            分析"大脑"(Python 包)
  valuation/           可比成交调整估值引擎(可对任意房源估价)
  sources/             取数适配器(android_adb；未来 web / xiaohongshu)
  pipelines/           端到端流程(harvest → value → advise)
research/              抓取/探索脚本:mbx.py(adb 取屏+解析+操作)、harvest_sale.py、captures/(留痕)
deliverables/          报告生成器 + 产物(HTML 报告、开发简报)
```

## 跑起来 / run

```powershell
# 估值模型(任意房源:改 researcher/valuation/run.py 里的 Subject/Comp 即可)
python -m researcher.valuation.run
# 生成 HTML 报告（默认输出到 G:\My Drive\004 RES\REsearch_Reports；
# 可用 RESEARCH_REPORTS_DIR 覆盖，G: 未挂载时回退到 deliverables/）
python deliverables/build_report.py
# 读一个安卓 App(需先登录、adb 可连):见 .claude/skills/read-investment-suite
python research/mbx.py cap my_screen
```

## 与 mobile_bridge 的关系 / relationship to mobile_bridge

[`mobile_bridge`](https://github.com/kingther94c/mobile_bridge) 是一个**独立**的工具仓库(通过
UI 自动化读安卓 App)。本仓库**不依赖**它的代码——`research/mbx.py` 直接调用 `adb`。当某个 skill
想用 mobile_bridge 那条已测试的 Appium 路径时,再 `pip install -e ../mobile_bridge` 即可。
依赖箭头单向:`RE_search → mobile_bridge`,绝不反向。详见 [`ARCHITECTURE.md`](ARCHITECTURE.md)。
