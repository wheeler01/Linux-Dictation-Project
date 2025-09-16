
# Whisper Dictation v2.0.0 with Voice Commands, Mouse Control, and App Management

## Overview
This Python application allows voice-driven dictation, command execution, mouse control, and application management. It uses OpenAI Whisper for transcription and PyQt5 for the on-screen widget interface. Users can switch between dictation and command modes via voice or by clicking the widget.

---

## Features
- **Dictation Mode**: Speak and have text typed into the active application.
- **Command Mode**: Execute voice commands to control keyboard, mouse, and applications.
- **Mouse Control**: Move, click, drag, and scroll with voice commands.
- **Hold and Release Keys**: Keep keys pressed until explicitly released.
- **NATO Phonetic Spelling**: Spell words using the NATO alphabet.
- **Application Management**: Open and close apps by name.
- **On-screen Widget**: Displays current mode, listening status, and last transcript.
- **Configurable Mouse Step**: Change mouse movement distance in settings.
- **Noise Suppression**: Optional background noise filtering.
- **FP16 Toggle**: Experimental GPU acceleration toggle.

---

## Installation

### Requirements
- Python 3.8+
- Recommended OS: **Windows 11** (due to FP16 restrictions, this code has only been tested on Windows 11)
- GPU (optional, for faster transcription)

### Install Dependencies
```bash
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118  # GPU version
pip install git+https://github.com/openai/whisper.git
pip install sounddevice scipy numpy psutil pynput pyqt5
```

### Clone/Download the Script
Save the script (e.g., `whisper_dictate.py`) to your desired location.

---

## Usage

### Run the Application
```bash
python whisper_dictate.py
```

The widget will appear on your screen. You can click it to toggle between dictation and command mode.

### Modes
- **Dictation Mode**: Types everything you say.
- **Command Mode**: Listens for specific voice commands.

### Switching Modes
- Voice commands: `"command mode"`, `"dictation mode"`
- Widget click toggles mode.

---

## Built-in Voice Commands

### Listening Control
- `"wake up"` / `"start listening"` – Start processing speech.
- `"stop listening"` – Stop processing speech.

### Keyboard Commands
- `"hold <key>"` – Hold a key down.
- `"release keys"` – Release all held keys.
- `"press <key>"` – Press and release a key.
- `"select all"`, `"copy"`, `"paste"`
- `"select line <n>"` – Select `n` lines.
- `"select word <word>"` – Select a specific word.
- NATO spelling: `"alpha bravo charlie"` → `abc`.

### Mouse Commands
- `"move mouse <direction> <amount>"` – Move mouse (`left`, `right`, `up`, `down`).
- `"click"`, `"double click"`
- `"left click"`, `"right click"`, `"middle click"`
- `"scroll up"`, `"scroll down"`
- `"hold click"`, `"release click"` – For dragging.

### Application Control
- `"open <app>"` – Opens an app (`notepad`, `calculator`, etc.)
- `"close <app>"` – Closes an app.

---

## Settings
Click the ⚙️ icon on the widget to open the settings window.
- Startup listening state.
- Startup mode.
- Noise suppression toggle.
- FP16 toggle (experimental GPU optimization).
- Mouse movement step size.

Settings are saved to `~/.config/whisper-dictate/settings.json`.

---

## Notes
- Ensure your microphone is set as the default input device.
- On Linux, you may need additional permissions for microphone access.
- For GPU acceleration, ensure PyTorch is installed with CUDA support.
- Due to FP16 restrictions, **this code is only tested and confirmed functional on Windows 11**.

---

## Troubleshooting
- **No transcription**: Check microphone settings.
- **Mouse not moving**: Verify settings for mouse step size.
- **App open/close not working**: Ensure the app alias is configured in `settings.json`.

---

## License
MIT License
