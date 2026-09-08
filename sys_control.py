"""Windows controls used by ActiVoice background services."""

import ctypes
import time
import threading

import win32api
import win32con
import win32gui

HWND_BROADCAST = getattr(win32con, "HWND_BROADCAST", 0xFFFF)
WM_APPCOMMAND = getattr(win32con, "WM_APPCOMMAND", 0x0319)
APPCOMMAND_MEDIA_PLAY_PAUSE = getattr(win32con, "APPCOMMAND_MEDIA_PLAY_PAUSE", 14)
APPCOMMAND_MEDIA_NEXTTRACK = getattr(win32con, "APPCOMMAND_MEDIA_NEXTTRACK", 11)
APPCOMMAND_MEDIA_PREVIOUSTRACK = getattr(win32con, "APPCOMMAND_MEDIA_PREVIOUSTRACK", 12)

try:
    import psutil
except ImportError:
    psutil = None
try:
    import pyautogui
except ImportError:
    pyautogui = None
try:
    import pygetwindow as gw
except ImportError:
    gw = None


def find_arc_window():
    if not gw:
        return None
    return next((window for window in gw.getAllWindows() if "Arc" in (window.title or "")), None)


def prepare_arc_window(delay=0.8):
    """Restore, focus, and maximize an existing Arc window."""
    window = find_arc_window()
    if not window:
        return None
    try:
        if window.isMinimized:
            window.restore()
        window.activate()
        if not window.isMaximized:
            window.maximize()
        if pyautogui:
            pyautogui.hotkey("win", "up")
        time.sleep(delay)
    except Exception as exc:
        print(f"[Arc] {exc}", flush=True)
    return window


def spotify_control(action):
    """Broadcast a native Windows media command to background media apps."""
    command = {
        "play_pause": APPCOMMAND_MEDIA_PLAY_PAUSE,
        "next": APPCOMMAND_MEDIA_NEXTTRACK,
        "previous": APPCOMMAND_MEDIA_PREVIOUSTRACK,
    }[action]
    win32gui.SendMessage(
        HWND_BROADCAST,
        WM_APPCOMMAND,
        0,
        command << 16,
    )
    return True


def lock_workstation():
    """Lock Windows without hiding or terminating the launcher first."""
    try:
        return bool(ctypes.windll.user32.LockWorkStation())
    except AttributeError:
        return False


VOICE_COMMANDS = {
    "play music": "play",
    "resume music": "play",
    "pause music": "pause",
    "stop music": "pause",
    "next song": "next",
    "skip song": "next",
    "lock screen": "lock",
    "sleep": "lock",
}


def match_voice_command(text):
    """Return a command key only for the supported English phrases."""
    normalized = " ".join(text.lower().strip().split())
    for phrase, command in VOICE_COMMANDS.items():
        if phrase in normalized:
            return command
    return None


def execute_voice_command(command):
    """Execute a parsed voice command and return whether it succeeded."""
    if command == "play":
        return spotify_control("play_pause")
    if command == "pause":
        return spotify_control("play_pause")
    if command == "next":
        return spotify_control("next")
    if command == "lock":
        return lock_workstation()
    return False


def voice_command_loop(
    stop_event,
    on_command=None,
    language="en-US",
    device_index=None,
    energy_threshold=1000,
    dynamic_energy_threshold=False,
):
    """Listen on a worker thread using SpeechRecognition, strictly in English."""
    try:
        import speech_recognition as sr
    except ImportError:
        print("[voice] SpeechRecognition is not installed; voice controls disabled.", flush=True)
        return

    recognizer = sr.Recognizer()
    recognizer.dynamic_energy_threshold = dynamic_energy_threshold
    recognizer.energy_threshold = energy_threshold
    recognizer.pause_threshold = 0.8
    try:
        microphone = sr.Microphone(device_index=device_index)
    except Exception as exc:
        print(f"[voice] microphone unavailable: {exc}", flush=True)
        return

    while not stop_event.is_set():
        try:
            with microphone as source:
                audio = recognizer.listen(source, timeout=1, phrase_time_limit=4)
            text = recognizer.recognize_google(audio, language=language)
            command = match_voice_command(text)
            if on_command:
                on_command(command, text)
        except sr.WaitTimeoutError:
            continue
        except sr.UnknownValueError:
            continue
        except sr.RequestError as exc:
            print(f"[voice] recognition service unavailable: {exc}", flush=True)
            stop_event.wait(5)
        except Exception as exc:
            print(f"[voice] listener error: {exc}", flush=True)
            stop_event.wait(1)
def pause_workspace():
    if pyautogui:
        pyautogui.hotkey("win", "d")
    try:
        lock_workstation()
    except AttributeError:
        pass


def battery_guard(stop_event, hud=None, speak=None, on_shutdown=None, interval=30):
    """Stop safely when an unplugged battery reaches 20 percent."""
    while not stop_event.wait(interval):
        if not psutil:
            return
        try:
            battery = psutil.sensors_battery()
            if battery and battery.percent <= 20 and not battery.power_plugged:
                if hud:
                    hud.set_state("SHUTDOWN", "Battery low. I am shutting down safely.", 5)
                if speak:
                    speak("Battery is low and the charger is disconnected. Goodbye for now.", "SHUTDOWN", hud)
                if on_shutdown:
                    on_shutdown()
                return
        except Exception as exc:
            print(f"[battery] {exc}", flush=True)
