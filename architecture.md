# ActiVoice Architecture

This document records the repository state before the Configuration GUI refactor. It distinguishes existing behavior from the proposed design so the implementation can be reviewed before code changes begin.

## 1. Directory Tree and Responsibilities

```text
launcher/
|-- main.py                         Grace runtime entry point, HUD, voice commands, guards
|-- config_gui.py                   CustomTkinter configuration editor and JSON persistence
|-- workspace.py                    Main workspace launcher, audio detection, tray, window placement
|-- overlay_hud.py                  PyQt6 Grace HUD and state/avatar rendering
|-- voice_engine.py                 Async Edge TTS playback through pygame
|-- sys_control.py                  Windows lock, Spotify/media controls, voice command loop, battery guard
|-- focus_guard.py                  Time-windowed blocked-window detection and termination
|-- gemini_engine.py                Gemini REST client for push-to-talk conversations
|-- global_hotkey.py                Ctrl+Alt push-to-talk registration
|-- clap-trigger.py                 Standalone simple double-clap launcher
|-- voice-trigger.py                Standalone Google Speech Recognition launcher
|-- workspace-launcher.ps1          Legacy PowerShell workspace launcher/window placement path
|-- workspace-hotkey.ahk             Optional AutoHotkey profile shortcuts
|-- clap-trigger-startup.bat        Standalone clap listener startup wrapper
|-- create-shortcut.vbs             Creates a startup shortcut for the built launcher
|-- create-startup-shortcut.ps1     Creates a startup shortcut for standalone clap trigger
|-- build.bat                       PyInstaller build for workspace.py
|-- requirements.txt                Python dependency list
|-- workspace-config.json            Active JSON configuration (user-specific)
|-- workspace-config.example.json    Example JSON configuration
|-- .env.example                    GEMINI_API_KEY template
|-- assets/                         HUD images and tray image
|   |-- grace_idle.png
|   |-- grace_working.png
|   |-- grace_thinking.png
|   |-- grace_shutdown.png
|   |-- grace_angry.png
|   |-- grace_sad.png
|   |-- grace_sleep.png
|   |-- grace_drag.png
|   |-- grace_tired.png
|   `-- tray_icon.png
`-- .vscode/, .git/                 Editor and version-control metadata
```

### Runtime modules

- `config_gui.py` loads `workspace-config.json`, normalizes old flat configs into a profile shape, edits Apps, Terminals, and Settings, and writes JSON. It currently has three tabs in this order: Apps, Terminals, Settings.
- `workspace.py` is the tray-oriented launcher. It reads global trigger settings and the active profile, starts clap detection, registers the configured Win32 hotkey, optionally starts Vosk keyword detection, launches apps/terminals, and positions windows with Win32 APIs.
- `main.py` is the Grace/ActiVoice orchestrator. It starts the HUD, standby clap activation, voice command listener, focus guard, mode scheduler, battery guard, Gemini push-to-talk, and workspace launch thread. It also contains many English response strings and the shutdown confirmation flow.
- `overlay_hud.py` owns the PyQt6 HUD. `ASSET_NAMES` maps nine runtime states to fixed files under `assets/`; missing files currently fall back to the IDLE image.
- `voice_engine.py` owns asynchronous Edge TTS generation and pygame playback. The voice (`en-US-MichelleNeural`), rate (`-5%`), and pitch (`+18Hz`) are currently hardcoded.
- `sys_control.py` owns Windows workstation locking, Spotify/media fallback controls, Google Speech Recognition command capture, and low-battery shutdown scheduling.
- `focus_guard.py` checks the Jakarta timezone against one global `work_hours` interval, scans visible window titles, and can terminate matching processes.
- `gemini_engine.py` reads `GEMINI_API_KEY` from `.env` and calls the pinned Gemini model. Its system prompt and language are fixed in code.
- `global_hotkey.py` wraps the `keyboard` package for the Ctrl+Alt Gemini push-to-talk trigger.

### Alternate/legacy launch paths

- `clap-trigger.py` is a simple standalone sound listener. It does not use the JSON GUI settings except for its command-line profile argument and launches `workspace-launcher.ps1`.
- `voice-trigger.py` is a standalone Google Speech Recognition listener. It builds keyword-to-profile mappings from profile `slowa_kluczowe`, with a legacy flat-key fallback.
- `workspace-launcher.ps1` is an older PowerShell implementation with a different expected `profiles` property name and should not become the owner of new Configuration data unless explicitly migrated.
- `workspace-hotkey.ahk`, `clap-trigger-startup.bat`, `create-shortcut.vbs`, and `create-startup-shortcut.ps1` are optional startup/shortcut wrappers.
- `build.bat` builds `workspace.py` as `WorkspaceLauncher.exe`; the GUI and `main.py` are not included by this build command.

## 2. Dependencies and External Integrations

From `requirements.txt`:

- Audio and detection: `numpy`, `sounddevice`, `panns-inference`, `vosk`.
- GUI and media: `customtkinter`, `PyQt6`, `Pillow`, `pygame`, `pystray`.
- Windows automation: `keyboard`, `pyautogui`, `pygetwindow`, `pywin32`, plus Win32 APIs via `ctypes`.
- Voice/TTS: `SpeechRecognition`, `edge-tts`.
- System diagnostics: `psutil`.
- Configuration/secrets: `python-dotenv`.

The proposed voice selector depends on the installed `edge-tts` CLI or equivalent package support. The asynchronous voice list operation must be optional and failure-tolerant because the current runtime can still use its fixed voice when the cache is unavailable. Timezone selection can use the standard-library `zoneinfo`; the current code already uses `ZoneInfo("Asia/Jakarta")` and does not currently require `pytz`.

## 3. Current Execution Data Flow

### Configuration and workspace launch

```text
config_gui.py
    | read/merge/write
    v
workspace-config.json
    |
    +--> workspace.py --> clap/audio stream --> launch_profile()
    |                     hotkey ----------------^
    |                     Vosk keywords ---------
    |
    +--> main.py --> standby clap --> workspace.launch_profile()
                       voice commands --> media/lock/shutdown/workspace
                       mode scheduler --> focus_guard_loop()
                       battery_guard() --> shutdown callback
```

1. The GUI loads the JSON file and preserves unknown top-level keys through `merge_config` during normal saves/imports.
2. `workspace.py` reads global trigger settings and selects `profil_aktywny` from `profile`. It launches configured applications and terminals, then manages their windows and tray menu.
3. `main.py` separately loads the same JSON, computes one current mode from `work_hours`, and starts Grace services. Its standby clap callback launches the active workspace through `workspace.launch_profile` and then calls `workspace.main()`.
4. Runtime notifications call `speak()`, which starts a worker thread, synthesizes an MP3 with Edge TTS, and plays it through pygame. The HUD receives the same text and state independently.
5. The current configuration is therefore shared by file convention, not by a typed schema or central configuration service. New keys must be ignored safely by older launch paths.

### HUD and avatar flow

```text
main.py or guard/service
    -> hud.set_state(state, text, duration)
    -> Qt signal
    -> GraceHUD._set_expression()
    -> state -> asset filename -> QPixmap -> avatar label
```

The current HUD supports `WORKING`, `IDLE`, `THINKING`, `ANGRY`, `SLEEP`, `SHUTDOWN`, `DRAG`, `TIRED`, and `SAD`. The requested Configuration mapping names seven of these states. A configurable mapping should overlay the existing mapping and retain the last valid/current image when a configured path is missing, unreadable, or not a valid image.

## 4. Existing Local Configuration Map

The active file is `workspace-config.json`; values below are the current keys and consumers.

| Key                        | Current shape          | Consumers                                          | Notes                                                                                    |
| -------------------------- | ---------------------- | -------------------------------------------------- | ---------------------------------------------------------------------------------------- |
| `czulosc_klasniecia`       | number                 | `config_gui.py`, `workspace.py`, `main.py`         | Clap threshold in dB.                                                                    |
| `hotkey`                   | string                 | `config_gui.py`, `workspace.py`                    | Win32 registration string such as `Win+Shift+W`.                                         |
| `zdarzenie_dzwiekowe`      | string                 | `config_gui.py`, `workspace.py`                    | Trigger class/group.                                                                     |
| `liczba_zdarzen`           | integer                | `config_gui.py`, `workspace.py`                    | Trigger count.                                                                           |
| `cooldown`                 | number                 | `config_gui.py`, `workspace.py` and Vosk path      | Trigger cooldown.                                                                        |
| `czulosc_nn`               | number                 | `config_gui.py`, `workspace.py`                    | Neural sound threshold.                                                                  |
| `slowa_kluczowe`           | comma-separated string | GUI legacy fallback and standalone voice path      | Profile values take precedence in current code.                                          |
| `jezyk_mowy`               | `pl` or `en`           | `config_gui.py` only in current GUI                | Runtime voice recognition is explicitly English-only in `workspace.py`/`sys_control.py`. |
| `profil_aktywny`           | string                 | `config_gui.py`, `workspace.py`, `main.py`         | Active profile name.                                                                     |
| `profile`                  | object keyed by name   | GUI, `workspace.py`, standalone `voice-trigger.py` | Each profile contains `aplikacje`, `terminale`, and `slowa_kluczowe`.                    |
| `profile.<name>.aplikacje` | list                   | `config_gui.py`, `workspace.py`                    | App name, executable, arguments, monitor, split, layer, order, minimize.                 |
| `profile.<name>.terminale` | list                   | `config_gui.py`, `workspace.py`                    | Terminal type, folder, command, monitor, split, layer.                                   |
| `work_hours`               | `{start, end}`         | `main.py`, `focus_guard.py`, GUI currently         | One global Jakarta-time mode interval.                                                   |
| `focus_guard`              | `{enabled, blacklist}` | `main.py`, `focus_guard.py`, GUI currently         | One global focus policy.                                                                 |

Important compatibility facts:

- The repository uses `profile` (singular), while `workspace-launcher.ps1` expects `profiles` (plural). The new GUI should continue using the Python runtime's existing `profile` contract and should not silently rewrite unrelated legacy keys.
- Profile keyword storage is already profile-first, with top-level `slowa_kluczowe` retained as a legacy fallback.
- The active config contains user-specific Windows paths and should not be copied into example/documentation data.
- Existing response text is distributed across `main.py`, `focus_guard.py`, and `sys_control.py`; it is not currently represented in JSON.

## 5. Proposed Configuration Data Contract

The new tab should add a namespaced, optional structure while preserving all existing keys. A compatible starting shape is:

```json
{
  "configuration": {
    "display_name": "Vinn",
    "dialogs": {
      "startup": "...",
      "workspace_launch": "...",
      "lock": "...",
      "shutdown_request": "...",
      "shutdown_confirmed": "...",
      "shutdown_cancelled": "...",
      "exit": "...",
      "focus_warning": "...",
      "focus_closed": "...",
      "low_battery": "...",
      "critical_battery": "...",
      "mode_work": "...",
      "mode_relax": "..."
    },
    "avatar_states": {
      "IDLE": "assets/grace_idle.png",
      "WORKING": "assets/grace_working.png",
      "THINKING": "assets/grace_thinking.png",
      "SHUTDOWN": "assets/grace_shutdown.png",
      "ANGRY": "assets/grace_angry.png",
      "SAD": "assets/grace_sad.png",
      "TALKING": "assets/grace_idle.png"
    },
    "tts": {
      "voice": "en-US-MichelleNeural",
      "pitch": "+18Hz",
      "rate": "-5%"
    },
    "timezone": "Asia/Jakarta",
    "modes": []
  }
}
```

The exact dialog key list should be finalized against every current hardcoded response before implementation. All dialog rendering should use a safe formatter that supplies `{name}`, `{battery}`, `{cpu}`, and `{ram}`, leaves unknown placeholders harmless, and falls back to the current English default if the configured template is empty or formatting fails.

## 6. Integration Plan for the Configuration Tab

### A. GUI composition and tab order

1. Keep the current Apps and Terminals implementations intact.
2. Keep Settings limited to listener and hardware controls: clap sensitivity, keyboard shortcut, sound trigger, wake keywords, and STT language model.
3. Remove the Settings `Grace system controls` frame and its `work_start_var`, `work_end_var`, `focus_var`, and `blacklist_var` UI ownership.
4. Add a fourth tab named `Configuration` after Settings. Build it as a scrollable tab with four sections in this order: User Profile & Dialogs, Avatar & HUD Mapping, Voice & TTS Engine, and Timezone & Multi-Mode Manager.
5. Extend `build_save_data()` with only the new `configuration` namespace plus any intentionally migrated mode data. Continue using `merge_config` so unknown keys survive.

### B. Dialog ownership and fallback

1. Add a small shared configuration/response helper rather than duplicating formatting in each service.
2. Replace response literals in `main.py`, `focus_guard.py`, and the relevant battery/system paths with lookups that accept the loaded configuration and runtime metrics.
3. Keep default English, gender-neutral templates in Python as the fallback source, but never overwrite user templates on load.
4. Pass the display name and dialog provider into the existing callbacks, or load the config once at startup and provide a thread-safe immutable snapshot. Avoid reading GUI variables from worker threads.

### C. Avatar mapping

1. Extend `GraceHUD` to accept an optional state mapping and merge it with `ASSET_NAMES`.
2. Resolve relative paths from `BASE_DIR`/the asset directory and validate with `QPixmap` before changing `_current_image_path`.
3. On invalid or missing custom images, keep the current valid image or fall back to the existing state/IDLE image without raising from the Qt event loop.
4. Add `TALKING` as an alias/state mapping without breaking existing `SLEEP`, `DRAG`, or `TIRED` runtime states.

### D. Voice and TTS

1. Start a daemon worker from the GUI/application startup to execute `edge-tts --list-voices` (or the package-equivalent listing), capture success/failure, and atomically write `voices_cache.json`.
2. Load an existing cache immediately when available; use a deterministic fallback voice list when the command is unavailable.
3. Store voice, pitch, and rate under `configuration.tts`, validate numeric input, and pass the selected values through `speak()` into `edge_tts.Communicate`.
4. Keep the test button disabled while a test is playing, and use exactly `checking 1,2,3 clear` as its sample.
5. Determine the target language from the selected voice prefix. Put translation behind a small provider boundary with a no-network/no-provider fallback that speaks the original text, since no translation dependency or API is currently present.
6. Ensure TTS workers remain serialized by the existing voice lock and do not block GUI startup.

### E. Timezone and multi-mode manager

1. Populate an autocomplete selector from `zoneinfo.available_timezones()` (or `pytz` only if added deliberately). Persist an IANA name such as `Asia/Jakarta`.
2. Replace the single global `work_hours`/`focus_guard` editor with a dynamic `modes` list containing name, start, end, focus-enabled, and blocked-title values.
3. Treat blank start or end as inactive; validate complete entries as `HH:MM` before saving.
4. Update `main.py` mode scheduling and `focus_guard.py` to select the applicable mode by configured timezone and interval, including overnight ranges where needed.
5. Preserve legacy `work_hours` and `focus_guard` as a read fallback during migration, so an existing config remains operational before it is saved through the new GUI.

### F. Validation and rollout checks

- Load old flat config, current profile config, and new configuration config without exceptions.
- Verify empty dialog fields produce fallback speech instead of silence or `KeyError`.
- Verify invalid avatar files leave the HUD visible with its prior image.
- Verify voice-list failure still leaves the GUI usable and TTS playable with the default voice.
- Verify blank mode hours do not activate focus guard.
- Verify existing Apps, Terminals, trigger settings, profile keywords, export/import, and startup shortcut behavior remain unchanged.
- Run Python syntax/diagnostic checks and a headless or Windows GUI smoke test where the environment permits it.

## 7. Current Gaps to Resolve During Implementation

- `main.py` contains the newest Grace orchestration but the documented build path still packages `workspace.py`; the deployment target for the refactor must be clarified in implementation.
- The requested `TALKING` state is not currently in `overlay_hud.py` and the requested settings label "Wake Keywords" differs from the current profile keyword implementation.
- Current runtime STT uses Google Speech Recognition in some paths and Vosk in the workspace path; the GUI's language selector does not currently control either runtime consistently.
- No translation engine, voice-cache file, typed schema, or dialog-template persistence exists yet.
- `workspace-launcher.ps1` has a separate config naming contract and should be treated as legacy until explicitly migrated.
