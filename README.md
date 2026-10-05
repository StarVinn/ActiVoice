# ActiVoice

> **Smart Voice, Gesture & Workspace Assistant for Windows**  
> Aplikasi desktop Windows yang menggabungkan workspace automation, sound trigger, voice command, Gemini push-to-talk, system control, dan Grace PyQt6 HUD dalam satu launcher.

ActiVoice dirancang sebagai **workspace assistant** yang dapat membuka dan mengatur lingkungan kerja secara otomatis melalui beberapa metode trigger, seperti tepuk tangan, global hotkey, voice keyword, system tray, serta percakapan suara dengan Gemini.

---

## ✨ Highlights

### 🖥️ Smart Workspace Launcher

- Multi-profile workspace seperti `Work`, `Dev`, `Gaming`, atau `Streaming`.
- Membuka aplikasi dan terminal secara otomatis.
- Menentukan monitor tujuan untuk setiap aplikasi.
- Mendukung split screen kiri/kanan.
- Mengatur layer, urutan startup, dan status minimize.
- Mendeteksi aplikasi yang sudah berjalan sebelum membuat instance baru.
- Mendukung handler khusus untuk aplikasi seperti Spotify dan Arc Browser.
- Windows window management menggunakan Win32 API.

### 👏 Sound & Gesture Trigger

- Double-clap detection.
- Neural sound detection menggunakan `panns-inference`.
- Configurable clap sensitivity.
- Configurable sound event.
- Cooldown untuk mencegah trigger berulang.
- Standalone clap listener tersedia melalui `clap-trigger.py`.

### 🎙️ Voice Command

ActiVoice memiliki beberapa jalur voice interaction:

- Workspace keyword detection menggunakan Vosk.
- Standalone voice trigger.
- Gemini push-to-talk conversation.
- Global `Ctrl + Alt` push-to-talk untuk Gemini.
- Runtime voice interaction menggunakan bahasa Inggris.

> **Catatan:** Jalur workspace menggunakan Vosk, sementara beberapa jalur legacy/standalone masih menggunakan Google Speech Recognition. Keduanya belum sepenuhnya disatukan menjadi satu STT provider.

### 🤖 Grace Gemini Assistant

Grace merupakan assistant layer yang berjalan di atas ActiVoice.

- Gemini REST client.
- Model Gemini yang dipin.
- Push-to-talk menggunakan `Ctrl + Alt`.
- English voice interaction.
- Edge TTS.
- PyQt6 HUD.
- Avatar state system.
- Shutdown confirmation flow.
- System control dan workspace control melalui voice command.

### 🎨 Grace HUD

Grace menggunakan PyQt6 sebagai graphical HUD.

HUD memiliki beberapa runtime state:

- `IDLE`
- `WORKING`
- `THINKING`
- `ANGRY`
- `SLEEP`
- `SHUTDOWN`
- `DRAG`
- `TIRED`
- `SAD`

Setiap state dipetakan ke asset gambar yang berada di folder `assets/`. Jika asset state tidak tersedia, HUD menggunakan fallback image yang valid.

HUD juga mendukung:

- Speech bubble.
- Dynamic avatar resizing.
- Native PyQt6 `QSizeGrip`.
- Diagonal resize cursor.
- Avatar tetap berada di sisi kanan ketika speech bubble disembunyikan.
- State-based avatar rendering.

---

# 🏗️ Architecture

ActiVoice terdiri dari beberapa layer utama:

```text
                         ┌──────────────────────┐
                         │      ActiVoice       │
                         │     main.py          │
                         │  Runtime Orchestrator │
                         └──────────┬───────────┘
                                    │
              ┌─────────────────────┼─────────────────────┐
              │                     │                     │
              ▼                     ▼                     ▼
      ┌──────────────┐      ┌──────────────┐      ┌──────────────┐
      │  Grace HUD   │      │ Voice / TTS  │      │ System Ctrl  │
      │ overlay_hud  │      │ Gemini / STT  │      │ sys_control  │
      └──────────────┘      └──────────────┘      └──────────────┘
              │                     │                     │
              └─────────────────────┼─────────────────────┘
                                    │
                                    ▼
                         ┌──────────────────────┐
                         │ Workspace Launcher   │
                         │    workspace.py      │
                         └──────────┬───────────┘
                                    │
                    ┌───────────────┼───────────────┐
                    ▼               ▼               ▼
                 Apps           Terminals       Window Manager
```

`main.py` bertindak sebagai orchestrator utama untuk Grace, HUD, standby clap activation, voice command, focus guard, battery guard, Gemini push-to-talk, dan workspace launch thread. Sementara `workspace.py` menangani workspace launcher, tray, audio trigger, hotkey, Vosk, aplikasi, terminal, dan window placement.

---

# 📁 Project Structure

```text
ActiVoice/
│
├── main.py
│   └── Grace runtime entry point
│       - HUD
│       - Voice commands
│       - Guards
│       - Gemini PTT
│       - Workspace orchestration
│
├── config_gui.py
│   └── Configuration editor
│       - Apps
│       - Terminals
│       - Settings
│       - JSON persistence
│
├── workspace.py
│   └── Main workspace launcher
│       - Audio detection
│       - Tray
│       - Hotkey
│       - Vosk keyword detection
│       - App launching
│       - Terminal launching
│       - Window placement
│
├── overlay_hud.py
│   └── PyQt6 Grace HUD
│       - Avatar rendering
│       - Speech bubble
│       - Runtime states
│       - HUD resizing
│
├── voice_engine.py
│   └── Edge TTS engine
│       - Async speech generation
│       - pygame playback
│       - Voice configuration
│
├── sys_control.py
│   └── Windows/system controls
│       - Lock workstation
│       - Spotify/media controls
│       - Voice command loop
│       - Battery guard
│
├── focus_guard.py
│   └── Focus protection
│       - Work-hour detection
│       - Blocked window detection
│       - Process termination
│
├── gemini_engine.py
│   └── Gemini REST client
│       - API authentication
│       - Gemini requests
│       - Push-to-talk conversations
│
├── global_hotkey.py
│   └── Global Ctrl+Alt registration
│
├── clap-trigger.py
│   └── Standalone clap listener
│
├── voice-trigger.py
│   └── Standalone voice trigger
│
├── workspace-launcher.ps1
│   └── Legacy PowerShell launcher
│
├── workspace-hotkey.ahk
│   └── Optional AutoHotkey shortcuts
│
├── clap-trigger-startup.bat
│   └── Startup wrapper
│
├── create-shortcut.vbs
│   └── Startup shortcut creator
│
├── create-startup-shortcut.ps1
│   └── Standalone clap startup shortcut
│
├── build.bat
│   └── PyInstaller build script
│
├── requirements.txt
│   └── Python dependencies
│
├── workspace-config.json
│   └── Active user configuration
│
├── workspace-config.example.json
│   └── Configuration template
│
├── .env.example
│   └── Gemini API key template
│
├── assets/
│   ├── grace_idle.png
│   ├── grace_working.png
│   ├── grace_thinking.png
│   ├── grace_shutdown.png
│   ├── grace_angry.png
│   ├── grace_sad.png
│   ├── grace_sleep.png
│   ├── grace_drag.png
│   ├── grace_tired.png
│   └── tray_icon.png
│
└── README.md
```

Struktur aktual proyek membagi tanggung jawab antara runtime orchestrator, workspace launcher, HUD, TTS, system control, focus guard, dan Gemini engine.

---

# ⚙️ Requirements

### Operating System

- Windows 10/11 64-bit

### Python

- Python 3.10+

### Hardware

- Microphone
- Speaker/headset
- Multiple monitors jika menggunakan multi-monitor workspace

### Dependencies

Dependensi utama meliputi:

```text
numpy
sounddevice
panns-inference
vosk

customtkinter
PyQt6
Pillow
pygame
pystray

keyboard
pyautogui
pygetwindow
pywin32

SpeechRecognition
edge-tts
psutil
python-dotenv
```

Daftar dependency tersebut berasal dari runtime configuration dan automation layer ActiVoice.

---

# 🚀 Installation

## 1. Clone Repository

```bash
git clone https://github.com/StarVinn/ActiVoice.git
cd ActiVoice
```

## 2. Create Virtual Environment

```bash
python -m venv .venv
```

Aktifkan:

```bat
.venv\Scripts\activate
```

## 3. Install Dependencies

```bash
python -m pip install -r requirements.txt
```

## 4. Configure Gemini

Buat file:

```text
.env
```

Gunakan `.env.example` sebagai template:

```env
GEMINI_API_KEY=YOUR_GEMINI_API_KEY
```

`gemini_engine.py` membaca API key melalui environment variable `GEMINI_API_KEY`.

## 5. Configure Workspace

Jalankan:

```bash
python config_gui.py
```

Kemudian konfigurasi:

- Applications
- Terminals
- Trigger settings
- Workspace profiles
- Active profile

## 6. Run ActiVoice

Runtime utama:

```bash
python main.py
```

Workspace launcher dapat dijalankan secara terpisah:

```bash
python workspace.py
```

---

# 🎛️ Configuration

Konfigurasi workspace utama disimpan pada:

```text
workspace-config.json
```

Template tersedia pada:

```text
workspace-config.example.json
```

Struktur profile menggunakan `profile` dalam bentuk object:

```json
{
  "profil_aktywny": "Work",

  "profile": {
    "Work": {
      "slowa_kluczowe": "launch, start work",

      "aplikacje": [
        {
          "nazwa": "Spotify",
          "exe": "C:\\Path\\Spotify.exe",
          "argumenty": "",
          "ekran": 1,
          "polowa": "",
          "warstwa": "Behind",
          "kolejnosc": 0,
          "minimalizuj": false
        }
      ],

      "terminale": []
    }
  }
}
```

### Application Fields

| Field | Description |
|---|---|
| `nazwa` | Nama aplikasi dan identifier untuk handler khusus |
| `exe` | Executable atau command |
| `argumenty` | URL, URI, folder, atau application arguments |
| `ekran` | Nomor monitor tujuan |
| `polowa` | `left` / `right` atau `lewa` / `prawa` |
| `warstwa` | Window layer |
| `kolejnosc` | Urutan startup |
| `minimalizuj` | Apakah window diminimalkan |

---

# 🎯 Trigger System

| Trigger | Default | Handler |
|---|---|---|
| Double Clap | 2× clap | Neural audio detection |
| Hotkey | `Win + Shift + W` | Global keyboard listener |
| Voice Keyword | `launch` | Vosk |
| System Tray | Tray menu | Workspace launcher |
| Gemini PTT | `Ctrl + Alt` | Gemini voice interaction |

Workspace configuration menggunakan beberapa global listener settings seperti clap sensitivity, hotkey, sound event, event count, cooldown, neural threshold, dan active profile.

---

# 🤖 Gemini + Grace

## Push-to-Talk

Global Gemini push-to-talk menggunakan:

```text
Ctrl + Alt
```

Flow:

```text
Ctrl + Alt
     │
     ▼
global_hotkey.py
     │
     ▼
main.py
     │
     ▼
gemini_engine.py
     │
     ▼
Gemini API
     │
     ▼
Grace response
     │
     ├──► overlay_hud.py
     │
     └──► voice_engine.py
                 │
                 ▼
             Edge TTS
```

---

# 🔊 Voice / TTS

`voice_engine.py` bertanggung jawab terhadap:

- Edge TTS generation.
- Async speech generation.
- Audio playback melalui pygame.
- Voice locking agar playback tidak bertabrakan.

Konfigurasi voice pada runtime saat ini menggunakan:

```text
Voice : en-US-MichelleNeural
Rate  : -5%
Pitch : +18Hz
```

Konfigurasi tersebut masih merupakan konfigurasi runtime yang ditetapkan oleh implementation saat ini.

---

# 🎨 Grace HUD

Grace HUD dibangun menggunakan:

```text
PyQt6
```

State rendering mengikuti alur:

```text
main.py / service
       │
       ▼
hud.set_state(...)
       │
       ▼
Qt Signal
       │
       ▼
GraceHUD
       │
       ▼
State → Asset
       │
       ▼
QPixmap
       │
       ▼
Avatar
```



### Avatar States

```text
IDLE
WORKING
THINKING
ANGRY
SLEEP
SHUTDOWN
DRAG
TIRED
SAD
```

Asset:

```text
assets/
├── grace_idle.png
├── grace_working.png
├── grace_thinking.png
├── grace_shutdown.png
├── grace_angry.png
├── grace_sad.png
├── grace_sleep.png
├── grace_drag.png
└── grace_tired.png
```

---

# 🔐 Shutdown Confirmation

ActiVoice tidak langsung menjalankan shutdown ketika command shutdown terdeteksi.

Flow:

```text
Voice command
     │
     ▼
"shutdown"
     │
     ▼
Grace → SHUTDOWN state
     │
     ▼
Wait for confirmation
     │
     ├── Confirm → Shutdown
     │
     └── Cancel  → Return to IDLE
```

Hal ini mencegah accidental shutdown akibat salah pengenalan suara.

---

# 🛡️ Focus Guard

`focus_guard.py` menangani focus protection berdasarkan:

- Configured work hours.
- Visible window titles.
- Blocked application/window titles.
- Process termination.

Konfigurasi focus guard pada arsitektur saat ini masih berupa global `work_hours` dan `focus_guard`.

---

# 🔋 Battery Guard

ActiVoice juga memiliki battery monitoring melalui system control layer.

Flow secara umum:

```text
Battery monitoring
       │
       ├── Low battery
       │       ▼
       │   Warning
       │
       └── Critical battery
               ▼
          Shutdown callback
```

Battery/system handling berada pada `sys_control.py`.

---

# 🖥️ Workspace Launch Flow

```text
Trigger
   │
   ├── Double Clap
   ├── Hotkey
   ├── Voice Keyword
   └── System Tray
          │
          ▼
    Active Profile
          │
          ▼
    launch_profile()
          │
     ┌────┴────┐
     ▼         ▼
Applications  Terminals
     │         │
     └────┬────┘
          ▼
    Window Manager
          │
          ├── Monitor
          ├── Split
          ├── Layer
          └── Position
```

Configuration dibaca dari `workspace-config.json`, kemudian `workspace.py` memilih `profil_aktywny` dan menjalankan aplikasi serta terminal yang terdaftar pada profile tersebut.

---

# 🧩 Legacy / Alternate Components

Beberapa file merupakan jalur alternatif atau legacy dan tidak menjadi owner utama arsitektur baru.

### `clap-trigger.py`

Standalone clap listener.

Tidak menggunakan seluruh configuration GUI; hanya menggunakan profile argument tertentu dan menjalankan legacy workspace launcher.

### `voice-trigger.py`

Standalone voice listener menggunakan Google Speech Recognition.

### `workspace-launcher.ps1`

Legacy PowerShell workspace launcher.

> File ini menggunakan contract konfigurasi `profiles` (plural), sedangkan runtime Python menggunakan `profile` (singular). Karena itu, `workspace-launcher.ps1` tidak boleh dijadikan sumber utama configuration contract tanpa migrasi eksplisit.

### Optional startup utilities

```text
workspace-hotkey.ahk
clap-trigger-startup.bat
create-shortcut.vbs
create-startup-shortcut.ps1
```

---

# 🏗️ Configuration Refactor

Arsitektur ActiVoice sedang diarahkan menuju configuration namespace yang lebih terstruktur:

```json
{
  "configuration": {
    "display_name": "Vinn",

    "dialogs": {},

    "avatar_states": {},

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

Tujuannya adalah memisahkan configuration Grace dari configuration workspace yang sudah ada tanpa merusak compatibility dengan konfigurasi lama.

### Planned Configuration Sections

```text
Configuration
│
├── User Profile & Dialogs
│
├── Avatar & HUD Mapping
│
├── Voice & TTS Engine
│
└── Timezone & Multi-Mode Manager
```

Fitur-fitur ini merupakan bagian dari **configuration refactor plan**, bukan berarti seluruhnya sudah tersedia pada runtime saat ini.

---

# 🔄 Configuration Compatibility

ActiVoice mempertahankan configuration lama agar workspace yang sudah ada tetap dapat digunakan.

Konfigurasi lama masih mencakup:

```text
czulosc_klasniecia
hotkey
zdarzenie_dzwiekowe
liczba_zdarzen
cooldown
czulosc_nn
slowa_kluczowe
jezyk_mowy
profil_aktywny
profile
work_hours
focus_guard
```

Configuration GUI menggunakan pendekatan merge agar unknown keys tidak hilang ketika konfigurasi disimpan.

---

# 📦 Build

Build script saat ini menggunakan PyInstaller:

```bat
build.bat
```

Namun terdapat perbedaan penting antara runtime architecture dan deployment path saat ini.

`build.bat` masih membangun:

```text
workspace.py
        ↓
WorkspaceLauncher.exe
```

sedangkan `main.py` sekarang menjadi orchestrator utama untuk Grace/ActiVoice.

Karena itu, **deployment target perlu diselaraskan** apabila ActiVoice nantinya ingin didistribusikan sebagai satu executable utama. Ini merupakan salah satu gap arsitektur yang masih perlu diselesaikan.

---

# 🧠 Runtime Data Flow

```text
workspace-config.json
        │
        ├──────────────────────────┐
        │                          │
        ▼                          ▼
 workspace.py                   main.py
        │                          │
        │                    ┌─────┼─────┐
        │                    │     │     │
        ▼                    ▼     ▼     ▼
 Audio / Hotkey            HUD   Voice  Guards
 Vosk / Tray                │     │      │
        │                    │     │      │
        └────────────┬───────┘     │      │
                     │             │      │
                     ▼             ▼      ▼
               Workspace      Gemini   System
                 Launch       Engine   Control
```

Configuration saat ini dibagikan antar-komponen melalui file JSON, bukan melalui typed schema atau centralized configuration service. Karena itu, penambahan configuration baru harus tetap backward-compatible dengan runtime lama.

---

# ⚠️ Current Architecture Notes

Beberapa bagian masih dalam proses penyelarasan:

1. `main.py` sudah menjadi Grace/ActiVoice orchestrator, tetapi `build.bat` masih mem-package `workspace.py`.
2. STT belum sepenuhnya menggunakan satu engine; workspace menggunakan Vosk sedangkan beberapa standalone/runtime path menggunakan Google Speech Recognition.
3. Configuration GUI saat ini belum sepenuhnya menjadi centralized configuration system.
4. `TALKING` belum menjadi runtime state utama pada mapping HUD saat ini.
5. Voice selector dan voice cache masih merupakan bagian dari proposed configuration refactor.
6. Translation provider belum tersedia pada dependency saat ini.
7. `workspace-launcher.ps1` masih menggunakan configuration contract legacy.
8. `work_hours` dan `focus_guard` masih merupakan configuration global pada runtime saat ini.

Catatan ini penting agar README tidak mengklaim fitur yang sebenarnya masih berada pada tahap desain/refactor.

---

# 👤 Credits

### Core Framework / System Creator

**MateuszMlynekHub**

### Upgraded & Customized By

**StarVinn**

---

# 📄 License

See the repository license file for the applicable license and redistribution terms.