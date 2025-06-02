Linux Dictation Project v0.9.4
==============================

This version includes:
- Continuous voice listening with improved wake command handling.
- Substring match for wake commands like "wake up" or "start listening".
- Forced English-only transcription to reduce misinterpretation.
- Skips empty transcripts to avoid typing blank lines.
- Optimized for lower CPU/memory consumption.

Installation Dependencies (Fedora):
----------------------------------
sudo dnf install python3-pip xdotool portaudio-devel
pip3 install sounddevice numpy scipy pyqt5 openai-whisper

Installation (Generic):
-----------------------
1. Copy `whisper_dictate.py` to ~/bin/Scripts/
2. Copy `whisper-dictation.service` to ~/.config/systemd/user/
3. Enable service with:
   systemctl --user daemon-reload
   systemctl --user enable whisper-dictation.service
   systemctl --user start whisper-dictation.service

Usage:
------
- Click the floating widget to toggle between Dictation and Command modes.
- Say "wake up" or "start listening" to activate listening.
- Say "stop listening" or "go to sleep" to pause recognition.

Commands:
---------
- In Command mode:
  - "copy", "paste", "select word", "select line", etc. (customize as needed)
- In Dictation mode:
  - Spoken words are typed in real-time, with punctuation support.

Logs:
-----
- View logs in ~/.local/share/whisper-dictation.log
