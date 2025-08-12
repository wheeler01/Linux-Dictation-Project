#!/usr/bin/env python3
import whisper
import sounddevice as sd
import numpy as np
import tempfile
import os
import scipy.io.wavfile
import time
import re
import threading
import signal
import json
from PyQt5 import QtWidgets, QtGui, QtCore
import psutil
import sys
import logging
import subprocess
import pynput.keyboard
from pynput.mouse import Controller as MouseController, Button as MouseButton

# Configuration path
config_path = os.path.expanduser("~/.config/whisper-dictate/settings.json")
os.makedirs(os.path.dirname(config_path), exist_ok=True)
default_config = {
    "startup_listening": "asleep",
    "startup_mode": "dictation",
    "noise_suppression": {"enabled": False},
    "use_fp16": False,
    "mouse_step": 50,
    "app_aliases": {
        "notepad": "notepad.exe",
        "calculator": "calc.exe",
        "paint": "mspaint.exe",
        "chrome": "chrome.exe",
        "edge": "msedge.exe"
    }
}
try:
    with open(config_path, "r") as f:
        config = json.load(f)
except (FileNotFoundError, json.JSONDecodeError):
    config = default_config
    with open(config_path, "w") as f:
        json.dump(config, f, indent=2)

startup_mode = config.get("startup_mode", "dictation")
startup_listening = config.get("startup_listening", "asleep")
mode = startup_mode
listening = startup_listening == "awake"

log_path = os.path.expanduser("~/.local/share/whisper-dictation.log")
os.makedirs(os.path.dirname(log_path), exist_ok=True)
logging.basicConfig(filename=log_path, level=logging.INFO, format="%(asctime)s %(message)s")

import torch
import torch

try:
    if torch.cuda.is_available():
        logging.info("Loading Whisper model in FP32 on GPU.")
        model = whisper.load_model("small").to("cuda").to(dtype=torch.float32)
    else:
        logging.info("Loading Whisper model in FP32 on CPU.")
        model = whisper.load_model("small").to("cpu").to(dtype=torch.float32)
except Exception as e:
    logging.error(f"Model loading failed: {e}")
    model = whisper.load_model("small").to("cpu").to(dtype=torch.float32)

    logging.info("Loading Whisper model in FP16 on GPU.")
    model = whisper.load_model("small").to("cuda").half()
else:
    logging.info("Loading Whisper model in FP32 on CPU.")
    model = whisper.load_model("small")

sample_rate = 16000
duration = 5

key_map = {
    "ctrl": pynput.keyboard.Key.ctrl,
    "alt": pynput.keyboard.Key.alt,
    "shift": pynput.keyboard.Key.shift,
    "super": pynput.keyboard.Key.cmd,
    "delete": pynput.keyboard.Key.delete,
    "backspace": pynput.keyboard.Key.backspace,
    "tab": pynput.keyboard.Key.tab,
    "enter": pynput.keyboard.Key.enter,
    "escape": pynput.keyboard.Key.esc,
    "space": pynput.keyboard.Key.space,
    "delete": pynput.keyboard.Key.delete,
    "left": pynput.keyboard.Key.left,
    "right": pynput.keyboard.Key.right,
    "up": pynput.keyboard.Key.up,
    "down": pynput.keyboard.Key.down,
}

nato_map = {
    "alpha": "a", "bravo": "b", "charlie": "c", "delta": "d", "echo": "e", "foxtrot": "f",
    "golf": "g", "hotel": "h", "india": "i", "juliett": "j", "kilo": "k", "lima": "l",
    "mike": "m", "november": "n", "oscar": "o", "papa": "p", "quebec": "q", "romeo": "r",
    "sierra": "s", "tango": "t", "uniform": "u", "victor": "v", "whiskey": "w",
    "x-ray": "x", "yankee": "y", "zulu": "z"
}
spoken_aliases = {'semicolon': ';', 'colon': ':', 'comma': ',', 'period': '.', 'dot': '.', 'slash': '/', 'backslash': '\\', 'quote': "'", 'double quote': '"', 'apostrophe': "'", 'dash': '-', 'minus': '-', 'equals': '=', 'plus': '+', 'underscore': '_', 'tilde': '~', 'grave': '`', 'backtick': '`', 'exclamation': '!', 'at': '@', 'hash': '#', 'pound': '#', 'dollar': '$', 'percent': '%', 'caret': '^', 'ampersand': '&', 'asterisk': '*', 'star': '*', 'pipe': '|', 'open bracket': '[', 'close bracket': ']', 'open brace': '{', 'close brace': '}', 'open paren': '(', 'close paren': ')', 'less than': '<', 'greater than': '>', 'question mark': '?'}


held_keys = set()
kb = pynput.keyboard.Controller()
mouse = MouseController()
mouse_held = False
last_transcript = ""

def type_text(text):
    for char in text:
        kb.type(char)

def parse_key_combo(text):
    words = text.strip().lower().split()
    return [key_map.get(w, w) for w in words]

def press_keys(keys):
    try:
        for k in keys:
            kb.press(k)
        for k in reversed(keys):
            kb.release(k)
    except Exception as e:
        print(f"[ERROR] Keypress failed: {e}")

def hold_key(key_name):
    key = key_map.get(key_name, key_name)
    if key not in held_keys:
        try:
            kb.press(key)
            held_keys.add(key)
        except Exception as e:
            print(f"[ERROR] Failed to hold {key_name}: {e}")

def release_all_keys():
    for k in list(held_keys):
        try:
            kb.release(k)
        except:
            pass
    held_keys.clear()







def launch_app(app_name: str):
    # Look up alias first
    target = config.get("app_aliases", {}).get(app_name, app_name)
    try:
        if sys.platform.startswith("win"):
            # Use 'start' to resolve PATH / App Paths
            subprocess.Popen(["cmd", "/c", "start", "", target], shell=False)
        else:
            # On POSIX, try launching directly (user can map aliases to full paths)
            subprocess.Popen([target], shell=False)
        logging.info(f"Launched app: {target}")
    except Exception as e:
        logging.error(f"Failed to launch '{app_name}' -> {target}: {e}")
        print(f"[ERROR] Failed to open {app_name}: {e}")

def close_app(app_name: str):
    # Try to match process by alias target first, then by given name (substring match, case-insensitive)
    names_to_match = {app_name.lower()}
    alias_target = config.get("app_aliases", {}).get(app_name, None)
    if alias_target:
        names_to_match.add(Path(alias_target).name.lower())

    matched = 0
    for p in psutil.process_iter(["name"]):
        try:
            pname = (p.info.get("name") or "").lower()
            if any(n in pname for n in names_to_match):
                p.terminate()
                matched += 1
        except Exception:
            continue
    # Fallback: force kill if still alive
    if matched:
        gone, alive = psutil.wait_procs([pr for pr in psutil.process_iter() if any(n in (getattr(pr, "name", lambda: "")() or "").lower() for n in names_to_match)], timeout=1)
        for pr in alive:
            try:
                pr.kill()
            except Exception:
                pass
    if matched == 0:
        print(f"[INFO] No running process matched '{app_name}'.")
    else:
        print(f"[INFO] Closed {matched} process(es) for '{app_name}'.")


def handle_command(text):
    text = spoken_aliases.get(text, text)
    words = text.strip().lower().split()

    if text.startswith("hold ") and len(words) == 2:
        hold_key(words[1])
    elif text.startswith("press ") and len(words) == 2:
        key = key_map.get(words[1], words[1])
        try:
            kb.press(key)
            kb.release(key)
        except Exception as e:
            print(f"[ERROR] Failed to press {words[1]}: {e}")
            logging.error(f"Failed to press {words[1]}: {e}")
    elif text.startswith("select line ") and len(words) == 3 and words[2].isdigit():
        line_num = int(words[2])
        try:
            for _ in range(line_num):
                kb.press(key_map.get("home", pynput.keyboard.Key.home))
                kb.release(key_map.get("home", pynput.keyboard.Key.home))
                kb.press(key_map.get("shift", pynput.keyboard.Key.shift))
                kb.press(key_map.get("down", pynput.keyboard.Key.down))
                kb.release(key_map.get("down", pynput.keyboard.Key.down))
                kb.release(key_map.get("shift", pynput.keyboard.Key.shift))
        except Exception as e:
            print(f"[ERROR] Failed to select line: {e}")
            logging.error(f"Failed to select line: {e}")
    elif text.startswith("select word ") and len(words) == 3:
        try:
            kb.press(key_map.get("ctrl", pynput.keyboard.Key.ctrl))
            for _ in range(100):
                kb.press(key_map.get("left", pynput.keyboard.Key.left))
                kb.release(key_map.get("left", pynput.keyboard.Key.left))
            kb.release(key_map.get("ctrl", pynput.keyboard.Key.ctrl))

            kb.press(key_map.get("shift", pynput.keyboard.Key.shift))
            for _ in range(100):
                kb.press(key_map.get("right", pynput.keyboard.Key.right))
                kb.release(key_map.get("right", pynput.keyboard.Key.right))
            kb.release(key_map.get("shift", pynput.keyboard.Key.shift))
        except Exception as e:
            print(f"[ERROR] Failed to select word: {e}")
            logging.error(f"Failed to select word: {e}")

    elif text.startswith("open "):
        app = text.split("open ", 1)[1].strip()
        if app:
            launch_app(app)
    elif text.startswith("close "):
        app = text.split("close ", 1)[1].strip()
        if app:
            close_app(app)

    elif "release keys" in text:
        release_all_keys()
    elif all(w in nato_map for w in words):
        spelled = ''.join(nato_map[w] for w in words)
        type_text(spelled)
    elif len(words) >= 2 and words[0] in key_map and "click" not in words:
        combo = parse_key_combo(text)
        press_keys(combo)
    elif text in key_map:
        press_keys([key_map[text]])
    elif len(text) == 1 and text in r"!@#$%^&*()_+-={}[]|\:;\"'<>,.?/~`":
        try:
            kb.press(text)
            kb.release(text)
        except Exception as e:
            print(f"[ERROR] Failed to press symbol {text}: {e}")
            logging.error(f"Failed to press symbol {text}: {e}")
    elif text == "copy":
        press_keys([key_map["ctrl"], 'c'])
    elif text == "paste":
        press_keys([key_map["ctrl"], 'v'])
    elif text == "select all":
        press_keys([key_map["ctrl"], 'a'])
    
    elif text.startswith("move mouse"):
        # Support: "move mouse left 1000" or "move mouse 1000 left" or no amount (uses settings)
        dirs = {"left": (-1, 0), "right": (1, 0), "up": (0, -1), "down": (0, 1)}
        direction = None
        amount = None
        # find direction anywhere
        for i, w in enumerate(words):
            if w in dirs:
                direction = w
                # amount may be next or previous token
                if i + 1 < len(words) and words[i + 1].isdigit():
                    amount = int(words[i + 1])
                elif i - 1 >= 0 and words[i - 1].isdigit():
                    amount = int(words[i - 1])
                break
        if amount is None:
            amount = int(config.get("mouse_step", 50))
        if direction:
            dx, dy = dirs[direction]
            mouse.move(dx * amount, dy * amount)

    elif text == "click":
        mouse.click(MouseButton.left)
    elif text == "double click":
        mouse.click(MouseButton.left, 2)
    elif text in ("left click", "left mouse click"):
        mouse.click(MouseButton.left)
    elif text in ("left double click", "double left click"):
        mouse.click(MouseButton.left, 2)

    elif text == "right click":
        mouse.click(MouseButton.right)
    elif text == "middle click":
        mouse.click(MouseButton.middle)
    elif text == "scroll up":
        mouse.scroll(0, 2)
    elif text == "scroll down":
        mouse.scroll(0, -2)
    elif text == "hold click":
        global mouse_held
        try:
            mouse.press(MouseButton.left)
            mouse_held = True
        except Exception as e:
            print(f"[ERROR] Failed to hold click: {e}")

    elif text == "release click":
        try:
            mouse.release(MouseButton.left)
            mouse_held = False
        except Exception as e:
            print(f"[ERROR] Failed to release click: {e}")




def normalize_command(text):
    return re.sub(r"[^a-zA-Z0-9 -]+", "", text.strip().lower())


def dictation_loop():
    logging.info("Dictation loop started.")
    global listening, mode
    while True:
        logging.debug("Recording audio...")
        logging.debug("Recording audio...")
        audio = sd.rec(int(duration * sample_rate), samplerate=sample_rate, channels=1)
        sd.wait()
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmpfile:
            filename = tmpfile.name
            scipy.io.wavfile.write(filename, sample_rate, audio)
        try:
            logging.debug(f"Transcribing audio file: {filename}")
            result = model.transcribe(filename, language='en')
            logging.debug(f"Transcription result: {{result}}")
            text = result["text"].strip()
            norm = normalize_command(text)
            print(f"Transcript: {text}")
            global last_transcript
            last_transcript = text[:200]
            if "wake up" in norm or "start listening" in norm:
                listening = True
            elif "stop listening" in norm:
                listening = False
            elif "command mode" in norm:
                mode = "command"
            elif "dictation mode" in norm:
                mode = "dictation"
            elif listening:
                if mode == "dictation":
                    type_text(text)
                elif mode == "command":
                    handle_command(norm)
        finally:
            time.sleep(0.5)
            try:
                os.remove(filename)
            except PermissionError:
                print(f"[WARNING] Could not delete temp file: {filename}")

# UI Widget
class DictationWidget(QtWidgets.QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowFlags(QtCore.Qt.WindowStaysOnTopHint | QtCore.Qt.FramelessWindowHint)
        self.setGeometry(100, 100, 525, 175)
        self.setStyleSheet("background-color: black; color: white;")
        self.setMouseTracking(True)

        self.label = QtWidgets.QLabel(self)
        self.label.setAlignment(QtCore.Qt.AlignCenter)
        self.label.setGeometry(10, 10, 400, 150)
        self.label.setStyleSheet("font-size: 16px;")

        self.keys_label = QtWidgets.QLabel(self)
        self.keys_label.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
        self.keys_label.setGeometry(410, 130, 100, 30)
        self.keys_label.setStyleSheet("font-size: 14px; color: yellow;")

        self.settings_icon = QtWidgets.QLabel(self)
        self.settings_icon.setPixmap(QtGui.QPixmap(16, 16))
        self.settings_icon.setText("⚙️")
        self.settings_icon.setGeometry(470, 10, 32, 32)
        self.settings_icon.mousePressEvent = self.open_settings

        self.close_button = QtWidgets.QPushButton("❌", self)
        self.close_button.setGeometry(495, 5, 24, 24)
        self.close_button.clicked.connect(QtWidgets.QApplication.quit)
        self.close_button.setStyleSheet("font-size: 14px; background-color: transparent; color: white;")

        self.update_text()
        self.show()

    def mousePressEvent(self, event):
        global mode
        if event.button() == QtCore.Qt.LeftButton and event.pos().x() < 400:
            mode = "command" if mode == "dictation" else "dictation"
            self.update_text()

    def update_text(self):
        self.label.setText(f"Mode: {mode.title()}\nListening: {'Yes' if listening else 'No'}\n\nLast heard: {last_transcript}")
        if held_keys:
            readable_keys = ', '.join(str(k).split('.')[-1] for k in held_keys)
            self.keys_label.setText(f"Held Keys: {readable_keys}")
        else:
            self.keys_label.setText("Held Keys: None")

    def open_settings(self, event):
        self.settings = SettingsWindow()
        self.settings.exec_()


class DebugWindow(QtWidgets.QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Live Debug")
        self.resize(400, 200)
        self.label = QtWidgets.QLabel("Listening...", self)
        self.label.setGeometry(10, 10, 380, 180)
        self.timer = QtCore.QTimer()
        self.timer.timeout.connect(self.update_debug)
        self.timer.start(1000)
        self.show()

    def update_debug(self):
        self.label.setText(f"Mode: {mode}\nListening: {'Yes' if listening else 'No'}")

class TrainingWindow(QtWidgets.QDialog):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Voice Training")
        self.resize(500, 300)
        layout = QtWidgets.QVBoxLayout()
        self.instructions = QtWidgets.QLabel("Please read the following sentence clearly:")
        self.sentence = QtWidgets.QLabel("The quick brown fox jumps over the lazy dog.")
        self.done_button = QtWidgets.QPushButton("Done")
        self.done_button.clicked.connect(self.accept)
        layout.addWidget(self.instructions)
        layout.addWidget(self.sentence)
        layout.addWidget(self.done_button)
        
        self.debug_button = QtWidgets.QPushButton("Open Debug Window")
        self.debug_button.clicked.connect(self.open_debug)
        self.training_button = QtWidgets.QPushButton("Start Voice Training")
        self.training_button.clicked.connect(self.open_training)
        layout.addRow(self.debug_button)
        layout.addRow(self.fp16Check)
        layout.addRow(self.training_button)
        self.setLayout(layout)

    def open_debug(self):
        self.debug_win = DebugWindow()

    def open_training(self):
        self.train_win = TrainingWindow()
        
        self.show()

class SettingsWindow(QtWidgets.QDialog):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Settings")
        self.setGeometry(100, 100, 500, 300)

        self.listenBox = QtWidgets.QComboBox()
        self.listenBox.addItems(["asleep", "awake"])
        self.listenBox.setCurrentText(config.get("startup_listening", "asleep"))

        self.modeBox = QtWidgets.QComboBox()
        self.modeBox.addItems(["dictation", "command"])
        self.modeBox.setCurrentText(config.get("startup_mode", "dictation"))

        self.noiseCheck = QtWidgets.QCheckBox("Enable Noise Suppression")
        self.noiseCheck.setChecked(config.get("noise_suppression", {}).get("enabled", False))
        self.fp16Check = QtWidgets.QCheckBox("Use FP16 (GPU Only, Experimental)")
        self.fp16Check.setChecked(config.get("use_fp16", False))

        # Mouse move pixels
        self.mouseStepSpin = QtWidgets.QSpinBox()
        self.mouseStepSpin.setRange(1, 2000)
        self.mouseStepSpin.setValue(int(config.get("mouse_step", 50)))


        saveBtn = QtWidgets.QPushButton("Save")
        saveBtn.clicked.connect(self.save_config)

        layout = QtWidgets.QFormLayout()
        layout.addRow("Startup Listening:", self.listenBox)
        layout.addRow("Startup Mode:", self.modeBox)
        layout.addRow(self.noiseCheck)
        layout.addRow("Mouse move pixels:", self.mouseStepSpin)
        layout.addWidget(saveBtn)
        
        self.debug_button = QtWidgets.QPushButton("Open Debug Window")
        self.debug_button.clicked.connect(self.open_debug)
        self.training_button = QtWidgets.QPushButton("Start Voice Training")
        self.training_button.clicked.connect(self.open_training)
        layout.addRow(self.debug_button)
        layout.addRow(self.fp16Check)
        layout.addRow(self.training_button)
        self.setLayout(layout)

    def open_debug(self):
        self.debug_win = DebugWindow()

    def open_training(self):
        self.train_win = TrainingWindow()
        

    def save_config(self):
        config["startup_listening"] = self.listenBox.currentText()
        config["startup_mode"] = self.modeBox.currentText()
        config["noise_suppression"]["enabled"] = self.noiseCheck.isChecked()
        config["use_fp16"] = self.fp16Check.isChecked()
        config["mouse_step"] = int(self.mouseStepSpin.value())
        with open(config_path, "w") as f:
            json.dump(config, f, indent=2)
        self.accept()

def update_widget_periodically(widget):
    while True:
        widget.update_text()
        time.sleep(1)

if __name__ == "__main__":
    signal.signal(signal.SIGINT, lambda sig, frame: sys.exit(0))
    threading.Thread(target=dictation_loop, daemon=True).start()
    app = QtWidgets.QApplication(sys.argv)
    widget = DictationWidget()
    updater = threading.Thread(target=update_widget_periodically, args=(widget,), daemon=True)
    updater.start()
    sys.exit(app.exec_())