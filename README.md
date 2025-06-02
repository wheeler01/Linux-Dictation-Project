# Linux-Dictation-Project
expands the boundaries of speech recognition technology for documentation productivity on the Linux PC. With dictation and transcription capabilities as well as control over your system written in Python using whisper.

# Linux Voice Dictation and Command Mode (Enhanced)

This project enables voice-based dictation and command control on Linux using Whisper, xdotool, and a system tray interface.

## ✅ Features

- **Dictation Mode**: Transcribes speech to text with Whisper and types it in any window.
- **Command Mode**:
  - Launch or kill applications by voice
  - Navigate, delete, or select text
  - Control mouse cursor, click, and adjust sensitivity
  - Press keys and combinations (e.g., `control a`, `alt f4`)
  - Say `"select word"`, `"select 5 characters"`, `"copy"`, `"paste"`, `"hold control"`, `"release"` etc.
- **System Tray**: Shows listening state and toggles modes via click

## 📦 Dependencies

### Fedora
```bash
sudo dnf install python3-pip portaudio-devel python3-devel libXtst xdotool PyQt5
pip install whisper sounddevice scipy numpy psutil
```

### Debian/Ubuntu
```bash
sudo apt install python3-pip portaudio19-dev python3-dev xdotool libxtst-dev python3-pyqt5
pip install whisper sounddevice scipy numpy psutil
```

## ⚙️ Systemd Startup Service

To enable on login:

### `~/.config/systemd/user/voice-dictation.service`
```ini
[Unit]
Description=Voice Dictation Service

[Service]
ExecStart=/usr/bin/python3 /path/to/whisper_dictate.py
Restart=on-failure

[Install]
WantedBy=default.target
```

Update `/path/to/whisper_dictate.py` to your script’s full path.

Then:
```bash
systemctl --user daemon-reexec
systemctl --user enable --now voice-dictation.service
```

## 🎙 Usage

- Start script or login with systemd enabled
- Say `"command mode"` to enter control mode
- Say commands like:
  - `"select word"`, `"select 5 words"`, `"hold shift"`, `"release"`
  - `"copy"`, `"paste"`, `"delete 3"`, `"control c"`
- Say `"dictation mode"` to return to typing

## ♿ Accessibility

Ideal for individuals with limited mobility needing voice-based system interaction.
