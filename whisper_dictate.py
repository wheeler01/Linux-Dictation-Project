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

logging.info("Loading Whisper model...")
model = whisper.load_model("small")
logging.info("Whisper model loaded.")

sample_rate = 16000
duration = 5
mode = "dictation"
listening = False

REPLACEMENTS = {
    r"\bcomma\b": ",",
    r"\bperiod\b": ".",
    r"\bquestion mark\b": "?",
    r"\bexclamation mark\b": "!",
    r"\bnew paragraph\b": "\n\n",
    r"\bnew line\b": "\n",
}

COMMAND_KEYWORDS = {
    "backspace": "BackSpace",
    "delete": "Delete",
    "enter": "Return",
    "escape": "Escape",
    "tab": "Tab",
    "space": "space",
    "shift": "Shift",
    "control": "Control",
    "alt": "Alt",
    "super": "Super",
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

def process_command(text):
    command = text.lower().strip()
    if command in {'select all': 'ctrl+a', 'copy': 'ctrl+c', 'paste': 'ctrl+v', 'cut': 'ctrl+x', 'undo': 'ctrl+z'}:
        combo = {'select all': 'ctrl+a', 'copy': 'ctrl+c', 'paste': 'ctrl+v', 'cut': 'ctrl+x', 'undo': 'ctrl+z'}[command]
        subprocess.run(["xdotool", "key", combo])
        logging.info(f"Executed custom mapped command: {command} -> {combo}")
        return True

    # Handle multi-key like 'control alt delete'
    key_alias = {
        'control': 'ctrl',
        'ctrl': 'ctrl',
        'alt': 'alt',
        'shift': 'shift',
        'super': 'super',
        'enter': 'Return',
        'return': 'Return',
        'tab': 'Tab',
        'escape': 'Escape',
        'backspace': 'BackSpace',
        'delete': 'Delete',
        'space': 'space'
    }

    parts = command.split()
    sequence = []
    for word in parts:
        if word in key_alias:
            sequence.append(key_alias[word])
        elif len(word) == 1 and word.isalpha():
            sequence.append(word.lower())
        else:
            sequence.append(word.lower())

    if sequence:
        joined = '+'.join(sequence)
        subprocess.run(["xdotool", "key", joined])
        logging.info(f"Executed sequence: {joined}")
        return True

    return False
    words = text.lower().split()
    keys = []
    for word in words:
        if word in COMMAND_KEYWORDS:
            keys.append(COMMAND_KEYWORDS[word])
        elif len(word) == 1 and word.isalpha():
            keys.append(word)
    if keys:
        subprocess.run(["xdotool", "key"] + keys)
        logging.info(f"Executed command keys: {keys}")
        return True
    return False

def apply_replacements(text):
    global mode, listening
    command = re.sub(r'[^\w\s]', '', text.lower().strip())
    logging.info(f"Normalized command: {command}")

    if command == "command mode":
        mode = "command"
        logging.info("Switched to command mode")
        try:
            overlay.update_text()
        except Exception as e:
            logging.error(f"Overlay update failed: {e}")
        return ""
    elif command == "dictation mode":
        mode = "dictation"
        logging.info("Switched to dictation mode")
        try:
            overlay.update_text()
        except Exception as e:
            logging.error(f"Overlay update failed: {e}")
        return ""
    elif command in ["stop listening", "go to sleep"]:
        listening = False
        logging.info("Listening paused")
        try:
            overlay.update_text()
        except Exception as e:
            logging.error(f"Overlay update failed: {e}")
        return ""

    if "wake up" in command or "start listening" in command:
        logging.info("Wake command matched inside apply_replacements")
        listening = True
        try:
            overlay.update_text()
        except Exception as e:
            logging.error(f"Overlay update failed: {e}")
        logging.info("Listening state set to True")
        return ""

    if not listening:
        return ""

    if mode == "command":
        success = process_command(command)
        return "" if success else command

    for pattern, replacement in REPLACEMENTS.items():
        text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)

    if text:
        text = text[0].upper() + text[1:]
    return text.strip()

def type_text(text):
    try:
        if text:
            subprocess.run(["xdotool", "type", "--delay", "50", text])
            logging.info(f"Typed: {text}")
    except Exception as e:
        logging.error(f"Error typing text: {e}")

def dictation_loop():
    try:
        while True:
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmpfile:
                audio = record_audio()
                save_audio_to_wav(audio, tmpfile.name)
                logging.info(f"Transcribing {tmpfile.name}...")
                result = model.transcribe(tmpfile.name, language='en')
                text = result["text"].strip()
                os.remove(tmpfile.name)

                if not text:
                    logging.info("Empty transcript, skipping.")
                    continue

                logging.info(f"Transcript: {text}")
                processed = apply_replacements(text)
                if processed and mode == "dictation":
                    type_text(processed)
    except Exception as e:
        logging.error(f"Dictation loop error: {e}")

class OverlayWidget(QtWidgets.QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowFlags(QtCore.Qt.WindowStaysOnTopHint | QtCore.Qt.FramelessWindowHint)
        self.setGeometry(100, 100, 240, 60)
        self.setStyleSheet("background-color: #222; color: white; font-size: 16px; padding: 10px; border: 2px solid #555; border-radius: 10px;")
        self.label = QtWidgets.QLabel(self)
        self.label.setAlignment(QtCore.Qt.AlignCenter)
        self.label.setGeometry(0, 0, 240, 60)
        self.update_text()
        self.offset = None
        self.mousePressEvent = self.click_handler
        self.mouseMoveEvent = self.move_handler

    def update_text(self):
        state = "🎙️ Listening" if listening else "😴 Asleep"
        self.label.setText("Mode: {}\n{}".format(mode.title(), state))

    def click_handler(self, event):
        global mode
        if event.button() == QtCore.Qt.LeftButton:
            mode = "command" if mode == "dictation" else "dictation"
            self.update_text()
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
    threading.Thread(target=dictation_loop, daemon=True).start()
    signal.signal(signal.SIGINT, signal.SIG_DFL)
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()
