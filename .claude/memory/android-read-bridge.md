---
name: android-read-bridge
description: "mobile_bridge project — Android Read-Bridge service, toolchain locations, and worktree isolation"
metadata: 
  node_type: memory
  type: project
  originSessionId: 00e62779-5c6e-4a94-8f62-60034e67882f
---

`mobile_bridge` is a local FastAPI service that reads text+images from an Android app
via UI automation (Appium + UiAutomator2) and returns LLM-friendly JSON for an AI
agent. Pure UI reading (no reverse engineering). Real target = a property-agent app;
safe public test stand-in = Wikipedia Android.

**Two-tier tests:** Tier 1 = offline, a `FakeAndroidDriver` serving synthetic property
screens (pytest, no device). Tier 2 = live emulator + Appium against Wikipedia
(`tests/tier2`, skipped unless `MB_TIER2=1`). App selectors are isolated per profile
in `mobile_bridge/apps/`.

**Worktree isolation (important):** active development runs in the git worktree
`.claude/worktrees/android-wrapper` on branch `wt/android-wrapper`, because a concurrent
`codex/*` process operates on the main checkout. Do not work in the main checkout.

**Toolchain already installed on this machine (don't reinstall):**
- Python 3.12 at `C:\Users\remoteuser\AppData\Local\Programs\Python\Python312`
- Portable Temurin JDK 17 at `C:\Users\remoteuser\android-tools\jdk\jdk-17.0.19+10`
- Appium 3.5.2 global (`%APPDATA%\npm\appium.cmd`) + uiautomator2 driver installed
- Android SDK target dir: `%LOCALAPPDATA%\Android\Sdk`
- venv in the worktree at `.venv`; run tests with `.venv\Scripts\python -m pytest -W ignore`

Machine is a physical Dell Inspiron 5680 (HypervisorPresent=True). **Tier 2 is set up
and verified working:** AVD `mb_pixel` (android-34 google_apis x86_64) boots with WHPX;
Wikipedia (`org.wikipedia`, F-Droid build 50595) is installed with first-run
onboarding + personalization already completed; `tests/tier2` passes (2 tests) with the
Appium server running on 127.0.0.1:4723. Start it: `scripts\start_emulator.ps1` +
`scripts\start_appium.ps1`, then `MB_TIER2=1 MB_APP_PROFILE=wikipedia pytest tests/tier2`.

**Non-obvious gotcha (cost real debugging):** Appium UiAutomator2 `page_source` uses the
element's CLASS NAME as the XML tag (`<android.widget.TextView ...>`), while adb
`uiautomator dump` (and the FakeDriver) use `<node>`. The parser must accept both or
every real-device read returns 0 nodes. Also: this Wikipedia build's search is a 2-step
bottom-nav flow (`nav_tab_search` -> `search_card` -> `search_src_text`) and result rows
have no resource-id. See [[kelvin-user]].
