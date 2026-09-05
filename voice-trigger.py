"""
Voice Trigger - launches workspace-launcher on voice command.
Listens in the background and reacts to selected keywords.

Installation:
    pip install SpeechRecognition pyaudio

If pyaudio doesn't install on Windows:
    pip install pipwin
    pipwin install pyaudio

Usage:
    python voice-trigger.py

Say: "uruchom workspace" or "start praca" etc.
"""

import subprocess
import sys
import os
import json

try:
    import speech_recognition as sr
except ImportError:
    print("Missing speech_recognition library!")
    print("Install: pip install SpeechRecognition pyaudio")
    sys.exit(1)

# Path to PowerShell script
LAUNCHER_SCRIPT = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "workspace-launcher.ps1"
)

CONFIG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "workspace-config.json")

# Speech recognition language (pl-PL = Polish, en-US = English)
LANGUAGE = "pl-PL"

FALLBACK_COMMANDS = {
    "uruchom workspace": "default",
    "start workspace": "default",
    "workspace domyslny": "default",
    "uruchom prace": "praca",
    "start praca": "praca",
    "workspace praca": "praca",
}


def load_config() -> dict:
    try:
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def build_voice_commands(cfg: dict) -> dict:
    commands = {}
    profiles = cfg.get("profile", {})
    if isinstance(profiles, dict) and profiles:
        for profile_name, profile_data in profiles.items():
            if not isinstance(profile_data, dict):
                continue
            keywords = profile_data.get("slowa_kluczowe", "")
            for keyword in keywords.split(","):
                cleaned = keyword.strip().lower()
                if cleaned:
                    commands[cleaned] = profile_name
    if commands:
        return commands

    active = cfg.get("profil_aktywny", "")
    keywords = cfg.get("slowa_kluczowe", "")
    for keyword in keywords.split(","):
        cleaned = keyword.strip().lower()
        if cleaned and active:
            commands[cleaned] = active
    return commands or FALLBACK_COMMANDS


def launch_workspace(profile: str):
    """Launch PowerShell script with the given profile."""
    print(f"\n>>> Launching workspace with profile: {profile}")
    cmd = [
        "powershell.exe",
        "-ExecutionPolicy", "Bypass",
        "-File", LAUNCHER_SCRIPT,
        "-Profile", profile
    ]
    subprocess.Popen(cmd)


def find_command(text: str, voice_commands: dict) -> str | None:
    """Check if spoken words match any command."""
    text_lower = text.lower().strip()
    for trigger, profile in voice_commands.items():
        if trigger in text_lower:
            return profile
    return None


def main():
    cfg = load_config()
    voice_commands = build_voice_commands(cfg)

    recognizer = sr.Recognizer()

    # Adjust sensitivity to ambient noise
    recognizer.energy_threshold = 300
    recognizer.dynamic_energy_threshold = True
    recognizer.pause_threshold = 0.8

    try:
        mic = sr.Microphone()
    except (OSError, AttributeError):
        print("Microphone not found! Check if microphone is connected.")
        print("If pyaudio is not installed: pip install pyaudio")
        sys.exit(1)

    print("=" * 50)
    print("  Voice Trigger - Workspace Launcher")
    print("=" * 50)
    print(f"Language: {LANGUAGE}")
    print(f"Script: {LAUNCHER_SCRIPT}")
    print()
    print("Available voice commands:")
    for cmd, profile in voice_commands.items():
        print(f"  '{cmd}' -> profile: {profile}")
    print()

    # Microphone calibration
    print("Calibrating microphone (silence for 2 seconds)...")
    with mic as source:
        recognizer.adjust_for_ambient_noise(source, duration=2)
    print(f"Energy threshold: {recognizer.energy_threshold:.0f}")
    print()
    print("Listening... (Ctrl+C to stop)")
    print("-" * 50)

    def callback(recognizer, audio):
        """Called when speech is detected."""
        try:
            # Use Google Speech Recognition (free, no API key needed)
            text = recognizer.recognize_google(audio, language=LANGUAGE)
            print(f"Heard: '{text}'")

            profile = find_command(text, voice_commands)
            if profile:
                launch_workspace(profile)
            else:
                print("  (no matching command)")

        except sr.UnknownValueError:
            # Speech not recognized - normal, don't log
            pass
        except sr.RequestError as e:
            print(f"Speech recognition API error: {e}")

    # Listen in background
    stop_listening = recognizer.listen_in_background(mic, callback, phrase_time_limit=5)

    try:
        import time
        while True:
            time.sleep(0.5)
    except KeyboardInterrupt:
        print("\nStopping listener...")
        stop_listening(wait_for_stop=True)
        print("Done.")


if __name__ == "__main__":
    main()
