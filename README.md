Ready Vinn! Ini versi raw Markdown (.md) murni yang tinggal kamu *copy-paste* langsung ke file `README.md` kamu:

```markdown
# Activoice

> **Smart Voice & Gesture Workspace Launcher for Windows**  
> Buka seluruh lingkungan kerja, aplikasi, dan terminal secara otomatis ke monitor pilihan hanya lewat tepuk tangan, perintah suara, atau *shortcut*.

---

## Highlights

* **Multi-Profile System** — Bikin berbagai profil workspace (misal: *Dev*, *Gaming*, *Streaming*) dan ganti profil secara fleksibel.
* **Neural Sound Detection** — AI bawaan (PANNs CNN14) yang presisi buat ngenalin tepukan tangan, petikan jari, atau siulan tanpa kepemicu suara bising sekitar.
* **Offline Voice Command** — Eksekusi perintah suara secara *offline* dan aman tanpa kirim data ke *cloud* (menggunakan Vosk).
* **Window & Monitor Management** — Bebas atur posisi window aplikasi ke Monitor 1/2, *split screen* (kiri/kanan), hingga simulasi *shortcut* khusus (misal: Arc Browser di Screen 2, Spotify auto-play).
* **Smart App Handling** — Otomatis nge-cek aplikasi yang udah kebuka biar nggak *double launch*, melainkan cuma mindahin fokus/layarnya.
* **Clean Terminal Auto-Shutdown** — Terminal pembantu bakal otomatis *force exit* bersih begitu semua aplikasi selesai diluncurkan.

---

## Persyaratan Sistem

* **OS:** Windows 10 / 11 (64-bit)
* **Python:** 3.10 atau versi lebih baru
* **Hardware:** Mikrofon aktif
* **Dependensi Python Utama:** `pyautogui`, `pygetwindow`, `customtkinter`, `pyloudnorm` / `sounddevice`

---

## Cara Instalasi & Cepat Pakai

### Mode 1: Menjalankan dari Source Code (Developer)

1. **Clone repository:**
   ```bash
   git clone [https://github.com/USERNAME/activoice.git](https://github.com/USERNAME/activoice.git)
   cd activoice

```

2. **Install dependensi:**
```bash
pip install -r requirements.txt

```


3. **Buka GUI Konfigurasi:**
```bash
python config_gui.py

```


4. **Jalankan Activoice Launcher:**
```bash
python workspace.py

```



---

### Mode 2: Compiled Executable (.exe)

Gunakan `build.bat` untuk melakukan kompilasi otomatis ke format Standalone `.exe` via PyInstaller:

```bash
build.bat

```

Hasil kompilasi ada di dalam folder `dist/`:

* `ActivoiceLauncher.exe` — Aplikasi utama (Tray & Sound/Voice Listener)
* `ActivoiceConfig.exe` — GUI Editor Konfigurasi
* `workspace-config.json` — File konfigurasi aktif

---

## Struktur Konfigurasi (`workspace-config.json`)

Contoh file konfigurasi `workspace-config.json`:

```json
{
  "czulosc_klasniecia": 70,
  "hotkey": "Win+Shift+W",
  "zdarzenie_dzwiekowe": "Clapping",
  "liczba_zdarzen": 2,
  "cooldown": 3,
  "czulosc_nn": 0.12,
  "slowa_kluczowe": "launch",
  "jezyk_mowy": "en",
  "profil_aktywny": "Work",
  "profile": {
    "Work": {
      "slowa_kluczowe": "launch, start work",
      "aplikacje": [
        {
          "nazwa": "Spotify",
          "exe": "C:\\Users\\YOUR_USER\\AppData\\Roaming\\Spotify\\Spotify.exe",
          "argumenty": "spotify:playlist:YOUR_PLAYLIST_ID",
          "ekran": 1,
          "polowa": "",
          "warstwa": "Behind",
          "kolejnosc": 0,
          "minimalizuj": false
        },
        {
          "nazwa": "Arc Browser",
          "exe": "C:\\Users\\YOUR_USER\\AppData\\Local\\Microsoft\\WindowsApps\\Arc.exe",
          "argumenty": "",
          "ekran": 2,
          "polowa": "",
          "warstwa": "Normal",
          "kolejnosc": 1,
          "minimalizuj": false
        }
      ]
    }
  }
}

```

---

## Metode Trigger

| Metode | Pemicu Default | Keterangan |
| --- | --- | --- |
| **Double Clap** | Tepuk tangan 2x | Dideteksi jaringan saraf PANNs CNN14 |
| **Hotkeys** | `Win + Shift + W` | Pintasan keyboard global |
| **Voice Command** | `"launch"` / `"start work"` | Pengenalan suara *offline* via Vosk |
| **System Tray** | Klik Kanan Icon Tray | Pilih & jalankan profil secara manual |

---

## Struktur Projek

```text
activoice/
├── workspace.py               # Main Service (Tray, AI Sound/Voice Listener, Automation Engine)
├── config_gui.py              # GUI Editor (CustomTkinter)
├── clap-trigger.py            # Standalone Clap Listener
├── voice-trigger.py           # Standalone Voice Listener
├── workspace-config.json      # File Konfigurasi Aktif
├── workspace-config.example.json # Template Contoh Konfigurasi
├── build.bat                  # Script Build Portable .exe
└── requirements.txt           # Python Dependencies List

```
---

## Catatan Penggunaan & Eksplorasi Aplikasi

> **Tips:** Racikan logika *delay*, simulasi tombol, dan *window focus* di dalam skrip saat ini disesuaikan khusus untuk karakteristik aplikasi tertentu (seperti Spotify dan Arc Browser). 
> 
> Setiap aplikasi di Windows memiliki alur *startup*, penanganan *session restore*, serta respons terhadap shortcut keyboard yang berbeda-beda. Sangat disarankan untuk mengeksplorasi dan menyesuaikan variabel penjedaan (`time.sleep`) maupun urutan perintah keyboard sesuai dengan kebutuhan aplikasi lain yang ingin kamu tambahkan ke dalam profil Activoice.

---
## Watermark & Credits

* **Core Framework / System Creator:** [MateuszMlynekHub](https://github.com/MateuszMlynekHub)
* **Upgraded & Customized By:** [StarVinn](https://github.com/StarVinn)