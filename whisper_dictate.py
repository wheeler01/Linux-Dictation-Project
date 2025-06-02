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
from PyQt5 import QtWidgets, QtGui
import psutil
import sys
tray_icon = None

# Load whisper model
model = whisper.load_model("small")

# Audio recording settings
duration = 15  # seconds
sample_rate = 16000

# Global indicators
MOUSE_SPEED = 50  # Pixels per movement step
global mode
mode = "dictation"
global listening
listening = False  # Start in sleep mode

# Spoken punctuation and command replacements
REPLACEMENTS = {
    r"\bcomma\b": ",",
    r"\bperiod\b": ".",
    r"\bquestion mark\b": "?",
    r"\bexclamation mark\b": "!",
    r"\bnew paragraph\b": "\n\n",
    r"\bnew line\b": "\n",
}

CONTROL_COMMANDS = {
    "press enter": "KEY_ENTER",
    "press space": "KEY_SPACE",
    "increase mouse sensitivity": "MOUSE_SPEED_UP",
    "decrease mouse sensitivity": "MOUSE_SPEED_DOWN",
    "press left arrow": "KEY_LEFT",
    "press right arrow": "KEY_RIGHT",
    "press up arrow": "KEY_UP",
    "press down arrow": "KEY_DOWN",
    "move mouse up": "MOUSE_UP",
    "move mouse down": "MOUSE_DOWN",
    "move mouse left": "MOUSE_LEFT",
    "move mouse right": "MOUSE_RIGHT",
    "stop mouse": "MOUSE_STOP",
    "single click mouse": "MOUSE_CLICK",
    "double click mouse": "MOUSE_DCLICK",
    "right click mouse": "MOUSE_RCLICK",
    "delete that": "BACKSPACE",
    "backspace": "BACKSPACE",
    "delete word": "DELETE_WORD",
    "clear line": "CLEAR_LINE",
    "command mode": "ENTER_COMMAND_MODE",
    "dictation mode": "ENTER_DICTATION_MODE",
    "stop listening": "SLEEP_MODE",
    "go to sleep": "SLEEP_MODE",
    "start listening": "WAKE_MODE",
    "wake up": "WAKE_MODE",
}

NATO_PHONETIC = {
    "alpha": "a", "bravo": "b", "charlie": "c", "delta": "d", "echo": "e", "foxtrot": "f",
    "golf": "g", "hotel": "h", "india": "i", "juliett": "j", "kilo": "k", "lima": "l",
    "mike": "m", "november": "n", "oscar": "o", "papa": "p", "quebec": "q", "romeo": "r",
    "sierra": "s", "tango": "t", "uniform": "u", "victor": "v", "whiskey": "w", "x-ray": "x",
    "yankee": "y", "zulu": "z"
}

def record_audio():
    audio = sd.rec(int(duration * sample_rate), samplerate=sample_rate, channels=1, dtype='float32')
    sd.wait()
    return np.squeeze(audio)

def save_audio_to_wav(audio_data, filename):
    scipy.io.wavfile.write(filename, sample_rate, audio_data)

def apply_replacements(text):
    global mode, listening
    command = text.lower().strip()

    if command == "command mode":
        mode = "command"
        print("⚙️ Switched to command mode")
        return ""
    elif command == "dictation mode":
        mode = "dictation"
        print("📝 Switched to dictation mode")
        return ""
    elif command in ["stop listening", "go to sleep"]:
        listening = False
        print("😴 Listening paused")
        return ""
    elif command in ["start listening", "wake up"]:
        listening = True
        print("🎙️ Listening resumed")
        return ""

    if not listening:
        return ""

    if mode == "command":
        match = re.match(r"(delete|backspace) (\d+)", command)
        if match:
            action, count = match.groups()
            return f"{action.upper()}_{count}"

        match_key = re.match(r"press ([a-z0-9])", command)
        match_ctrl = re.match(r"control ([a-z0-9])", command)
        match_alt = re.match(r"alt ([a-z0-9])", command)
        match_meta = re.match(r"(windows|logo) ([a-z0-9])", command)
        match_combo = re.match(r"(control|alt|shift|windows|logo)(?: (control|alt|shift|windows|logo))? ([a-z0-9])", command)

        if match_ctrl:
            return f"CTRL_{match_ctrl.group(1).lower()}"
        elif match_alt:
            return f"ALT_{match_alt.group(1).lower()}"
        elif match_combo:
            mods = [m for m in match_combo.groups()[:2] if m]
            key = match_combo.group(3)
            mods = [m.replace("windows", "super").replace("logo", "super") for m in mods]
            return f"COMBO_{'+'.join(mods)}+{key.lower()}"
        elif match_meta:
            return f"META_{match_meta.group(2).lower()}"
        elif match_key:
            return f"KEY_{match_key.group(1).upper()}"

        match_launch = re.match(r"open (.+)", command)
        if match_launch:
            name = match_launch.group(1).strip().lower()
            return f"LAUNCH_{name}"
        match_kill = re.match(r"close (.+)", command)
        if match_kill:
            name = match_kill.group(1).strip().lower()
            return f"KILL_{name}"

        if match_launch:
            return f"LAUNCH_{match_launch.group(1)}"
        elif match_kill:
            return f"KILL_{match_kill.group(1)}"

        if command in CONTROL_COMMANDS:
            return CONTROL_COMMANDS[command]

        return ""

    if command.startswith("capital "):
        code = command.replace("capital ", "").strip()
        if code in NATO_PHONETIC:
            return NATO_PHONETIC[code].upper()
    elif command in NATO_PHONETIC:
        return NATO_PHONETIC[command]

    if all(word in NATO_PHONETIC for word in command.split()):
        return ''.join(NATO_PHONETIC[word] for word in command.split())

    for pattern, replacement in REPLACEMENTS.items():
        text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)

    if len(text) > 0:
        text = text[0].upper() + text[1:]

    return text.strip()

def type_text(text):
    if text == "BACKSPACE":
        subprocess.run(["xdotool", "key", "BackSpace"])
    elif text.startswith("DELETE_") or text.startswith("BACKSPACE_"):
        try:
            count = int(text.split("_")[1])
            for _ in range(count):
                subprocess.run(["xdotool", "key", "BackSpace"])
        except ValueError:
            pass
    elif text == "DELETE_WORD":
        subprocess.run(["xdotool", "key", "ctrl+BackSpace"])
    elif text == "CLEAR_LINE":
        subprocess.run(["xdotool", "key", "Home"])
        subprocess.run(["xdotool", "key", "Shift+End"])
        subprocess.run(["xdotool", "key", "BackSpace"])
    elif mode == "command":
        if text == "MOUSE_SPEED_UP":
            global MOUSE_SPEED
            MOUSE_SPEED = min(200, MOUSE_SPEED + 10)
            print(f"🔧 Increased mouse speed to {MOUSE_SPEED}")
        elif text == "MOUSE_SPEED_DOWN":
            MOUSE_SPEED = max(10, MOUSE_SPEED - 10)
            print(f"🔧 Decreased mouse speed to {MOUSE_SPEED}")
        elif text == "KEY_LEFT":
            subprocess.run(["xdotool", "key", "Left"])
        elif text == "KEY_RIGHT":
            subprocess.run(["xdotool", "key", "Right"])
        elif text == "KEY_UP":
            subprocess.run(["xdotool", "key", "Up"])
        elif text == "KEY_DOWN":
            subprocess.run(["xdotool", "key", "Down"])
        elif text == "KEY_ENTER":
            subprocess.run(["xdotool", "key", "Return"])
        elif text == "KEY_SPACE":
            subprocess.run(["xdotool", "key", "space"])
        elif text.startswith("CTRL_"):
            subprocess.run(["xdotool", "key", f"ctrl+{text[5:]}"])
        elif text.startswith("ALT_"):
            subprocess.run(["xdotool", "key", f"alt+{text[4:]}"])
        elif text.startswith("META_"):
            subprocess.run(["xdotool", "key", f"super+{text[5:]}"])
        elif text.startswith("COMBO_"):
            combo_keys = text[6:]
            subprocess.run(["xdotool", "key", combo_keys])
        elif text.startswith("LAUNCH_"):
            app_name = text[7:].strip().lower()
            import shutil
            path = shutil.which(app_name)
            if path:
                subprocess.Popen([path])
                subprocess.run(["notify-send", "✅ Opened", app_name])
            else:
                print(f"❌ Application '{app_name}' not found")
                subprocess.run(["notify-send", "❌ Not Found", app_name])
        elif text.startswith("KILL_"):
            app_name = text[5:].strip().lower()
            import psutil
            for proc in psutil.process_iter(['pid', 'name']):
                if app_name in proc.info['name'].lower():
                    proc.kill()
                    print(f"✅ Closed application: {proc.info['name']}")
                    subprocess.run(["notify-send", "✅ Closed", proc.info['name']])
        elif text.startswith("KEY_") and len(text) == 5:
            subprocess.run(["xdotool", "key", text[4:].lower()])
            subprocess.run(["xdotool", "key", "space"])
            subprocess.run(["xdotool", "key", "Down"])
        if text == "MOUSE_UP":
            subprocess.run(["xdotool", "mousemove_relative", "--", "0", f"-{MOUSE_SPEED}"])
        elif text == "MOUSE_DOWN":
            subprocess.run(["xdotool", "mousemove_relative", "--", "0", f"{MOUSE_SPEED}"])
        elif text == "MOUSE_LEFT":
            subprocess.run(["xdotool", "mousemove_relative", "--", f"-{MOUSE_SPEED}", "0"])
        elif text == "MOUSE_RIGHT":
            subprocess.run(["xdotool", "mousemove_relative", "--", f"{MOUSE_SPEED}", "0"])
        elif text == "MOUSE_CLICK":
            subprocess.run(["xdotool", "click", "1"])
        elif text == "MOUSE_DCLICK":
            subprocess.run(["xdotool", "click", "1"])
            subprocess.run(["xdotool", "click", "1"])
        elif text == "MOUSE_RCLICK":
            subprocess.run(["xdotool", "click", "3"])
    elif text:
        tray_icon.update_tooltip()
        subprocess.run(["xdotool", "type", "--delay", "50", text])

def dictation_loop():
    try:
        while True:
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmpfile:
                audio = record_audio()
                save_audio_to_wav(audio, tmpfile.name)
                result = model.transcribe(tmpfile.name)
                tray_icon.update_tooltip()
                text = result["text"].strip()
                os.remove(tmpfile.name)

                if text:
                    processed = apply_replacements(text)
                    if processed:
                        type_text(processed + (" " if not processed.startswith("BACKSPACE") and len(processed) > 1 else ""))
    except KeyboardInterrupt:
        print("\n🛑 Dictation stopped.")

class SystemTrayIcon(QtWidgets.QSystemTrayIcon):
    def __init__(self, parent=None):
        self.icon_active = QtGui.QIcon("/usr/share/icons/HighContrast/32x32/status/audio-input-microphone.png")
        self.icon_sleeping = QtGui.QIcon("/usr/share/icons/HighContrast/32x32/status/appointment-missed.png")
        super().__init__(self.icon_sleeping, parent)
        self.update_tooltip()

        menu = QtWidgets.QMenu(parent)
        exit_action = menu.addAction("Exit")
        exit_action.triggered.connect(QtWidgets.qApp.quit)
        self.setContextMenu(menu)
        self.activated.connect(self.icon_clicked)

    def icon_clicked(self, reason):
        global mode
        if reason == self.Trigger:
            mode = "command" if mode == "dictation" else "dictation"
            print(f"🔁 Switched to {mode} mode")
            self.update_tooltip()

    def update_icon(self):
        self.setIcon(self.icon_active if listening else self.icon_sleeping)

    def update_tooltip(self):
        state = "Listening" if listening else "Asleep"
        self.setToolTip(f"Linux Dictation - {mode.title()} Mode - {state}")
        self.update_icon()

def main():
    global tray_icon
    app = QtWidgets.QApplication(sys.argv)
    w = QtWidgets.QWidget()
    tray_icon = SystemTrayIcon(w)
    tray_icon.show()

    threading.Thread(target=dictation_loop, daemon=True).start()
    signal.signal(signal.SIGINT, signal.SIG_DFL)
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()

