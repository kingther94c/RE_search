"""mbx — minimal, reusable Android read/operate extractor (adb only).

Drives the PropNex Investment Suite app on emulator-5554 via UI automation
only (no reverse engineering): screencap + uiautomator dump + parse the
accessibility tree into ordered text / structured nodes, plus tap-by-text,
tap-by-xy, swipe/scroll, back. Every capture saves a PNG + XML + JSON so the
whole research run is auditable and replayable.

Usage:
    python mbx.py cap <name>           # capture + dump current screen
    python mbx.py tap "<text>"         # tap node whose text == / contains text
    python mbx.py xy <x> <y>           # tap coordinate
    python mbx.py swipe up|down|left|right [frac]
    python mbx.py back
    python mbx.py texts                # print ordered visible texts
"""
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
import xml.etree.ElementTree as ET

# The app's UI text carries glyphs outside the Windows console codepage (a sort
# arrow U+25BC on every table header). Printing one to a cp1252 stdout raises
# UnicodeEncodeError and kills the run mid-harvest — so normalise the streams
# once, here, for every script that imports mbx (harvesters, doctor).
for _s in (sys.stdout, sys.stderr):
    if hasattr(_s, "reconfigure"):
        _s.reconfigure(encoding="utf-8", errors="replace")


def _find_adb() -> str:
    """MBX_ADB -> PATH -> known SDK locations. Hardcoding one absolute path made
    the harness depend on a stale SDK copy surviving on C:."""
    env = os.environ.get("MBX_ADB")
    if env:
        return env
    on_path = shutil.which("adb")
    if on_path:
        return on_path
    for cand in (r"D:\Android\Sdk\platform-tools\adb.exe",
                 os.path.expandvars(r"%LOCALAPPDATA%\Android\Sdk\platform-tools\adb.exe")):
        if os.path.isfile(cand):
            return cand
    return "adb"          # let it fail loudly with a clear "not found" from doctor


ADB = _find_adb()
SERIAL = os.environ.get("MBX_SERIAL", "emulator-5554")
OUT = os.environ.get(
    "MBX_OUT",
    os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "captures"),
)
os.makedirs(OUT, exist_ok=True)

_BOUNDS = re.compile(r"\[(\d+),(\d+)\]\[(\d+),(\d+)\]")


def sh(*args: str) -> str:
    # adb emits UTF-8; without encoding= Python would use the Windows locale
    # codepage (cp1252/cp936) and silently mojibake all non-ASCII UI text.
    r = subprocess.run(
        [ADB, "-s", SERIAL, *args],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
    )
    if r.returncode != 0:
        print(f"[adb!] rc={r.returncode} {' '.join(args[:3])}: {r.stderr.strip()[:200]}",
              file=sys.stderr)
    return r.stdout or ""


def screen_size() -> tuple[int, int]:
    out = sh("shell", "wm", "size")
    m = re.search(r"(\d+)x(\d+)", out)
    return (int(m.group(1)), int(m.group(2))) if m else (2560, 1600)


def _center(bounds: str) -> tuple[int, int] | None:
    m = _BOUNDS.search(bounds or "")
    if not m:
        return None
    x1, y1, x2, y2 = map(int, m.groups())
    return (x1 + x2) // 2, (y1 + y2) // 2


def dump_xml() -> str:
    sh("shell", "uiautomator", "dump", "/sdcard/_mbx.xml")
    xml = sh("exec-out", "cat", "/sdcard/_mbx.xml")
    if not xml.strip():
        raise RuntimeError(
            "uiautomator dump came back empty — device offline / app not in foreground? "
            f"(adb={ADB}, serial={SERIAL})"
        )
    return xml


def parse(xml: str) -> list[dict]:
    """Flatten every node with text/desc/id/bounds/clickable in document order."""
    nodes: list[dict] = []
    try:
        root = ET.fromstring(xml)
    except ET.ParseError:
        return nodes

    def walk(el):
        text = (el.get("text") or "").strip()
        desc = (el.get("content-desc") or "").strip()
        rid = el.get("resource-id") or ""
        if text or desc:
            nodes.append(
                {
                    "text": text,
                    "desc": desc,
                    "id": rid.split("/")[-1] if rid else "",
                    "full_id": rid,
                    "cls": el.get("class") or "",
                    "clickable": el.get("clickable") == "true",
                    "bounds": el.get("bounds") or "",
                    "center": _center(el.get("bounds") or ""),
                }
            )
        for ch in list(el):
            walk(ch)

    walk(root)
    return nodes


def capture(name: str) -> list[dict]:
    sh("shell", "screencap", "-p", "/sdcard/_mbx.png")
    sh("pull", "/sdcard/_mbx.png", os.path.join(OUT, f"{name}.png"))
    xml = dump_xml()
    with open(os.path.join(OUT, f"{name}.xml"), "w", encoding="utf-8") as f:
        f.write(xml)
    nodes = parse(xml)
    with open(os.path.join(OUT, f"{name}.json"), "w", encoding="utf-8") as f:
        json.dump(nodes, f, ensure_ascii=False, indent=2)
    texts = [n["text"] or n["desc"] for n in nodes]
    print(f"[cap] {name}: {len(nodes)} nodes, {len(texts)} texts -> {OUT}")
    for i, t in enumerate(texts, 1):
        print(f"{i:3}: {t}")
    return nodes


def find(text: str, contains: bool = True) -> dict | None:
    nodes = parse(dump_xml())
    for n in nodes:
        hay = n["text"] or n["desc"]
        if (contains and text.lower() in hay.lower()) or hay == text:
            return n
    return None


def tap_text(text: str) -> None:
    n = find(text)
    if not n or not n["center"]:
        print(f"[tap] NOT FOUND: {text!r}")
        return
    x, y = n["center"]
    sh("shell", "input", "tap", str(x), str(y))
    print(f"[tap] {text!r} -> ({x},{y}) [{n['cls']}]")


def tap_xy(x: int, y: int) -> None:
    sh("shell", "input", "tap", str(x), str(y))
    print(f"[tap] ({x},{y})")


def swipe(direction: str, frac: float = 0.6) -> None:
    w, h = screen_size()
    cx, cy = w // 2, h // 2
    dx = int(w * frac / 2)
    dy = int(h * frac / 2)
    moves = {
        "up": (cx, cy + dy, cx, cy - dy),     # content moves up (scroll down)
        "down": (cx, cy - dy, cx, cy + dy),
        "left": (cx + dx, cy, cx - dx, cy),
        "right": (cx - dx, cy, cx + dx, cy),
    }
    x1, y1, x2, y2 = moves[direction]
    sh("shell", "input", "swipe", str(x1), str(y1), str(x2), str(y2), "400")
    print(f"[swipe] {direction} {(x1,y1)}->{(x2,y2)}")


def swipe_region(x1, y1, x2, y2, dur=400) -> None:
    sh("shell", "input", "swipe", str(x1), str(y1), str(x2), str(y2), str(dur))
    print(f"[swipe_region] {(x1,y1)}->{(x2,y2)}")


def type_text(text: str) -> None:
    """Type into the focused field via real key events (adb input text).
    Spaces must be %s-escaped for adb; tap the field first to focus it."""
    sh("shell", "input", "text", text.replace(" ", "%s"))
    print(f"[type] {text!r}")


def clear_field(chars: int = 40) -> None:
    """Clear the focused text field: jump to end, then backspace `chars` times.
    (adb has no select-all; keyevent 123=MOVE_END, 67=DEL accepts a batch.)"""
    sh("shell", "input", "keyevent", "123")
    for _ in range(0, chars, 10):
        sh("shell", "input", "keyevent", *(["67"] * 10))
    print(f"[clear] up to {chars} chars")


def back() -> None:
    sh("shell", "input", "keyevent", "4")
    print("[back]")


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "texts"
    if cmd == "cap":
        capture(sys.argv[2])
    elif cmd == "tap":
        tap_text(sys.argv[2])
    elif cmd == "xy":
        tap_xy(int(sys.argv[2]), int(sys.argv[3]))
    elif cmd == "swipe":
        swipe(sys.argv[2], float(sys.argv[3]) if len(sys.argv) > 3 else 0.6)
    elif cmd == "region":
        swipe_region(*map(int, sys.argv[2:6]))
    elif cmd == "type":
        type_text(sys.argv[2])
    elif cmd == "clear":
        clear_field(int(sys.argv[2]) if len(sys.argv) > 2 else 40)
    elif cmd == "back":
        back()
    elif cmd == "texts":
        for i, n in enumerate(parse(dump_xml()), 1):
            print(f"{i:3}: {n['text'] or n['desc']}  [{n['id']}]")
    else:
        print(__doc__)
