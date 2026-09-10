"""Windows controls used by ActiVoice background services."""

import ctypes
import time
import threading

import win32con
import win32gui

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
    """Control Spotify directly, with a native media-key fallback."""
    app_command = {
        "play_pause": getattr(win32con, "APPCOMMAND_MEDIA_PLAY_PAUSE", 14),
        "pause": 0x2F,
        "next": getattr(win32con, "APPCOMMAND_MEDIA_NEXTTRACK", 11),
        "previous": getattr(win32con, "APPCOMMAND_MEDIA_PREVIOUSTRACK", 12),
    }[action]
    virtual_key = {
        "play_pause": 0xCD,
        "pause": 0xCD,
        "next": 0xB0,
        "previous": 0xB1,
    }[action]

    try:
        spotify_hwnd = win32gui.FindWindowEx(0, 0, "SpotifyMainWindow", None)
    except Exception:
        spotify_hwnd = None

    def find_spotify_window(hwnd, _):
        nonlocal spotify_hwnd
        title = win32gui.GetWindowText(hwnd)
        class_name = win32gui.GetClassName(hwnd)
        if spotify_hwnd is None and ("spotify" in title.lower() or class_name.lower() == "spotifymainwindow"):
            spotify_hwnd = hwnd
            return False
        return True

    try:
        win32gui.EnumWindows(find_spotify_window, None)
        if spotify_hwnd:
            result = win32gui.SendMessage(
                spotify_hwnd,
                getattr(win32con, "WM_APPCOMMAND", 0x0319),
                0,
                app_command << 16,
            )
            if result:
                print(f"[Spotify Control] Triggered: {action} (Success)", flush=True)
                return True
    except Exception:
        pass

    try:
        user32 = ctypes.windll.user32
        user32.keybd_event(virtual_key, 0, 0, 0)
        time.sleep(0.1)
        user32.keybd_event(virtual_key, 0, 2, 0)
        print(f"[Spotify Control] Triggered: {action} (Success)", flush=True)
        return True
    except Exception:
        print(f"[Spotify Control] Triggered: {action} (Failed)", flush=True)
        return False


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
        return spotify_control("pause")
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
    processing_event=None,
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
            if processing_event and processing_event.is_set():
                stop_event.wait(0.05)
                continue
            with microphone as source:
                audio = recognizer.listen(source, timeout=1, phrase_time_limit=4)
            text = recognizer.recognize_google(audio, language=language)
            audio = None
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


def battery_guard(
    stop_event,
    hud=None,
    speak=None,
    on_shutdown=None,
    interval=30,
    threshold_provider=None,
    shutdown_delay=10,
):
    """Monitor power changes and schedule a cancellable low-battery shutdown.

    A charger connection always clears ``is_shutdown_pending`` and cancels the
    active timer before any other battery logic runs.  This prevents a timer
    started while unplugged from shutting down a device that is now charging.
    """
    is_shutdown_pending = False
    shutdown_timer = None
    shutdown_state_lock = threading.Lock()
    last_plugged_in = None
    low_warning_announced = False
    critical_warning_announced = False

    def cancel_pending_shutdown():
        """Atomically cancel the scheduled shutdown, if there is one."""
        nonlocal is_shutdown_pending, shutdown_timer
        with shutdown_state_lock:
            if shutdown_timer:
                shutdown_timer.cancel()
                shutdown_timer = None
            is_shutdown_pending = False

    def trigger_shutdown():
        """Run only if the charger has not cancelled this scheduled action."""
        nonlocal is_shutdown_pending
        # Re-read the power source because Timer.cancel() cannot stop a timer
        # callback that has already begun on another thread.
        try:
            current_battery = psutil.sensors_battery() if psutil else None
            if current_battery and current_battery.power_plugged:
                cancel_pending_shutdown()
                return
        except Exception as exc:
            print(f"[battery] shutdown verification failed: {exc}", flush=True)
            return
        with shutdown_state_lock:
            if not is_shutdown_pending or stop_event.is_set():
                return
            is_shutdown_pending = False
        if stop_event.is_set():
            return
        if on_shutdown:
            on_shutdown()

    while not stop_event.is_set():
        if not psutil:
            return
        try:
            battery = psutil.sensors_battery()
            threshold = threshold_provider() if threshold_provider else 40
            if not battery:
                if stop_event.wait(interval):
                    return
                continue

            plugged_in = battery.power_plugged
            if plugged_in:
                # This is deliberately first: charging invalidates every
                # unplugged warning, event flag, and pending shutdown timer.
                cancel_pending_shutdown()
                low_warning_announced = False
                critical_warning_announced = False
                if last_plugged_in is not True and speak:
                    message = "Charger connected. Shutdown cancelled and battery charging has started."
                    if hud:
                        hud.set_state("IDLE", message, 5)
                    speak(message, "IDLE", hud)
            else:
                if last_plugged_in is not False and speak:
                    message = "Charger disconnected. I will monitor the battery closely."
                    if hud:
                        hud.set_state("TIRED", message, 5)
                    speak(message, "TIRED", hud)

                critical_threshold = min(15, threshold)
                if battery.percent <= critical_threshold:
                    if not critical_warning_announced:
                        message = (
                            f"Critical battery warning. Battery is at {battery.percent:.0f} percent "
                            "and the charger is disconnected. Shutdown will begin shortly."
                        )
                        if hud:
                            hud.set_state("SHUTDOWN", message, 5)
                        if speak:
                            speak(message, "SHUTDOWN", hud)
                        critical_warning_announced = True
                    if not is_shutdown_pending:
                        with shutdown_state_lock:
                            # The lock prevents duplicate timers if a future
                            # caller invokes this guard's state transition.
                            if not is_shutdown_pending:
                                is_shutdown_pending = True
                                shutdown_timer = threading.Timer(shutdown_delay, trigger_shutdown)
                                shutdown_timer.daemon = True
                                shutdown_timer.start()
                elif battery.percent <= threshold and not low_warning_announced:
                    message = (
                        f"Low battery warning. Battery is at {battery.percent:.0f} percent. "
                        "Please connect the charger soon."
                    )
                    if hud:
                        hud.set_state("TIRED", message, 5)
                    if speak:
                        speak(message, "TIRED", hud)
                    low_warning_announced = True
                elif battery.percent > threshold:
                    low_warning_announced = False
                    critical_warning_announced = False
                    # A recovered battery should not retain an old shutdown.
                    cancel_pending_shutdown()

            last_plugged_in = plugged_in
        except Exception as exc:
            print(f"[battery] {exc}", flush=True)
        if stop_event.wait(interval):
            cancel_pending_shutdown()
            return
