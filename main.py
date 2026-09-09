"""ActiVoice entry point: Grace HUD, guards, and the existing workspace launcher."""

import ctypes
import json
import os
import random
import re
import sys
import threading
import time
import traceback
from datetime import datetime, time as clock_time
from zoneinfo import ZoneInfo

try:
    import psutil
except ImportError:
    psutil = None

os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")
os.environ.setdefault("TORCH_CPP_LOG_LEVEL", "ERROR")

from focus_guard import focus_guard_loop
from overlay_hud import GraceHUD
from sys_control import battery_guard, execute_voice_command, voice_command_loop
from voice_engine import speak

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(BASE_DIR, "workspace-config.json")
MEDIA_RESPONSES = ["Got it, Sir!", "On it!", "Sure thing!", "Consider it done!", "Right away, Sir!"]
LOCK_RESPONSES = [
    "Locking your workspace now.",
    "Securing your setup, catch you later!",
    "Locking up. Take a quick break, Sir!",
    "Workspace secured!",
]
EXIT_RESPONSES = [
    "Goodbye Vinn, see you!",
    "Shutting down, have a good rest, Vinn!",
    "Closing launcher now, catch you later!",
]


def execute_native_media_command(action):
    """Send one lightweight native Windows media-key press and release."""
    virtual_key = {
        "play": 0xB3,
        "pause": 0xB3,
        "next": 0xB0,
    }.get(action)
    if virtual_key is None:
        return False
    try:
        user32 = ctypes.windll.user32
        user32.keybd_event(virtual_key, 0, 0, 0)
        time.sleep(0.05)
        user32.keybd_event(virtual_key, 0, 2, 0)
        return True
    except Exception as exc:
        print(f"[MEDIA] {action} failed: {exc}", flush=True)
        return False


def get_input_device_name():
    try:
        import sounddevice as sd

        default_device = sd.default.device
        device_index = default_device[0] if isinstance(default_device, (list, tuple)) else default_device
        if device_index is not None and device_index >= 0:
            return sd.query_devices(device_index).get("name", "Unknown")
    except Exception:
        pass
    return "Unavailable"


def print_startup_menu(config):
    profile = config.get("profil_aktywny", "Default")
    sensitivity = config.get("czulosc_klasniecia", 70)
    nn_threshold = config.get("czulosc_nn", 0.11)
    input_device = get_input_device_name()

    os.system("cls" if os.name == "nt" else "clear")
    print(f"==================================================")
    print(f"  System: {profile} | Sensitivity: {sensitivity} dB | Status: LISTENING")
    print(f"  NN Threshold: {nn_threshold} | Input: {input_device}")
    print(f"==================================================")
    print()
    print("+--------------------------------------------------+")
    print("|              GRACE ACTIVOICE LAUNCHER            |")
    print("+--------------------------------------------------+")
    print()
    print("--------------------------------------------------")
    print("[ GRACE ACTIVOICE - VOICE COMMAND CHEAT SHEET ]")
    print("--------------------------------------------------")
    print("- Media Controls:")
    print('  - "play music" / "resume"    -> Play/Resume Spotify')
    print('  - "pause music" / "stop"      -> Pause Spotify')
    print('  - "skip music" / "next"       -> Skip to next track')
    print("- System Controls:")
    print('  - "lock workspace" / "sleep"  -> Lock Windows PC')
    print("- Launcher Controls:")
    print('  - "shutdown" / "exit"       -> Shutdown Launcher & Close CMD')
    print("--------------------------------------------------")
    print()


def load_config():
    with open(CONFIG_PATH, "r", encoding="utf-8") as stream:
        return json.load(stream)


def active_mode(config):
    rules = config.get("work_hours", {})
    start, end = rules.get("start", "08:00"), rules.get("end", "17:00")
    now = datetime.now(ZoneInfo("Asia/Jakarta")).time()
    return "VINN MODE" if clock_time.fromisoformat(start) <= now <= clock_time.fromisoformat(end) else "RELAX MODE"


def block_low_battery_startup():
    """Stop startup when running unplugged below the safe battery threshold."""
    if not psutil:
        return False
    try:
        battery = psutil.sensors_battery()
    except (psutil.Error, OSError):
        return False

    if battery and not battery.power_plugged and battery.percent < 50:
        print(
            f"[WARNING] Battery level is at {battery.percent:.0f}%. "
            "Launcher startup blocked to save power. Please plug in the charger.",
            flush=True,
        )
        os._exit(0)
    return False


def system_status_message():
    if not psutil:
        return "System diagnostics are unavailable because psutil is not installed."
    battery = psutil.sensors_battery()
    battery_text = "unknown"
    if battery:
        battery_text = f"{battery.percent:.0f}%"
    cpu = psutil.cpu_percent(interval=0.5)
    ram = psutil.virtual_memory().percent
    return (
        f"All systems operational Vinn. Battery is at {battery_text}, "
        f"CPU load is {cpu:.0f}%, and RAM usage is at {ram:.0f}%."
    )


def main():
    block_low_battery_startup()
    config = load_config()
    print_startup_menu(config)
    hud = GraceHUD()
    stop_event = threading.Event()
    workspace_launched = False
    workspace_launching = False
    workspace_launch_lock = threading.Lock()
    clap_stream = {"value": None}

    mode = active_mode(config)
    hud.set_state("IDLE", "STANDBY: Awaiting Activation...")
    print("[SYSTEM] STANDBY: Awaiting Activation...", flush=True)

    def launch_workspace():
        """Start the existing workspace launcher after standby activation."""
        nonlocal workspace_launched, workspace_launching
        try:
            import workspace

            if workspace.should_skip_workspace_launch():
                message = "Low battery, skipping workspace launch to save power, Vinn!"
                print(f"[POWER] {message}", flush=True)
                hud.set_state("SLEEP", message, 8)
                speak(message, hud=hud)
                workspace_launching = False
                return

            workspace.launch_profile(workspace.get_active_profile(config))
            workspace_launched = True
            workspace_launching = False
            hud.set_state("IDLE", "Workspace ready.")
            workspace.main()
        except Exception as exc:
            workspace_launching = False
            print(f"[startup] workspace launch failed: {exc}", flush=True)
            traceback.print_exc()
            hud.set_state("IDLE", "Workspace startup failed.")

    def activate_workspace(source):
        nonlocal workspace_launching
        with workspace_launch_lock:
            if workspace_launched or workspace_launching:
                return
            workspace_launching = True
        stream = clap_stream["value"]
        if stream:
            try:
                stream.stop()
                stream.close()
            except Exception:
                pass
        print(f"[SYSTEM] Workspace activation: {source}", flush=True)
        speak("Launching your workspace now, Vinn!", hud=hud, wait=True)
        thread = threading.Thread(target=launch_workspace, daemon=True, name="workspace-launch")
        thread.start()

    def start_clap_listener():
        try:
            import workspace

            threshold = config.get("czulosc_klasniecia", 70)
            stream, _ = workspace.wait_for_claps(
                threshold,
                callback=lambda _event: activate_workspace("clap"),
            )
            clap_stream["value"] = stream
        except Exception as exc:
            print(f"[clap] standby listener unavailable: {exc}", flush=True)

    threading.Thread(target=start_clap_listener, daemon=True, name="standby-clap").start()

    focus = config.get("focus_guard", {})
    focus_enabled = threading.Event()
    if focus.get("enabled", True):
        focus_enabled.set()
    threading.Thread(target=focus_guard_loop, args=(stop_event, hud, speak), kwargs={
        "blacklist": focus.get("blacklist"),
        "start": config.get("work_hours", {}).get("start", "08:00"),
        "end": config.get("work_hours", {}).get("end", "17:00"),
        "interval": 30,
        "enabled_event": focus_enabled,
    }, daemon=True, name="focus-guard").start()
    threading.Thread(target=battery_guard, args=(stop_event, hud, speak, stop_event.set),
                     daemon=True, name="battery-guard").start()

    command_state = {"last_command": None, "last_command_time": 0.0}
    command_state_lock = threading.Lock()
    is_processing_command = threading.Event()
    media_cooldown_until = {"value": 0.0}

    def handle_voice_command(command, transcript):
        normalized = re.sub(r"\s+", " ", transcript.lower().strip())
        intents = {
            "play music": "play",
            "resume music": "play",
            "pause music": "pause",
            "stop music": "pause",
            "skip music": "next",
            "next song": "next",
            "skip song": "next",
            "launch workspace": "launch_workspace",
            "start work": "launch_workspace",
            "wake up": "launch_workspace",
            "lock workspace": "lock",
            "lock screen": "lock",
            "sleep": "lock",
            "status report": "status",
            "system status": "status",
            "check system": "status",
            "exit launcher": "exit",
            "kill launcher": "exit",
            "shutdown": "exit",
        }
        matched_command = next(
            (
                intent
                for phrase, intent in intents.items()
                if re.search(rf"\b{re.escape(phrase)}\b", normalized)
            ),
            None,
        )

        if not matched_command:
            hud.set_state("IDLE")
            return

        now = time.monotonic()
        with command_state_lock:
            if is_processing_command.is_set():
                return
            if matched_command in {"play", "pause", "next"} and now < media_cooldown_until["value"]:
                return
            if (
                matched_command == command_state["last_command"]
                and now - command_state["last_command_time"] < 3.0
            ):
                return
            is_processing_command.set()
            command_state["last_command"] = matched_command
            command_state["last_command_time"] = now
            if matched_command in {"play", "pause", "next"}:
                media_cooldown_until["value"] = now + 2.5

        hud.set_state("WORKING", transcript, 3)
        try:
            if matched_command == "status":
                print("[EXECUTE] System Status", flush=True)
                speak(system_status_message(), hud=hud, wait=True)
            elif matched_command == "focus_enable":
                focus_enabled.set()
                print("[EXECUTE] Enable Focus Guard", flush=True)
            elif matched_command == "focus_disable":
                focus_enabled.clear()
                print("[EXECUTE] Disable Focus Guard", flush=True)
            elif matched_command == "launch_workspace":
                activate_workspace("voice")
            elif matched_command == "pause":
                print("[EXECUTE] Pause Music", flush=True)
                execute_native_media_command("pause")
                speak(random.choice(MEDIA_RESPONSES), hud=hud, wait=True)
                return
            elif matched_command in {"play", "next"}:
                print(f"[EXECUTE] {matched_command.title()} Music", flush=True)
                execute_native_media_command(matched_command)
                speak(random.choice(MEDIA_RESPONSES), hud=hud, wait=True)
                return
            elif matched_command == "lock":
                print("[EXECUTE] Lock Workspace", flush=True)
                success = execute_voice_command(matched_command)
                if success:
                    speak(random.choice(LOCK_RESPONSES), hud=hud, wait=True)
            else:
                print("[SYSTEM] Shutting down launcher", flush=True)
                speak(random.choice(EXIT_RESPONSES), hud=hud, wait=True)
                stop_event.set()
                is_processing_command.clear()

                def finish_shutdown():
                    hud.root.destroy()
                    sys.exit(0)

                hud.root.after(0, finish_shutdown)
                return
            stop_event.wait(0.5)
        finally:
            is_processing_command.clear()
            if matched_command != "exit":
                hud.set_state("IDLE")

    def listen_for_voice_commands():
        try:
            voice_command_loop(
                stop_event,
                handle_voice_command,
                language="en-US",
                energy_threshold=1000,
                dynamic_energy_threshold=False,
                processing_event=is_processing_command,
            )
        except Exception as exc:
            print(f"[voice] background listener failed: {exc}", flush=True)
            traceback.print_exc()

    print("[SYSTEM] Voice command listener active.", flush=True)
    threading.Thread(target=listen_for_voice_commands, daemon=True, name="voice-control").start()

    try:
        hud.run()
    except Exception as exc:
        print(f"[hud] main loop failed: {exc}", flush=True)
        traceback.print_exc()
    finally:
        stop_event.set()
        hud.shutdown()


if __name__ == "__main__":
    main()
