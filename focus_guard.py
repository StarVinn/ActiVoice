"""Time-windowed distraction blocker for Vinn Mode."""

import time
from datetime import datetime, time as clock_time
from zoneinfo import ZoneInfo

try:
    import psutil
except ImportError:
    psutil = None
try:
    import pygetwindow as gw
except ImportError:
    gw = None
try:
    import win32process
except ImportError:
    win32process = None

DEFAULT_BLACKLIST = ["Genshin Impact", "YouTube", "TikTok", "Steam", "Netflix"]


def vinn_mode_now(start="08:00", end="17:00"):
    now = datetime.now(ZoneInfo("Asia/Jakarta")).time()
    return clock_time.fromisoformat(start) <= now <= clock_time.fromisoformat(end)


def focus_guard_loop(
    stop_event,
    hud=None,
    speak=None,
    blacklist=None,
    start="08:00",
    end="17:00",
    interval=30,
    enabled_event=None,
):
    blocked = [item.lower() for item in (blacklist or DEFAULT_BLACKLIST)]
    detected_at = {}
    while not stop_event.wait(interval):
        if enabled_event is not None and not enabled_event.is_set():
            continue
        if not vinn_mode_now(start, end) or not gw:
            continue
        try:
            active_pids = set()
            for window in gw.getAllWindows():
                if hasattr(window, "isVisible") and not window.isVisible:
                    continue
                if hasattr(window, "isMinimized") and window.isMinimized:
                    continue
                title = (window.title or "").lower()
                if not title or not any(item in title for item in blocked):
                    continue

                pid = None
                if win32process and getattr(window, "_hWnd", None):
                    try:
                        _, pid = win32process.GetWindowThreadProcessId(window._hWnd)
                    except Exception:
                        pid = None
                if not pid:
                    continue

                active_pids.add(pid)
                now = time.monotonic()
                first_seen = detected_at.get(pid)
                if first_seen is None:
                    detected_at[pid] = now
                    if hud:
                        hud.set_state("SAD", "Focus mode is active.", 5)
                    if speak:
                        speak("Hey Vinn, shouldn't you be coding right now? Please close it.", "SAD", hud)
                    continue
                if now - first_seen < 60:
                    continue

                try:
                    if psutil:
                        psutil.Process(pid).kill()
                    else:
                        continue
                except Exception:
                    continue
                print(f"[focus] terminated blacklisted process {pid}.", flush=True)
                detected_at.pop(pid, None)
                if hud:
                    hud.set_state("SAD", "Time's up. I closed it for you.", 5)
                if speak:
                    speak("Time's up Vinn! I closed it for you. Now get back to work!", "SAD", hud)
                    break
            for pid in set(detected_at) - active_pids:
                detected_at.pop(pid, None)
        except Exception as exc:
            print(f"[focus] {exc}", flush=True)
