"""ActiVoice entry point: Grace HUD, guards, and the existing workspace launcher."""

import json
import os
import random
import re
import threading
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
    print('  - "close grace" / "exit"       -> Shutdown Launcher & Close CMD')
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

    if battery and not battery.power_plugged and battery.percent < 45:
        print(
            f"[WARNING] Battery level is at {battery.percent:.0f}%. "
            "Launcher startup blocked to save power. Please plug in the charger.",
            flush=True,
        )
        os._exit(0)
    return False


def main():
    block_low_battery_startup()
    config = load_config()
    print_startup_menu(config)
    hud = GraceHUD()
    stop_event = threading.Event()
    mode = active_mode(config)
    hud.set_state("WORKING", f"{mode} active. Starting workspace.")
    speak(f"{mode} is active. Starting workspace.", hud=hud)

    def launch_workspace():
        """Start the existing workspace launcher without blocking Tk."""
        try:
            import workspace

            if workspace.should_skip_workspace_launch():
                message = "Low battery, skipping workspace launch to save power, Vinn!"
                print(f"[POWER] {message}", flush=True)
                hud.set_state("SLEEP", message, 8)
                speak(message, hud=hud)
                return

            workspace.launch_profile(workspace.get_active_profile(config))
            hud.set_state("IDLE", "Workspace ready.")
            workspace.main()
        except Exception as exc:
            print(f"[startup] workspace launch failed: {exc}", flush=True)
            traceback.print_exc()
            hud.set_state("IDLE", "Workspace startup failed.")

    threading.Thread(target=launch_workspace, daemon=True, name="workspace-launch").start()

    focus = config.get("focus_guard", {})
    if focus.get("enabled", True):
        threading.Thread(target=focus_guard_loop, args=(stop_event, hud, speak), kwargs={
            "blacklist": focus.get("blacklist"),
            "start": config.get("work_hours", {}).get("start", "08:00"),
            "end": config.get("work_hours", {}).get("end", "17:00"),
        }, daemon=True, name="focus-guard").start()
    threading.Thread(target=battery_guard, args=(stop_event, hud, speak, stop_event.set),
                     daemon=True, name="battery-guard").start()

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
            "lock workspace": "lock",
            "lock screen": "lock",
            "sleep": "lock",
            "exit launcher": "exit",
            "thank you grace": "exit",
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

        hud.set_state("WORKING", transcript, 3)
        try:
            if matched_command in {"play", "pause", "next"}:
                print(f"[EXECUTE] {matched_command.title()} Music", flush=True)
                execute_voice_command(matched_command)
                speak(random.choice(MEDIA_RESPONSES), hud=hud, wait=True)
            elif matched_command == "lock":
                print("[EXECUTE] Lock Workspace", flush=True)
                success = execute_voice_command(matched_command)
                if success:
                    speak(random.choice(LOCK_RESPONSES), hud=hud, wait=True)
            else:
                print("[SYSTEM] Shutting down launcher", flush=True)
                speak(random.choice(EXIT_RESPONSES), hud=hud, wait=True)
                os._exit(0)
            stop_event.wait(0.5)
        finally:
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
