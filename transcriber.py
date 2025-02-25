import sounddevice as sd
import numpy as np
from vosk import Model, KaldiRecognizer
import json
import sys
import threading
import pyautogui
import pyperclip
import queue
import time
from PyQt6.QtWidgets import (QApplication, QMainWindow, QLabel, QTextEdit, 
                            QVBoxLayout, QWidget, QPushButton, QHBoxLayout, QComboBox)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QTimer
from PyQt6.QtGui import QShortcut, QKeySequence, QFont, QColor, QPalette

class TranscriberWindow(QMainWindow):
    update_status = pyqtSignal(str)
    update_preview = pyqtSignal(str)
    update_recording_status = pyqtSignal(bool)
    update_debug_info = pyqtSignal(str)
    update_partial_text = pyqtSignal(str)

    def __init__(self, app_instance):
        super().__init__()
        self.app_instance = app_instance
        self.setWindowTitle("Quick Transcriber")
        self.setGeometry(100, 100, 500, 400)  # Slightly taller for extra controls
        self.setWindowFlags(Qt.WindowType.WindowStaysOnTopHint)

        # Create central widget and layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)

        # Create status label
        self.status_label = QLabel("Press Ctrl+Shift+R to start/stop recording")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.status_label.setFont(QFont("Arial", 11, QFont.Weight.Bold))
        main_layout.addWidget(self.status_label)

        # Create recording indicator
        self.recording_indicator = QLabel("●")
        self.recording_indicator.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.recording_indicator.setFont(QFont("Arial", 24))
        self.set_recording_inactive()
        main_layout.addWidget(self.recording_indicator)
        
        # Add device selection
        device_layout = QHBoxLayout()
        device_label = QLabel("Input Device:")
        self.device_selector = QComboBox()
        self.populate_devices()
        self.device_selector.currentIndexChanged.connect(self.app_instance.change_device)
        device_layout.addWidget(device_label)
        device_layout.addWidget(self.device_selector)
        main_layout.addLayout(device_layout)
        
        # Add partial recognition text
        self.partial_text = QLabel("Partial: ")
        font = QFont("Arial", 9)
        font.setItalic(True)
        self.partial_text.setFont(font)
        main_layout.addWidget(self.partial_text)

        # Create preview text area with better styling
        self.preview_text = QTextEdit()
        self.preview_text.setReadOnly(True)
        self.preview_text.setFont(QFont("Arial", 11))
        self.preview_text.setMinimumHeight(120)
        main_layout.addWidget(self.preview_text)
        
        # Add debug info area
        self.debug_info = QLabel("Audio status: Not started")
        self.debug_info.setAlignment(Qt.AlignmentFlag.AlignLeft)
        self.debug_info.setFont(QFont("Arial", 9))
        main_layout.addWidget(self.debug_info)

        # Add buttons
        button_layout = QHBoxLayout()
        
        self.clear_button = QPushButton("Clear Context")
        self.clear_button.clicked.connect(self.app_instance.clear_context)
        button_layout.addWidget(self.clear_button)
        
        self.paste_button = QPushButton("Paste All")
        self.paste_button.clicked.connect(self.app_instance.paste_all_text)
        button_layout.addWidget(self.paste_button)
        
        main_layout.addLayout(button_layout)

        # Create keyboard shortcut hints
        shortcuts_label = QLabel("Shortcuts: Ctrl+Shift+R (record) | Ctrl+Shift+C (clear) | Ctrl+Shift+P (paste) | Ctrl+Shift+Q (quit)")
        shortcuts_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        shortcuts_label.setFont(QFont("Arial", 9))
        main_layout.addWidget(shortcuts_label)

        # Connect signals
        self.update_status.connect(self.status_label.setText)
        self.update_preview.connect(self.preview_text.setText)
        self.update_recording_status.connect(self.update_recording_indicator)
        self.update_debug_info.connect(self.debug_info.setText)
        self.update_partial_text.connect(self.partial_text.setText)

        # Setup shortcuts
        self.setup_shortcuts()
    
    def populate_devices(self):
        devices = sd.query_devices()
        for i, device in enumerate(devices):
            if device['max_input_channels'] > 0:  # Only add input devices
                self.device_selector.addItem(f"{device['name']}", i)
    
    def set_recording_active(self):
        palette = self.recording_indicator.palette()
        palette.setColor(QPalette.ColorRole.WindowText, QColor(255, 0, 0))
        self.recording_indicator.setPalette(palette)
    
    def set_recording_inactive(self):
        palette = self.recording_indicator.palette()
        palette.setColor(QPalette.ColorRole.WindowText, QColor(128, 128, 128))
        self.recording_indicator.setPalette(palette)
    
    def update_recording_indicator(self, is_recording):
        if is_recording:
            self.set_recording_active()
        else:
            self.set_recording_inactive()

    def setup_shortcuts(self):
        # Record shortcut (Ctrl+Shift+R)
        record_shortcut = QShortcut(QKeySequence("Ctrl+Shift+R"), self)
        record_shortcut.activated.connect(self.app_instance.toggle_recording)

        # Clear context shortcut (Ctrl+Shift+C)
        clear_shortcut = QShortcut(QKeySequence("Ctrl+Shift+C"), self)
        clear_shortcut.activated.connect(self.app_instance.clear_context)

        # Paste all text shortcut (Ctrl+Shift+P)
        paste_shortcut = QShortcut(QKeySequence("Ctrl+Shift+P"), self)
        paste_shortcut.activated.connect(self.app_instance.paste_all_text)

        # Quit shortcut (Ctrl+Shift+Q)
        quit_shortcut = QShortcut(QKeySequence("Ctrl+Shift+Q"), self)
        quit_shortcut.activated.connect(self.app_instance.quit_app)

class TranscriberApp:
    def __init__(self):
        self.recording = False
        self.audio_queue = queue.Queue()
        self.text_queue = queue.Queue()
        self.context_buffer = ""
        self.audio_counter = 0
        self.last_audio_time = 0
        self.current_device = None
        
        # Initialize GUI
        self.app = QApplication(sys.argv)
        self.window = TranscriberWindow(self)
        self.window.show()
        
        # Initialize Vosk model
        try:
            print("Loading speech recognition model...")
            self.model = Model("vosk-model-small-en-us-0.15")
            self.recognizer = KaldiRecognizer(self.model, 16000)
            # Enable partial results
            self.recognizer.SetWords(True)
            self.recognizer.SetPartialWords(True)
            print("Model loaded successfully!")
        except Exception as e:
            print(f"Error loading model: {e}")
            sys.exit(1)
        
        # Check available devices
        try:
            devices = sd.query_devices()
            default_input = sd.query_devices(kind='input')
            self.current_device = default_input['index']
            self.window.update_debug_info.emit(f"Default input device: {default_input['name']}")
            print(f"Available audio devices: {devices}")
            print(f"Default input device: {default_input['name']}")
        except Exception as e:
            print(f"Error querying audio devices: {e}")
            self.window.update_debug_info.emit(f"Error querying audio devices: {e}")
        
        # Start processing threads
        self.audio_thread = threading.Thread(target=self.process_audio, daemon=True)
        self.text_thread = threading.Thread(target=self.process_text, daemon=True)
        self.audio_thread.start()
        self.text_thread.start()
        
        # Start timer for monitoring audio
        self.timer = QTimer()
        self.timer.timeout.connect(self.check_audio_activity)
        self.timer.start(1000)  # Check every second

    def change_device(self, index):
        device_id = self.window.device_selector.itemData(index)
        if device_id is not None:
            self.current_device = device_id
            print(f"Changed to device {device_id}")
            self.window.update_debug_info.emit(f"Changed to input device: {self.window.device_selector.currentText()}")
            
            # Restart recording if active
            if self.recording:
                self.stop_recording()
                self.start_recording()

    def check_audio_activity(self):
        if self.recording:
            current_time = time.time()
            if current_time - self.last_audio_time > 2:
                self.window.update_debug_info.emit(f"Audio status: No audio data received in the last 2 seconds")
            else:
                self.window.update_debug_info.emit(f"Audio status: Active (packets: {self.audio_counter})")

    def toggle_recording(self):
        self.recording = not self.recording
        self.window.update_recording_status.emit(self.recording)
        
        if self.recording:
            self.window.update_status.emit("Recording... (Press Ctrl+Shift+R to stop)")
            self.start_recording()
        else:
            self.window.update_status.emit("Stopped (Press Ctrl+Shift+R to start)")
            self.stop_recording()

    def audio_callback(self, indata, frames, time_info, status):
        if status:
            print(f"Status: {status}")
            self.window.update_debug_info.emit(f"Audio error: {status}")
        
        if self.recording:
            # Check if we have actual audio data
            if np.any(indata) and np.max(np.abs(indata)) > 0.01:  # Check if signal has reasonable amplitude
                self.audio_counter += 1
                self.last_audio_time = time.time()
                self.audio_queue.put(bytes(indata))
            else:
                # Still put empty audio for VAD to work properly
                self.audio_counter += 1
                self.last_audio_time = time.time()
                self.audio_queue.put(bytes(indata))

    def start_recording(self):
        try:
            self.audio_counter = 0
            self.last_audio_time = time.time()
            self.stream = sd.InputStream(
                device=self.current_device,
                channels=1,
                samplerate=16000,
                callback=self.audio_callback,
                dtype=np.int16,
                blocksize=4000  # Process 0.25 seconds at a time for more responsive recognition
            )
            self.stream.start()
            print("Audio stream started successfully")
            self.window.update_debug_info.emit(f"Audio stream started on device: {self.window.device_selector.currentText()}")
        except Exception as e:
            print(f"Error starting audio stream: {e}")
            self.window.update_debug_info.emit(f"Error starting audio stream: {e}")
            self.recording = False
            self.window.update_recording_status.emit(False)
            self.window.update_status.emit(f"Error: {e}")

    def stop_recording(self):
        if hasattr(self, 'stream'):
            try:
            self.stream.stop()
            self.stream.close()
                print("Audio stream stopped")
                self.window.update_debug_info.emit("Audio stream stopped")
            except Exception as e:
                print(f"Error stopping audio stream: {e}")
                self.window.update_debug_info.emit(f"Error stopping audio stream: {e}")

    def process_audio(self):
        while True:
            if not self.audio_queue.empty():
                audio_data = self.audio_queue.get()
                try:
                    # Get partial results
                    if self.recognizer.AcceptWaveform(audio_data):
                        result = json.loads(self.recognizer.Result())
                        if result.get("text", "").strip():
                            print(f"Recognized text: {result['text']}")
                            self.text_queue.put(result["text"])
                    else:
                        # Show partial results
                        partial = json.loads(self.recognizer.PartialResult())
                        if partial.get("partial", "").strip():
                            self.window.update_partial_text.emit(f"Partial: {partial['partial']}")
                except Exception as e:
                    print(f"Error processing audio: {e}")
                    self.window.update_debug_info.emit(f"Error processing audio: {e}")
            else:
                time.sleep(0.05)  # Don't hog CPU when queue is empty

    def process_text(self):
        while True:
            if not self.text_queue.empty():
                text = self.text_queue.get()
                print(f"Processing text: {text}")
                
                # Add text to context buffer
                if self.context_buffer:
                    # Add proper spacing between previous and new text
                    if not self.context_buffer.endswith(('.', '!', '?', ':', ';')):
                        self.context_buffer += " "
                    else:
                        self.context_buffer += " "
                    
                    # Capitalize first letter if previous text ended with sentence-ending punctuation
                    if self.context_buffer.rstrip()[-1] in ('.', '!', '?'):
                        text = text[0].upper() + text[1:] if text and text[0].islower() else text
                
                self.context_buffer += text
                
                # Update preview with full context
                self.window.update_preview.emit(self.context_buffer)
                
                # Copy the latest text piece to clipboard and paste
                try:
                    pyperclip.copy(text + " ")
                    pyautogui.hotkey('command', 'v') if sys.platform == 'darwin' else pyautogui.hotkey('ctrl', 'v')
                    # Clear partial text once we have a full result
                    self.window.update_partial_text.emit("Partial: ")
                except Exception as e:
                    print(f"Error pasting text: {e}")
                    self.window.update_debug_info.emit(f"Error pasting text: {e}")
            else:
                time.sleep(0.05)  # Don't hog CPU when queue is empty

    def clear_context(self):
        self.context_buffer = ""
        self.window.update_preview.emit("Context cleared")
        self.window.update_status.emit("Context cleared. Ready to start new transcription.")
        self.window.update_partial_text.emit("Partial: ")

    def paste_all_text(self):
        if self.context_buffer:
            pyperclip.copy(self.context_buffer)
            pyautogui.hotkey('command', 'v') if sys.platform == 'darwin' else pyautogui.hotkey('ctrl', 'v')
            self.window.update_status.emit("Full context pasted at cursor position")
        else:
            self.window.update_status.emit("No text to paste")

    def quit_app(self):
            self.stop_recording()
        self.app.quit()
        sys.exit(0)

    def run(self):
        return self.app.exec()

if __name__ == "__main__":
    app = TranscriberApp()
        app.run()