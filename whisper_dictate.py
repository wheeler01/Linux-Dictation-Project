#!/usr/bin/env python3

import whisper
import sounddevice as sd
import numpy as np
import tempfile
import os
import subprocess
import scipy.io.wavfile
import re
import threading
import signal
from PyQt5 import QtWidgets, QtGui, QtCore
import psutil
import sys
import logging

log_path = os.path.expanduser("~/.local/share/whisper-dictation.log")
os.makedirs(os.path.dirname(log_path), exist_ok=True)
logging.basicConfig(filename=log_path, level=logging.INFO, format="%(asctime)s %(message)s")

try:
    import torch
    use_fp16 = torch.cuda.is_available() and torch.cuda.get_device_capability(0)[0] >= 7
    torch.set_num_threads(1)
except Exception:
    use_fp16 = False

model_size = "base"
logging.info("Loading Whisper model...")
model = whisper.load_model(model_size)
logging.info(f"Whisper model loaded: {model_size} | FP16 Supported: {use_fp16}")

sample_rate = 16000
duration = 3
MOUSE_SPEED = 50
mode = "dictation"
listening = False
state_lock = threading.Lock()
click_in_progress = False

REPLACEMENTS = {
    r"\bcomma\b": ",",
    r"\bperiod\b": ".",
    r"\bquestion mark\b": "?",
    r"\bexclamation mark\b": "!",
    r"\bnew paragraph\b": "\n\n",
    r"\bnew line\b": "\n",
}

def record_audio():
    try:
        logging.info("Recording audio...")
        audio = sd.rec(int(duration * sample_rate), samplerate=sample_rate, channels=1, dtype='float32')
        sd.wait()
        logging.info("Audio recorded successfully.")
        return np.squeeze(audio)
    except Exception as e:
        logging.error(f"Audio recording failed: {e}")
        return np.zeros(sample_rate * duration)

def save_audio_to_wav(audio_data, filename):
    scipy.io.wavfile.write(filename, sample_rate, audio_data)

def apply_replacements(text):
    global mode, listening
    command = re.sub(r'[^\w\s]', '', text.lower().strip())
    logging.info(f"Normalized command: {command}")

    if command == "command mode":
        mode = "command"
        logging.info("Switched to command mode")
        QtCore.QMetaObject.invokeMethod(overlay, lambda: overlay.update_text(), QtCore.Qt.QueuedConnection)
        return ""
    elif command == "dictation mode":
        mode = "dictation"
        logging.info("Switched to dictation mode")
        QtCore.QMetaObject.invokeMethod(overlay, lambda: overlay.update_text(), QtCore.Qt.QueuedConnection)
        return ""
    elif command in ["stop listening", "go to sleep"]:
        listening = False
        logging.info("Listening paused")
        QtCore.QMetaObject.invokeMethod(overlay, lambda: overlay.update_text(), QtCore.Qt.QueuedConnection)
        return ""
    elif "wake up" in command or "start listening" in command:
        logging.info("Wake command matched inside apply_replacements")
        listening = True
        QtCore.QMetaObject.invokeMethod(overlay, lambda: overlay.update_text(), QtCore.Qt.QueuedConnection)
        logging.info("Listening state set to True")
        return ""

    if not listening:
        return ""

    for pattern, replacement in REPLACEMENTS.items():
        text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)

    if text:
        text = text[0].upper() + text[1:]
    return text.strip()

def type_text(text):
    try:
        if text.startswith("KEY_"):
            subprocess.run(["xdotool", "key", text[4:]])
        elif text == "BACKSPACE":
            subprocess.run(["xdotool", "key", "BackSpace"])
        elif text == "DELETE_WORD":
            subprocess.run(["xdotool", "key", "ctrl+BackSpace"])
        elif text == "CLEAR_LINE":
            subprocess.run(["xdotool", "key", "Home"])
            subprocess.run(["xdotool", "key", "Shift+End"])
            subprocess.run(["xdotool", "key", "BackSpace"])
        else:
            subprocess.run(["xdotool", "type", "--delay", "50", text])
        logging.info(f"Typed: {text}")
    except Exception as e:
        logging.error(f"Error typing text: {e}")

def dictation_loop():
    try:
        while True:
            QtCore.QMetaObject.invokeMethod(overlay, lambda: overlay.set_state("listening"), QtCore.Qt.QueuedConnection)
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmpfile:
                audio = record_audio()
                save_audio_to_wav(audio, tmpfile.name)
                QtCore.QMetaObject.invokeMethod(overlay, lambda: overlay.set_state("processing"), QtCore.Qt.QueuedConnection)
                logging.info(f"Transcribing {tmpfile.name}...")
                result = model.transcribe(tmpfile.name, language='en', fp16=use_fp16, vad_filter=False)
                text = result["text"].strip()
                os.remove(tmpfile.name)

            if not text:
                logging.info("Empty transcript, skipping.")
                QtCore.QMetaObject.invokeMethod(overlay, lambda: overlay.set_state("idle"), QtCore.Qt.QueuedConnection)
                continue

            logging.info(f"Transcript: {text}")
            processed = apply_replacements(text)
            if processed or listening:
                type_text(processed)
            QtCore.QMetaObject.invokeMethod(overlay, lambda: overlay.set_state("idle"), QtCore.Qt.QueuedConnection)
    except Exception as e:
        logging.error(f"Dictation loop error: {e}")

class OverlayWidget(QtWidgets.QWidget):
    def __init__(self):
        super().__init__()
        self.fp32 = self.detect_fp32()
        self.setWindowFlags(QtCore.Qt.WindowStaysOnTopHint | QtCore.Qt.FramelessWindowHint)
        self.setGeometry(100, 100, 240, 60)
        self.label = QtWidgets.QLabel(self)
        self.label.setAlignment(QtCore.Qt.AlignCenter)
        self.label.setGeometry(0, 0, 240, 60)
        self.offset = None
        self.mousePressEvent = self.click_handler
        self.mouseMoveEvent = self.move_handler
        self._last_state = None
        self.set_state("idle")

    def detect_fp32(self):
        try:
            import torch
            return not torch.cuda.is_available() or torch.cuda.get_device_capability(0)[0] < 7
        except Exception:
            return True

    def set_state(self, state):
        if getattr(self, "_last_state", None) == state:
            return
        self._last_state = state
        try:
            color_map = {
                "idle": "#8B0000",
                "listening": "#006400",
                "processing": "#DAA520"
            }
            bg_color = color_map.get(state, "#333")
            badge = "\n32" if self.fp32 else ""
            self.label.setText(f"Mode: {mode.title()}{badge}\n{'🎙️ Listening' if listening else '😴 Asleep'}")
            self.setStyleSheet(f"background-color: {bg_color}; color: white; font-size: 16px; padding: 10px; border: 2px solid #555; border-radius: 10px;")
        except Exception as e:
            logging.error(f"Error setting widget state: {e}")

    def update_text(self):
        self.set_state("idle")

    def click_handler(self, event):
        global mode
        if event.button() == QtCore.Qt.LeftButton:
            mode = "command" if mode == "dictation" else "dictation"
            QtCore.QTimer.singleShot(0, self.update_text)
            logging.info(f"Widget toggled mode to {mode}")
            self.offset = event.pos()

    def move_handler(self, event):
        if self.offset is not None and event.buttons() == QtCore.Qt.LeftButton:
            self.move(self.pos() + event.pos() - self.offset)

def main():
    global overlay
    app = QtWidgets.QApplication(sys.argv)
    overlay = OverlayWidget()
    overlay.show()
    logging.info("Floating widget displayed")
    threading.Thread(target=dictation_loop, daemon=True).start()
    signal.signal(signal.SIGINT, signal.SIG_DFL)
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()
