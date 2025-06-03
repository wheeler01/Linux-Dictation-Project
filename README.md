
# Linux Dictation Project

A voice-powered dictation and command system for Linux using OpenAI Whisper.

Created and maintained by **Andrew Mitchell**, President and Senior Network Engineer of VoIPster Communications, Inc.

---

## 🆕 Version 0.9.6 Highlights

- ✅ **Color-coded floating widget** (Green = Listening, Yellow = Processing, Red = Idle)
- ✅ **FP32 processor detection** with a small "32" badge shown on CPU-only systems
- ✅ Improved **wake command detection**
- ✅ Real-time punctuation and selection commands
- ✅ Works in headless environments using `QT_QPA_PLATFORM=offscreen`
- ✅ Logging enabled at `~/.local/share/whisper-dictation.log`

---

## 🖥️ Features

- 🎙️ Whisper-based speech-to-text transcription
- 🗣️ Two modes: Dictation Mode and Command Mode
- 🔤 Voice-activated editing: "select word", "select 3 words", "select line"
- ⌨️ Support for modifier key commands: "hold shift", "release control"
- 💬 Automatic punctuation support
- 🪟 Movable floating overlay widget

---

## 📦 Installation

### Fedora 42

```bash
sudo dnf install python3-pip xdotool portaudio-devel ffmpeg
pip3 install sounddevice numpy scipy pyqt5 openai-whisper
```

### Debian/Ubuntu

```bash
sudo apt install python3-pip xdotool portaudio19-dev ffmpeg
pip3 install sounddevice numpy scipy pyqt5 openai-whisper
```

---

## 🚀 Usage

Run the application:

```bash
python3 whisper_dictate.py
```

To run it as a background service on login:

### Create a systemd user service

Save the following to `~/.config/systemd/user/whisper-dictation.service`:

```ini
[Unit]
Description=Linux Whisper Voice Dictation
After=network.target

[Service]
ExecStart=/usr/bin/python3 /home/YOUR_USERNAME/path/to/whisper_dictate.py
Restart=always
Environment=QT_QPA_PLATFORM=offscreen

[Install]
WantedBy=default.target
```

Then enable and start the service:

```bash
systemctl --user daemon-reexec
systemctl --user enable whisper-dictation.service
systemctl --user start whisper-dictation.service
```

---

## 💡 Tips

- Click the floating widget to toggle between Dictation and Command modes.
- Say **"command mode"** or **"dictation mode"** to switch modes by voice.
- Say **"wake up"** to start listening again, or **"stop listening"** to pause.
- Use your voice to type text, move the mouse, or simulate keystrokes.

---

## 🛠 Troubleshooting

Check the log for diagnostics:

```bash
cat ~/.local/share/whisper-dictation.log
```

Ensure your microphone is working and that PulseAudio or PipeWire is correctly configured.

---

## 🔖 License

MIT License
