# Linux Dictation Project v1.0.0

## Description
Voice-based dictation and command execution for Linux using Whisper AI.

## Features
- 🎤 Dictation Mode: Speak text and it gets typed.
- 🖱️ Command Mode: Execute key commands like `ctrl+alt+delete`, `backspace`, etc.
- 🛌 Asleep Mode: Pauses input. Say "wake up" or "start listening" to resume.
- 🟢 Movable floating widget displays current mode and state.
- 🧠 Common voice commands like "select all", "copy", "paste" are supported.

## Usage

### Install Dependencies (Fedora/Debian)
```bash
sudo dnf install python3-pip portaudio python3-devel qt5-qtbase-devel xdotool
pip3 install whisper sounddevice numpy scipy pynput PyQt5
```

### Run Manually
```bash
python3 whisper_dictate.py
```

### Modes
- "command mode": Switch to command input
- "dictation mode": Switch to dictation
- "go to sleep" or "stop listening": Pauses recognition
- "wake up" or "start listening": Resumes recognition

### Example Commands in Command Mode
- "control c"
- "control alt delete"
- "select all"
- "copy"
- "backspace"

## Logging
Log file at: `~/.local/share/whisper-dictation.log`

## Notes
Tested with the `small` Whisper model. For better speed on low-resource systems, use `tiny` or `base`.

---

© 2025 Voipster Communications, Inc. | MIT License
