# Voice-to-Text Toggle Utility

A Python-based voice-to-text utility optimized for Rocky Linux KDE (X11) that acts as a toggle for recording and transcribing audio. Perfect for quick voice notes, meeting transcriptions, or any scenario where you need hands-free text input.

## Features

- **Toggle Recording**: First run starts recording, second run stops and transcribes
- **Automatic Transcription**: Uses faster-whisper with CPU/Int8 quantization for efficient processing
- **Clipboard Integration**: Automatically copies transcribed text to X11 clipboard
- **Flexible File Organization**: Configurable file naming with date/time stamps and optional dated folders
- **Desktop Notifications**: Shows KDE notifications when recording starts/stops
- **Keyboard Shortcut Ready**: Designed to work seamlessly with KDE custom shortcuts

## Configuration

The tool uses `config.json` in the project directory to customize settings. The default location is created on first run.

### Configurable Options

- **transcriptions_directory**: Base directory where transcriptions are saved (default: `~/Documents/transcriptions`)
- **model_name**: Whisper model to use - `base.en` (faster) or `small` (more accurate)
- **sample_rate**: Audio sample rate (default: 16000)
- **channels**: Audio channels (default: 1 for mono)
- **bit_depth**: Audio bit depth (default: 16)
- **lock_file**: Lock file location (default: `/tmp/voice_rec.lock`)
- **audio_file**: Temporary audio file location (default: `/tmp/voice_capture.wav`)
- **filename_options**: Object containing file naming options:
  - **use_datetime**: Whether to include date/time in filename (default: `true`)
  - **create_dated_folders**: Whether to create a folder for each day (default: `true`)
  - **prefix**: Prefix for filenames (default: `"transcription"`)
  - **suffix**: Suffix for filenames (default: `""` - empty)
  - **datetime_format**: Format string for date/time in filename (default: `"%Y-%m-%d_%H-%M-%S"`)
  - **date_folder_format**: Format string for dated folder names (default: `"%Y-%m-%d"`)

### Example config.json

```json
{
    "transcriptions_directory": "~/Documents/transcriptions",
    "model_name": "base.en",
    "sample_rate": 16000,
    "channels": 1,
    "bit_depth": 16,
    "lock_file": "/tmp/voice_rec.lock",
    "audio_file": "/tmp/voice_capture.wav",
    "filename_options": {
        "use_datetime": true,
        "create_dated_folders": true,
        "prefix": "transcription",
        "suffix": "",
        "datetime_format": "%Y-%m-%d_%H-%M-%S",
        "date_folder_format": "%Y-%m-%d"
    }
}
```

### Filename Examples

With default settings:
- Files saved to: `~/Documents/transcriptions/2026-01-02/transcription_2026-01-02_20-30-45.txt`

With `"suffix": "meeting"`:
- Files saved to: `~/Documents/transcriptions/2026-01-02/transcription_2026-01-02_20-30-45_meeting.txt`

With `"create_dated_folders": false`:
- Files saved to: `~/Documents/transcriptions/transcription_2026-01-02_20-30-45.txt`

With `"use_datetime": false` and `"suffix": "notes"`:
- Files saved to: `~/Documents/transcriptions/transcription_notes.txt` (will overwrite if multiple per day)

## Installation

### Prerequisites

- Rocky Linux (or compatible RHEL-based distribution)
- KDE Desktop Environment (X11)
- Python 3.9 or higher
- sudo/root access for package installation

### Setup

1. Clone or download this repository:
   ```bash
   cd ~/voice  # or your preferred directory
   ```

2. Run the setup script:
   ```bash
   chmod +x setup_rocky.sh
   ./setup_rocky.sh
   ```

3. The script will:
   - Install system dependencies (sox, ffmpeg, xclip, libnotify, alsa-utils)
   - Create a Python virtual environment
   - Install Python dependencies (faster-whisper, pyperclip)
   - Create a default `config.json` file

**Note**: The first transcription will download the Whisper model (~150MB for `base.en`). This is a one-time download.

## Usage

### Option 1: Wrapper Script (Recommended for Keyboard Shortcuts)

```bash
./voice_toggle.sh
```

### Option 2: Manual Activation

```bash
source venv/bin/activate
./voice_tool.py
```

### Setting Up Keyboard Shortcuts in KDE

1. Go to **System Settings > Shortcuts > Custom Shortcuts**
2. Add a new command shortcut
3. Set the command to: `/home/mini2/voice/voice_toggle.sh` (or your path)
4. Assign your preferred key combination (e.g., `Ctrl+Shift+V`)

## How It Works

1. **First Run**: 
   - Starts recording audio from the default microphone
   - Creates a lock file to track recording state
   - Shows a desktop notification
   - Process runs in background until stopped

2. **Second Run**: 
   - Stops the recording process
   - Transcribes the audio using faster-whisper
   - Saves transcription to a file (with date/time in filename)
   - Copies text to X11 clipboard
   - Shows a desktop notification with preview

The tool uses a lock file (`/tmp/voice_rec.lock`) to track recording state, allowing you to toggle recording on/off with the same command.

## Troubleshooting

### Empty Audio Files

If you get empty audio files:
- Check microphone permissions and ensure it's not muted
- Verify microphone is working: `arecord -l` (lists available devices)
- Test recording manually: `sox -t alsa default -r 16000 -c 1 -b 16 -e signed-integer /tmp/test.wav trim 0 2`
- Check if another application is using the microphone
- Verify ALSA/PulseAudio configuration

### Process Not Found Error

If you see "Process not found (may have already terminated)":
- The recording process may have crashed
- Check `/tmp/voice_rec_stderr.log` for error messages
- Try running `./voice_toggle.sh` again to start fresh
- Ensure sox/ffmpeg is properly installed

### Model Download Issues

- The first transcription downloads the Whisper model (~150MB for `base.en`)
- Models are cached in `~/.cache/huggingface/`
- If download fails, check internet connection
- You can manually download models using the huggingface-hub CLI

### Audio Device Issues

- Multiple audio devices: The script uses the ALSA "default" device
- To use a specific device, you may need to configure ALSA defaults
- Check available devices: `arecord -l`
- Test specific device: `sox -t alsa hw:1,0 ...` (replace with your device)

## Project Structure

```
voice/
├── voice_tool.py          # Main Python script
├── voice_toggle.sh        # Wrapper script for keyboard shortcuts
├── config.json            # Configuration file (created on first run)
├── requirements.txt       # Python dependencies
├── setup_rocky.sh         # Setup script for Rocky Linux
├── test_recording.py      # Diagnostic script for testing audio recording
├── README.md              # This file
└── .gitignore            # Git ignore file
```

## License

This project is provided as-is for personal use.

## Contributing

Feel free to submit issues or pull requests for improvements!

