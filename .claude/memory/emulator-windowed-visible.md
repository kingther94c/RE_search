---
name: emulator-windowed-visible
description: "When driving the Android emulator (esp. Investment Suite), run it WINDOWED/visible so Kelvin can watch and intervene — never headless for interactive work"
metadata: 
  node_type: memory
  type: feedback
  originSessionId: 05a8a0f6-1bf9-4533-9ace-a43bc7336084
---

Whenever the Android emulator is used for interactive property research (driving PropNex
Investment Suite via `mbx.py`/adb), it **must be launched windowed (visible), not headless** —
so Kelvin can watch the automation live and step in at any moment (sign in, correct navigation,
tap a control).

**Why:** Kelvin's directive (2026-07-03, "使用安卓模拟器的时候请打开ui这样用户可以方便介入").
Login is manual and UI-only; navigation can go off-track — a visible window is what lets the
human intervene. adb input reaches a headless emulator fine, so nothing forces a window; it must
be a deliberate default.

**How to apply:**
- Launch via mobile_bridge `scripts\start_emulator.ps1` — it boots **windowed by default**;
  `-NoWindow` (adds `-no-window`) is CI-only, never for a research run. For Investment Suite use
  `-AvdName mb_play` (the 2560x1600 tablet).
- Before driving the app, confirm the emulator window is up; if it may be hidden, ask the user to
  bring it to the foreground.
- This pairs with the open-failure protocol in the `read-investment-suite` skill: on any
  emulator/app problem, pause, report the exact error, and let the user act in the visible UI.
See [[data-source-trust-hierarchy]], [[read-investment-suite (skill)]], [[kelvin-user]].
