"""doctor — automated readiness check for Investment Suite harvesting.

Codifies the open-failure protocol from the read-investment-suite skill so no
judgment is needed when something is wrong: run it, read the verdict, do
exactly what it says, re-run. Exit code 0 = READY (safe to harvest);
2 = NOT READY (stop — hand the printed instruction to the user; do NOT fall
back to web data: Investment Suite is Tier-1 ground truth).

Checks, in order (each failure stops with a specific remediation):
  1. adb binary exists            (fix: install SDK platform-tools / set MBX_ADB)
  2. device serial is online      (fix: start the emulator WINDOWED)
  3. Investment Suite in foreground (fix: launch the app; command printed)
  4. UI dump parses                (fix: retry; app may be mid-animation)
  5. logged in, not on a sign-in screen (fix: USER signs in manually — never
     automate credentials)

Usage:  python doctor.py            # human/agent readable verdict
        python doctor.py --json     # machine readable
"""
from __future__ import annotations

import json
import os
import re
import shutil
import sys

if __package__:
    from ..lib import mbx
else:  # direct script run: python research/tools/doctor.py
    sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "lib"))
    import mbx

PACKAGE = "com.investmentsuite"
ACTIVITY = "com.propnex.investmentsuite.MainActivity2"
# mobile_bridge owns the emulator/AVD lifecycle; the default points there but the
# dependency is configurable instead of hardcoded (override: MBX_EMULATOR_CMD).
EMULATOR_CMD = os.environ.get(
    "MBX_EMULATOR_CMD",
    "powershell -File D:\\projects\\git_projects\\mobile_bridge\\scripts\\"
    "start_emulator.ps1 -AvdName mb_play",
)
EMULATOR_HINT = (
    "start it WINDOWED (visible, never headless) via the mobile_bridge repo:\n"
    f"      {EMULATOR_CMD}\n"
    "    then wait for the home screen and re-run doctor.\n"
    "    (override the start command with the MBX_EMULATOR_CMD env var)"
)
# nav labels that prove we are inside the logged-in app
_NAV = ("Market", "Property Analysis", "ProTrend", "ProMap")
_LOGIN = ("log in", "login", "sign in", "otp", "password", "forgot")


def _check() -> tuple[bool, list[dict]]:
    steps: list[dict] = []

    def fail(name: str, err: str, fix: str) -> tuple[bool, list[dict]]:
        steps.append({"check": name, "ok": False, "error": err, "fix": fix})
        return False, steps

    def ok(name: str, note: str = "") -> None:
        steps.append({"check": name, "ok": True, "note": note})

    # 1. adb binary (mbx resolves: MBX_ADB -> PATH -> known SDK locations)
    if not (os.path.isfile(mbx.ADB) or shutil.which(mbx.ADB)):
        return fail("adb-binary", f"adb not found (resolved to {mbx.ADB!r})",
                    "install Android SDK platform-tools, put adb on PATH, or set MBX_ADB "
                    "to the full adb.exe path")
    ok("adb-binary", mbx.ADB)

    # 2. device online
    devices = mbx.sh("devices")
    dev_lines = [l for l in devices.splitlines()[1:] if l.strip()]
    match = [l for l in dev_lines if l.startswith(mbx.SERIAL)]
    if not match:
        return fail("device-online",
                    f"serial {mbx.SERIAL} not in `adb devices` (saw: {dev_lines or 'none'})",
                    f"the emulator/device isn't running — {EMULATOR_HINT}\n"
                    "    (different serial? set MBX_SERIAL)")
    if "device" not in match[0].split():
        return fail("device-online", f"device state is {match[0].split()[-1]!r}, not 'device'",
                    "wait for the emulator to finish booting, or restart it, then re-run")
    ok("device-online", mbx.SERIAL)

    # 3. app in foreground
    focus = mbx.sh("shell", "dumpsys", "window") or ""
    m = re.search(r"mCurrentFocus=.*?\s([\w.]+)/[\w.$]+", focus)
    front = m.group(1) if m else ""
    if front != PACKAGE:
        return fail("app-foreground",
                    f"foreground package is {front or 'unknown'!r}, want {PACKAGE!r}",
                    f"launch the app:\n      adb -s {mbx.SERIAL} shell am start -n {PACKAGE}/{ACTIVITY}\n"
                    "    then wait ~5s and re-run doctor")
    ok("app-foreground", PACKAGE)

    # 4. UI dump parses
    try:
        texts = [n["text"] or n["desc"] for n in mbx.parse(mbx.dump_xml())]
        texts = [t for t in texts if t]
    except RuntimeError as e:
        return fail("ui-dump", str(e),
                    "the app may be mid-animation or the device stalled — wait 5s and re-run; "
                    "if it persists, restart the app")
    if not texts:
        return fail("ui-dump", "dump parsed but zero visible texts",
                    "screen may be blank/splash — wait and re-run")
    ok("ui-dump", f"{len(texts)} visible texts")

    # 5. logged in (bottom nav present, no sign-in markers)
    lower = [t.lower() for t in texts]
    nav_hits = sum(1 for n in _NAV if n in texts)
    login_hits = [t for t in lower if any(k in t for k in _LOGIN)]
    if nav_hits >= 2:
        ok("logged-in", f"nav labels present ({nav_hits}/4)")
    elif login_hits:
        return fail("logged-in", f"sign-in screen detected (saw {login_hits[:3]})",
                    "STOP — the USER must sign in manually in the emulator window "
                    "(UI only; never automate credentials). Ask them to confirm, then re-run.")
    else:
        return fail("logged-in",
                    f"no bottom-nav labels on screen (first texts: {texts[:6]})",
                    "the app is open but not on a main screen — press Back a few times "
                    "(python mbx.py back) or ask the user to bring it to the dashboard, then re-run")
    return True, steps


def main() -> int:
    ready, steps = _check()
    if "--json" in sys.argv:
        print(json.dumps({"ready": ready, "steps": steps}, ensure_ascii=False, indent=1))
    else:
        for s in steps:
            mark = "PASS" if s["ok"] else "FAIL"
            print(f"[{mark}] {s['check']}: {s.get('note') or s.get('error')}")
            if not s["ok"]:
                print(f"    -> {s['fix']}")
        print("\nREADY — safe to harvest." if ready else
              "\nNOT READY — do the fix above, wait for the user if it needs them. "
              "Do NOT fall back to web data (Tier-1 rule).")
    return 0 if ready else 2


if __name__ == "__main__":
    sys.exit(main())
