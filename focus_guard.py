"""Time-windowed distraction blocker for Vinn Mode."""

from datetime import datetime, time as clock_time
from zoneinfo import ZoneInfo

try:
    import pygetwindow as gw
except ImportError:
    gw = None

DEFAULT_BLACKLIST = ["Genshin Impact", "Roblox", "YouTube", "Valorant", "Steam"]


def vinn_mode_now(start="08:00", end="17:00"):
    now = datetime.now(ZoneInfo("Asia/Jakarta")).time()
    return clock_time.fromisoformat(start) <= now <= clock_time.fromisoformat(end)


def focus_guard_loop(stop_event, hud=None, speak=None, blacklist=None, start="08:00", end="17:00", interval=3):
    blocked = [item.lower() for item in (blacklist or DEFAULT_BLACKLIST)]
    while not stop_event.wait(interval):
        if not vinn_mode_now(start, end) or not gw:
            continue
        try:
            for window in gw.getAllWindows():
                title = (window.title or "").lower()
                if title and any(item in title for item in blocked):
                    window.minimize()
                    if hud:
                        hud.set_state("ANGRY", "Focus mode is active.", 4)
                    if speak:
                        speak("Back to work, please.", "ANGRY", hud)
                    break
        except Exception as exc:
            print(f"[focus] {exc}", flush=True)
