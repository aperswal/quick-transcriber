import sounddevice as sd
import numpy as np
from vosk import Model, KaldiRecognizer
import json
import sys
import threading
import pyautogui
import queue
from PyQt6.QtWidgets import QApplication, QMainWindow, QLabel, QTextEdit, QVBoxLayout, QWidget
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QShortcut, QKeySequence

class TranscriberWindow(QMainWindow):
    update_status = pyqtSignal(str)
    update_preview = pyqtSignal(str)

    def __init__(self, app_instance):
        super().__init__()
        self.app_instance = app_instance
        self.setWindowTitle("Speech Transcriber")
        self.setGeometry(100, 100, 400, 200)
        self.setWindowFlags(Qt.WindowType.WindowStaysOnTopHint)

        # Create central widget and layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)

        # Create status label
        self.status_label = QLabel("Press Ctrl+Shift+R to start/stop recording")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.status_label)

        # Create preview text area
        self.preview_text = QTextEdit()
        self.preview_text.setReadOnly(True)
        layout.addWidget(self.preview_text)

        # Connect signals
        self.update_status.connect(self.status_label.setText)
        self.update_preview.connect(self.preview_text.setText)

        # Setup shortcuts
        self.setup_shortcuts()

    def setup_shortcuts(self):
        # Record shortcut (Ctrl+Shift+R)
        record_shortcut = QShortcut(QKeySequence("Ctrl+Shift+R"), self)
        record_shortcut.activated.connect(self.app_instance.toggle_recording)

        # Quit shortcut (Ctrl+Shift+Q)
        quit_shortcut = QShortcut(QKeySequence("Ctrl+Shift+Q"), self)
        quit_shortcut.activated.connect(self.app_instance.quit_app)

class TranscriberApp:
    def __init__(self):
        self.recording = False
        self.audio_queue = queue.Queue()
        self.text_queue = queue.Queue()
        
        # Initialize GUI
        self.app = QApplication(sys.argv)
        self.window = TranscriberWindow(self)
        self.window.show()
        
        # Initialize Vosk model
        try:
            print("Loading speech recognition model...")
            self.model = Model("vosk-model-small-en-us-0.15")
            self.recognizer = KaldiRecognizer(self.model, 16000)
            print("Model loaded successfully!")
        except Exception as e:
            print(f"Error loading model: {e}")
            sys.exit(1)
        
        # Start processing threads
        self.audio_thread = threading.Thread(target=self.process_audio, daemon=True)
        self.text_thread = threading.Thread(target=self.process_text, daemon=True)
        self.audio_thread.start()
        self.text_thread.start()

    def toggle_recording(self):
        self.recording = not self.recording
        if self.recording:
            self.window.update_status.emit("Recording... (Press Ctrl+Shift+R to stop)")
            self.start_recording()
        else:
            self.window.update_status.emit("Stopped (Press Ctrl+Shift+R to start)")
            self.stop_recording()

    def audio_callback(self, indata, frames, time, status):
        if status:
            print(status)
        if self.recording:
            self.audio_queue.put(bytes(indata))

    def start_recording(self):
        self.stream = sd.InputStream(
            channels=1,
            samplerate=16000,
            callback=self.audio_callback,
            dtype=np.int16
        )
        self.stream.start()

    def stop_recording(self):
        if hasattr(self, 'stream'):
            self.stream.stop()
            self.stream.close()

    def process_audio(self):
        while True:
            if not self.audio_queue.empty():
                audio_data = self.audio_queue.get()
                if self.recognizer.AcceptWaveform(audio_data):
                    result = json.loads(self.recognizer.Result())
                    if result.get("text", "").strip():
                        self.text_queue.put(result["text"])

    def process_text(self):
        while True:
            if not self.text_queue.empty():
                text = self.text_queue.get()
                # Update preview
                self.window.update_preview.emit(text)
                # Type text at cursor position
                pyautogui.write(text + " ")

    def quit_app(self):
        self.stop_recording()
        self.app.quit()
        sys.exit(0)

    def run(self):
        return self.app.exec()

if __name__ == "__main__":
    app = TranscriberApp()
    app.run()