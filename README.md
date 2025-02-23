# Quick Transcriber

A real-time speech-to-text application that transcribes your voice and types it where your cursor is located.

## Features

- Real-time voice transcription
- Local processing (no internet required)
- Automatic text insertion at cursor position
- Always-on-top window for easy monitoring
- Global keyboard shortcuts for control
- Cross-platform compatibility (Windows, macOS, Linux)

## System Requirements

- Python 3.7 or higher
- Working microphone
- macOS users: Must grant accessibility permissions to Terminal/IDE
  (System Preferences > Security & Privacy > Privacy > Accessibility)

## Setup Instructions

1. Create and activate a virtual environment:

   ```bash
   # Create virtual environment
   python -m venv venv

   # Activate on macOS/Linux
   source venv/bin/activate

   # Activate on Windows
   venv\Scripts\activate
   ```

2. Install required packages:

   ```bash
   pip install vosk sounddevice numpy PyQt6 pyautogui
   ```

3. Download and extract the Vosk speech recognition model:

   ```bash
   wget https://alphacephei.com/vosk/models/vosk-model-small-en-us-0.15.zip
   unzip vosk-model-small-en-us-0.15.zip
   ```

   If wget is not available, download manually from:
   https://alphacephei.com/vosk/models/vosk-model-small-en-us-0.15.zip

## Usage

1. Launch the application:

   ```bash
   python transcriber.py
   ```

2. A small monitoring window will appear and stay on top of other windows

3. Control the application using global shortcuts:
   - `Ctrl+Shift+R`: Start/stop recording
   - `Ctrl+Shift+Q`: Quit the application

4. Recording workflow:
   - Position your cursor where you want the text to appear
   - Press `Ctrl+Shift+R` to start recording
   - Speak clearly into your microphone
   - Watch the transcribed text appear in the preview window
   - Text will be automatically typed at the cursor location
   - Press `Ctrl+Shift+R` again to stop recording

## Troubleshooting

### macOS Process Trust Issues
If you encounter a "Process is not trusted" error:
1. Open System Preferences
2. Navigate to Security & Privacy > Privacy > Accessibility
3. Add your Terminal application or IDE to the allowed applications

### No Audio Input
If the application isn't detecting your microphone:
1. Verify your microphone is properly connected
2. Check microphone permissions in system settings
3. Confirm the correct input device is selected in system sound settings
4. Try using a different microphone

### Poor Transcription Quality
To improve transcription accuracy:
1. Speak clearly and at a moderate pace
2. Minimize background noise
3. Use a high-quality microphone
4. Consider using a larger Vosk model (available at https://alphacephei.com/vosk/models)

## Technical Notes

- Built using the Vosk speech recognition engine
- All processing happens locally on your machine
- Uses PyQt6 for the GUI interface
- Employs pyautogui for cursor control and text insertion
- Requires accessibility permissions for automated text entry

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request