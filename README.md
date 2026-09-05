# Activoice

> **Smart Voice & Gesture Workspace Launcher for Windows**  
> Buka seluruh lingkungan kerja, aplikasi, dan terminal secara otomatis ke monitor pilihan hanya lewat tepuk tangan, perintah suara, atau shortcut.

---

## Highlights

- **Multi-Profile System** - Buat beberapa profil workspace seperti _Dev_, _Gaming_, atau _Streaming_, lalu ganti profil dengan fleksibel.
- **Neural Sound Detection** - PANNs CNN14 mengenali tepukan tangan, petikan jari, siulan, dan suara pemicu lain.
- **Offline Voice Command** - Jalankan perintah suara secara offline menggunakan Vosk tanpa mengirim audio ke cloud.
- **Window & Monitor Management** - Atur posisi aplikasi ke monitor tertentu, split screen kiri/kanan, dan shortcut khusus untuk aplikasi seperti Arc Browser dan Spotify.
- **Smart App Handling** - Periksa aplikasi yang sudah berjalan agar tidak selalu membuka instance baru dan dapat memosisikan ulang window.
- **Clean Terminal Auto-Shutdown** - Proses launcher keluar setelah seluruh batch workspace selesai diluncurkan.

## Persyaratan Sistem

- **OS:** Windows 10/11 64-bit
- **Python:** 3.10 atau lebih baru
- **Hardware:** Mikrofon aktif untuk pemicu suara
- **Dependensi:** Lihat [requirements.txt](requirements.txt)

## Instalasi dan Penggunaan

### Menjalankan dari Source Code

1. Clone repository:

   ```bash
   git clone https://github.com/StarVinn/ActiVoice.git
   cd ActiVoice
   ```

2. Install dependensi:

   ```bash
   python -m pip install -r requirements.txt
   ```

3. Buka GUI konfigurasi:

   ```bash
   python config_gui.py
   ```

4. Jalankan launcher:

   ```bash
   python workspace.py
   ```

### Membuat Executable

Jalankan `build.bat` untuk membuat executable standalone menggunakan PyInstaller:

```bat
build.bat
```

Output build berada di folder `dist/`:

- `WorkspaceLauncher.exe` - Launcher utama dengan tray, deteksi suara, dan voice trigger.
- `workspace-config.json` - Konfigurasi aktif yang disalin di samping executable.

## Struktur Konfigurasi

Konfigurasi aktif berada di `workspace-config.json`. Gunakan [workspace-config.example.json](workspace-config.example.json) sebagai template:

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
      ],
      "terminale": []
    }
  }
}
```

Field penting untuk aplikasi:

- `nazwa` - nama aplikasi dan identitas untuk handler khusus seperti Spotify atau Arc.
- `exe` - executable atau command yang akan dijalankan.
- `argumenty` - URL, URI, folder proyek, atau argumen aplikasi.
- `ekran` - nomor monitor tujuan, mulai dari `1`.
- `polowa` - `left`/`lewa` atau `right`/`prawa` untuk split screen.
- `kolejnosc` - nilai lebih besar dari `0` diproses berurutan sebelum aplikasi lain.

## Metode Trigger

| Metode        | Pemicu default               | Keterangan                                          |
| ------------- | ---------------------------- | --------------------------------------------------- |
| Double clap   | Tepuk tangan 2 kali          | Diverifikasi oleh PANNs CNN14.                      |
| Hotkey        | `Win + Shift + W`            | Shortcut keyboard global.                           |
| Voice command | `launch` atau keyword profil | Pengenalan suara offline melalui Vosk.              |
| System tray   | Klik kanan ikon tray         | Jalankan profil atau tutup workspace secara manual. |

## Struktur Projek

```text
ActiVoice/
├── workspace.py                  # Launcher utama, tray, audio, voice, dan automation
├── config_gui.py                 # GUI editor konfigurasi
├── clap-trigger.py               # Listener tepukan standalone
├── voice-trigger.py              # Listener suara standalone
├── workspace-config.json         # Konfigurasi aktif
├── workspace-config.example.json # Template konfigurasi
├── build.bat                     # Script build executable
├── requirements.txt              # Dependensi Python
└── README.md                     # Dokumentasi proyek
```

## Catatan Penggunaan

Handler Spotify dan Arc menggunakan jeda, aktivasi window, klik mouse, dan shortcut keyboard karena setiap aplikasi Windows memiliki waktu startup dan perilaku session restore yang berbeda. Sesuaikan nilai `time.sleep`, title window, dan urutan shortcut bila konfigurasi digunakan pada mesin atau aplikasi lain.

Launcher menggunakan `os._exit(0)` setelah seluruh batch launching selesai. Karena pemanggilan ini menghentikan proses Python secara langsung, gunakan konfigurasi dengan hati-hati jika launcher perlu tetap berjalan di system tray setelah aplikasi dibuka.

## Credits

- **Core Framework / System Creator:** [MateuszMlynekHub](https://github.com/MateuszMlynekHub)
- **Upgraded & Customized By:** [StarVinn](https://github.com/StarVinn)
