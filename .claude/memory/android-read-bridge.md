---
name: android-read-bridge
description: "mobile_bridge repo — emulator ops + PropertyGuru explorer (Appium service retired 2026-07-18), toolchain locations, parser gotcha"
metadata: 
  node_type: memory
  type: project
  originSessionId: 00e62779-5c6e-4a94-8f62-60034e67882f
---

`mobile_bridge` (since the 2026-07-18 refactor) = **Android emulator ops + raw-adb
read-only UI explorers**. Live surface: `core/adb.py` (retrying AdbDevice transport,
screen geometry from `wm size`), `core/ui_tree.py` (UiAutomator XML parser),
`apps/propertyguru_explorer.py` (+ `scripts/propertyguru.ps1`, Codex skill
`explore-propertyguru`). Tests are offline stdlib-only: `python -m pytest` (~30).

**Retired to `legacy/` (frozen, do not extend):** the original Appium/FastAPI
read-bridge service, the `Driver`/`FakeAndroidDriver` stack, app profiles, and the
Investment Suite explorer (IS harvesting is owned by RE_search `research/lib/mbx.py`;
this repo only supplies the running emulator). Rationale in `legacy/README.md`.

**Emulator:** the real `mb_play` AVD lives repo-locally in `.local/android/avd/`
(gitignored — never scan/wipe/commit). Start:
`scripts\start_emulator.ps1 -AvdName mb_play`. Device profile truth lives in
AGENTS.md: Pixel 6 portrait **1080x2400 @ 420dpi**, rotation locked 0 (the old
2560x1600 landscape config triggers tablet layouts).

**Toolchain on this machine (don't reinstall):** Python 3.12
(`%LOCALAPPDATA%\Programs\Python\Python312`), Android SDK at `D:\Android\Sdk`
(resolve `ANDROID_HOME` first; `%LOCALAPPDATA%\Android\Sdk` is only a fallback),
portable Temurin JDK 17 at `C:\Users\remoteuser\android-tools\jdk\jdk-17.0.19+10`,
repo venv `.venv`.

**Non-obvious gotcha (cost real debugging):** Appium UiAutomator2 `page_source` uses
the element's CLASS NAME as the XML tag (`<android.widget.TextView ...>`), while adb
`uiautomator dump` uses `<node>`. `core/ui_tree.py` accepts both — keep it that way or
every real-device read returns 0 nodes. See [[kelvin-user]].
