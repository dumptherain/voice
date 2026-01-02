#!/usr/bin/env python3
"""
Voice-to-Text Toggle Utility for Rocky Linux KDE (X11)
Starts/stops recording and transcribes audio using faster-whisper
"""

import os
import sys
import subprocess
import signal
import time
import json
from pathlib import Path
from datetime import datetime

# Try to import required libraries
try:
    from faster_whisper import WhisperModel
    import pyperclip
except ImportError as e:
    print(f"Error: Missing required library: {e}")
    print("Please run: pip install -r requirements.txt")
    sys.exit(1)

# Configuration file path
CONFIG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.json")

# Default configuration
DEFAULT_CONFIG = {
    "transcriptions_directory": "~/Documents/transcriptions",
    "transcriptions_file": "~/Documents/transcriptions.txt",  # Legacy: kept for backward compatibility
    "model_name": "base.en",
    "sample_rate": 16000,
    "channels": 1,
    "bit_depth": 16,
    "lock_file": "/tmp/voice_rec.lock",
    "audio_file": "/tmp/voice_capture.wav",
    "filename_options": {
        "use_datetime": True,
        "create_dated_folders": True,
        "prefix": "transcription",
        "suffix": "",
        "datetime_format": "%Y-%m-%d_%H-%M-%S",
        "date_folder_format": "%Y-%m-%d"
    }
}

def load_config():
    """Load configuration from config.json, or use defaults if not found"""
    config = DEFAULT_CONFIG.copy()
    
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r") as f:
                user_config = json.load(f)
                config.update(user_config)
        except Exception as e:
            print(f"Warning: Could not load config file: {e}. Using defaults.")
    else:
        # Create default config file
        try:
            with open(CONFIG_FILE, "w") as f:
                json.dump(DEFAULT_CONFIG, f, indent=4)
            print(f"Created default config file: {CONFIG_FILE}")
        except Exception as e:
            print(f"Warning: Could not create config file: {e}")
    
    # Expand user paths
    if "transcriptions_file" in config:
        config["transcriptions_file"] = os.path.expanduser(config["transcriptions_file"])
    if "transcriptions_directory" in config:
        config["transcriptions_directory"] = os.path.expanduser(config["transcriptions_directory"])
    # If transcriptions_directory not set, derive from transcriptions_file
    if "transcriptions_directory" not in config or not config.get("transcriptions_directory"):
        if "transcriptions_file" in config:
            config["transcriptions_directory"] = os.path.dirname(config["transcriptions_file"])
        else:
            config["transcriptions_directory"] = os.path.expanduser("~/Documents/transcriptions")
    
    return config

# Load configuration
CONFIG = load_config()

# Configuration variables (for backward compatibility and easier access)
LOCK_FILE = CONFIG["lock_file"]
AUDIO_FILE = CONFIG["audio_file"]
TRANSCRIPTIONS_DIR = CONFIG["transcriptions_directory"]
TRANSCRIPTIONS_FILE = CONFIG.get("transcriptions_file", "")  # Legacy support
MODEL_NAME = CONFIG["model_name"]
SAMPLE_RATE = CONFIG["sample_rate"]
CHANNELS = CONFIG["channels"]
BIT_DEPTH = CONFIG["bit_depth"]

# Audio recording command (prefer sox, fallback to ffmpeg)
def get_recording_command():
    """Get the appropriate recording command based on available tools"""
    # Try PulseAudio first (common on KDE)
    pulse_result = subprocess.run(["which", "pactl"], capture_output=True)
    if pulse_result.returncode == 0:
        # Check if PulseAudio is running
        pa_check = subprocess.run(["pactl", "info"], capture_output=True)
        if pa_check.returncode == 0:
            # Use PulseAudio with ffmpeg
            if subprocess.run(["which", "ffmpeg"], capture_output=True).returncode == 0:
                return [
                    "ffmpeg",
                    "-f", "pulse",
                    "-ar", str(SAMPLE_RATE),
                    "-ac", str(CHANNELS),
                    "-sample_fmt", "s16",
                    "-i", "default",  # PulseAudio default source
                    "-y",  # Overwrite output file
                    AUDIO_FILE
                ]
    
    # Check for sox (preferred for ALSA)
    if subprocess.run(["which", "sox"], capture_output=True).returncode == 0:
        # Use sox with ALSA device specification (this works reliably)
        return [
            "sox",
            "-t", "alsa",  # Specify ALSA input
            "default",     # Use default ALSA device
            "-r", str(SAMPLE_RATE),
            "-c", str(CHANNELS),
            "-b", str(BIT_DEPTH),
            "-e", "signed-integer",
            AUDIO_FILE
        ]
    
    # Fallback to ffmpeg with ALSA
    if subprocess.run(["which", "ffmpeg"], capture_output=True).returncode == 0:
        # Try to find the default ALSA capture device
        try:
            arecord_result = subprocess.run(
                ["arecord", "-l"], capture_output=True, text=True
            )
            if arecord_result.returncode == 0:
                # Use hw:1,0 as default (first capture card, first device)
                # This is more reliable than "default"
                return [
                    "ffmpeg",
                    "-f", "alsa",
                    "-ar", str(SAMPLE_RATE),
                    "-ac", str(CHANNELS),
                    "-sample_fmt", "s16",
                    "-i", "hw:1,0",  # Try first capture device explicitly
                    "-y",
                    AUDIO_FILE
                ]
        except Exception:
            pass
        
        # Last resort: use default
        return [
            "ffmpeg",
            "-f", "alsa",
            "-ar", str(SAMPLE_RATE),
            "-ac", str(CHANNELS),
            "-sample_fmt", "s16",
            "-i", "default",
            "-y",
            AUDIO_FILE
        ]
    
    raise RuntimeError("Neither sox nor ffmpeg found. Please install one of them.")


def send_notification(title, message, urgency="normal"):
    """Send desktop notification using notify-send"""
    try:
        subprocess.run(
            ["notify-send", f"--urgency={urgency}", title, message],
            check=False,
            capture_output=True
        )
    except Exception:
        pass  # Silently fail if notify-send is not available


def is_recording():
    """Check if recording is in progress by checking lock file"""
    return os.path.exists(LOCK_FILE)


def start_recording():
    """Start audio recording and create lock file"""
    if is_recording():
        print("Recording is already in progress!")
        send_notification("Voice Tool", "Recording already in progress", "low")
        return False
    
    try:
        # Get recording command
        cmd = get_recording_command()
        
        # Debug: print the command being used
        print(f"Using recording command: {' '.join(cmd)}")
        
        # Start recording process
        # Use DEVNULL for stdout/stderr to avoid blocking, but log stderr to a file for debugging
        stderr_file = "/tmp/voice_rec_stderr.log"
        try:
            with open(stderr_file, "w") as stderr_f:
                # Use shell=False but ensure process is fully detached
                # Redirect stdin to avoid issues with terminal
                process = subprocess.Popen(
                    cmd,
                    stdin=subprocess.DEVNULL,
                    stdout=subprocess.DEVNULL,
                    stderr=stderr_f,
                    preexec_fn=os.setsid,  # Create new process group
                    start_new_session=False  # setsid already does this
                )
        except Exception as e:
            print(f"Error starting recording process: {e}")
            send_notification("Voice Tool", f"Failed to start recording: {e}", "critical")
            return False
        
        # Give it a moment to start and verify it's running
        time.sleep(0.5)
        
        # Check if process is still running
        if process.poll() is not None:
            # Process already terminated - read error
            error_msg = "Unknown error"
            try:
                with open(stderr_file, "r") as f:
                    error_msg = f.read().strip()
                if not error_msg:
                    error_msg = f"Process exited with code {process.returncode}"
            except Exception:
                error_msg = f"Process exited with code {process.returncode}"
            print(f"Error: Recording process terminated immediately: {error_msg}")
            send_notification("Voice Tool", f"Recording failed: {error_msg[:50]}", "critical")
            # Clean up
            try:
                if os.path.exists(AUDIO_FILE):
                    os.remove(AUDIO_FILE)
            except Exception:
                pass
            return False
        
        # Verify the audio file is being created and growing
        initial_size = 0
        if os.path.exists(AUDIO_FILE):
            initial_size = os.path.getsize(AUDIO_FILE)
        
        # Wait a bit more and check if file is growing (proves recording is working)
        time.sleep(0.5)
        if os.path.exists(AUDIO_FILE):
            new_size = os.path.getsize(AUDIO_FILE)
            if new_size > initial_size:
                print(f"Recording verified: file growing ({initial_size} -> {new_size} bytes)")
            elif new_size == 0:
                print("Warning: Audio file exists but is empty")
        else:
            print("Warning: Audio file not created yet")
        
        # Double-check process is still running before saving lock file
        if process.poll() is not None:
            error_msg = "Process died after starting"
            try:
                with open(stderr_file, "r") as f:
                    err = f.read().strip()
                    if err:
                        error_msg = err
            except Exception:
                pass
            print(f"Error: Process terminated: {error_msg}")
            send_notification("Voice Tool", "Recording process died", "critical")
            return False
        
        # Save process info to lock file
        try:
            pgid = os.getpgid(process.pid)
        except Exception:
            pgid = None
        
        lock_data = {
            "pid": process.pid,
            "pgid": pgid,  # Process group ID
            "started_at": datetime.now().isoformat(),
            "command": cmd
        }
        
        with open(LOCK_FILE, "w") as f:
            json.dump(lock_data, f)
        
        print(f"Recording started (PID: {process.pid}, PGID: {pgid})")
        send_notification("Voice Tool", "Recording started...", "normal")
        return True
        
    except Exception as e:
        print(f"Error starting recording: {e}")
        send_notification("Voice Tool", f"Error: {e}", "critical")
        return False


def stop_recording():
    """Stop recording, transcribe audio, and save results"""
    if not is_recording():
        print("No recording in progress!")
        send_notification("Voice Tool", "No recording in progress", "low")
        return False
    
    try:
        # Read lock file to get process info
        with open(LOCK_FILE, "r") as f:
            lock_data = json.load(f)
        
        pid = lock_data["pid"]
        pgid = lock_data.get("pgid")  # Process group ID if available
        
        # Check if process is still running
        process_running = False
        try:
            os.kill(pid, 0)  # Check if process exists (doesn't kill it)
            process_running = True
        except ProcessLookupError:
            print(f"Process {pid} not found (may have already terminated)")
            # Check if file exists and has content
            if os.path.exists(AUDIO_FILE) and os.path.getsize(AUDIO_FILE) > 0:
                print("Process is gone but audio file exists with content - proceeding with transcription")
            else:
                print("Process is gone and no valid audio file found")
        
        # Kill the recording process gracefully (if still running)
        if process_running:
            try:
                # Try to kill the process group first (more reliable)
                if pgid:
                    try:
                        os.killpg(pgid, signal.SIGTERM)
                        time.sleep(0.5)  # Give it more time to flush
                        # Check if any process in the group still exists
                        try:
                            os.killpg(pgid, 0)
                            os.killpg(pgid, signal.SIGKILL)
                        except ProcessLookupError:
                            pass
                    except ProcessLookupError:
                        pass
                
                # Also try killing the specific process
                try:
                    os.kill(pid, signal.SIGTERM)
                    time.sleep(0.5)  # Give it time to flush buffers
                    # Check if process still exists
                    try:
                        os.kill(pid, 0)
                        os.kill(pid, signal.SIGKILL)
                    except ProcessLookupError:
                        pass  # Process already terminated
                except ProcessLookupError:
                    pass  # Process already terminated
            except Exception as e:
                print(f"Warning: Error killing process: {e}")
        
        # Check for recording errors
        stderr_file = "/tmp/voice_rec_stderr.log"
        if os.path.exists(stderr_file):
            try:
                with open(stderr_file, "r") as f:
                    error_output = f.read().strip()
                    if error_output:
                        print(f"Recording process errors: {error_output[:300]}")
            except Exception:
                pass
        
        # Remove lock file
        os.remove(LOCK_FILE)
        
        # Wait for the process to fully terminate and file to be written
        # Give it time to flush buffers
        time.sleep(1.0)
        
        # Check if audio file exists
        if not os.path.exists(AUDIO_FILE):
            print("Error: Audio file not found!")
            print("The recording process may have failed. Check microphone permissions and device selection.")
            # Check if process is still running (shouldn't be, but check anyway)
            try:
                os.kill(pid, 0)
                print(f"Warning: Process {pid} is still running!")
            except ProcessLookupError:
                print(f"Process {pid} has terminated.")
            send_notification("Voice Tool", "Error: Audio file not found", "critical")
            return False
        
        # Check file size (should be > 0)
        file_size = os.path.getsize(AUDIO_FILE)
        if file_size == 0:
            print("Error: Audio file is empty!")
            print("This usually means the microphone wasn't detected or accessed correctly.")
            print("Try running: arecord -l  to see available devices")
            print(f"Try testing manually: sox -t alsa default -r 16000 -c 1 -b 16 -e signed-integer /tmp/test.wav trim 0 2")
            send_notification("Voice Tool", "Error: Audio file is empty - check microphone", "critical")
            return False
        
        # Warn if file is suspiciously small (less than 1KB for a few seconds of audio)
        if file_size < 1024:
            print(f"Warning: Audio file is very small ({file_size} bytes). Recording may have failed.")
            send_notification("Voice Tool", "Warning: Audio file is very small", "normal")
        
        print("Recording stopped. Transcribing...")
        send_notification("Voice Tool", "Transcribing audio...", "normal")
        
        # Transcribe audio
        transcribed_text = transcribe_audio()
        
        if not transcribed_text:
            print("Error: Transcription failed or produced no text")
            send_notification("Voice Tool", "Transcription failed", "critical")
            return False
        
        # Save to file
        save_transcription(transcribed_text)
        
        # Copy to clipboard
        try:
            pyperclip.copy(transcribed_text)
            print(f"Text copied to clipboard: {transcribed_text[:50]}...")
        except Exception as e:
            print(f"Warning: Could not copy to clipboard: {e}")
        
        # Clean up audio file
        try:
            os.remove(AUDIO_FILE)
        except Exception:
            pass
        
        print(f"Transcription complete: {transcribed_text}")
        send_notification("Voice Tool", f"Transcribed: {transcribed_text[:50]}...", "normal")
        return True
        
    except Exception as e:
        print(f"Error stopping recording: {e}")
        send_notification("Voice Tool", f"Error: {e}", "critical")
        # Clean up lock file on error
        try:
            if os.path.exists(LOCK_FILE):
                os.remove(LOCK_FILE)
        except Exception:
            pass
        return False


def transcribe_audio():
    """Transcribe audio file using faster-whisper"""
    try:
        print(f"Loading Whisper model: {MODEL_NAME}...")
        # Use CPU with int8 quantization for efficiency
        model = WhisperModel(MODEL_NAME, device="cpu", compute_type="int8")
        
        print("Transcribing audio...")
        segments, info = model.transcribe(
            AUDIO_FILE,
            beam_size=5,
            language="en"
        )
        
        # Collect all segments
        text_parts = []
        for segment in segments:
            text_parts.append(segment.text.strip())
        
        full_text = " ".join(text_parts).strip()
        return full_text
        
    except Exception as e:
        print(f"Error during transcription: {e}")
        return None


def save_transcription(text):
    """Save transcribed text to file based on configuration options"""
    # Get filename options from config
    filename_opts = CONFIG.get("filename_options", {})
    use_datetime = filename_opts.get("use_datetime", True)
    create_dated_folders = filename_opts.get("create_dated_folders", True)
    prefix = filename_opts.get("prefix", "transcription")
    suffix = filename_opts.get("suffix", "")
    datetime_format = filename_opts.get("datetime_format", "%Y-%m-%d_%H-%M-%S")
    date_folder_format = filename_opts.get("date_folder_format", "%Y-%m-%d")
    
    # Start with base directory
    transcriptions_dir = Path(TRANSCRIPTIONS_DIR)
    
    # Create dated folder if enabled
    if create_dated_folders:
        date_folder = datetime.now().strftime(date_folder_format)
        transcriptions_dir = transcriptions_dir / date_folder
    
    # Ensure directory exists
    transcriptions_dir.mkdir(parents=True, exist_ok=True)
    
    # Build filename
    if use_datetime:
        timestamp = datetime.now().strftime(datetime_format)
        # Build filename: prefix_timestamp_suffix.txt (or prefix_timestamp.txt if no suffix)
        parts = [prefix, timestamp]
        if suffix:
            parts.append(suffix)
        filename = "_".join(parts) + ".txt"
    else:
        # Use simple filename: prefix_suffix.txt (or prefix.txt if no suffix)
        if suffix:
            filename = f"{prefix}_{suffix}.txt"
        else:
            filename = f"{prefix}.txt"
    
    filepath = transcriptions_dir / filename
    
    # Write transcription to file
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(f"Transcription: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write("=" * 80 + "\n")
        f.write(f"{text}\n")
        f.write("=" * 80 + "\n")
    
    print(f"Transcription saved to {filepath}")


def main():
    """Main toggle function"""
    if is_recording():
        stop_recording()
    else:
        start_recording()


if __name__ == "__main__":
    main()

