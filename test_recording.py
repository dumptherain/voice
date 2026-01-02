#!/usr/bin/env python3
"""Test script to diagnose recording issues"""

import subprocess
import time
import os
import signal

AUDIO_FILE = "/tmp/test_voice_capture.wav"
cmd = ["sox", "-t", "alsa", "default", "-r", "16000", "-c", "1", "-b", "16", "-e", "signed-integer", AUDIO_FILE]

print(f"Testing command: {' '.join(cmd)}")
print(f"Output file: {AUDIO_FILE}")

# Remove old file
if os.path.exists(AUDIO_FILE):
    os.remove(AUDIO_FILE)

stderr_file = "/tmp/test_rec_stderr.log"
print(f"Starting process...")

with open(stderr_file, "w") as stderr_f:
    process = subprocess.Popen(
        cmd,
        stdout=subprocess.DEVNULL,
        stderr=stderr_f,
        preexec_fn=os.setsid
    )

print(f"Process started with PID: {process.pid}")

# Check multiple times
for i in range(5):
    time.sleep(1)
    status = process.poll()
    file_exists = os.path.exists(AUDIO_FILE)
    file_size = os.path.getsize(AUDIO_FILE) if file_exists else 0
    
    print(f"After {i+1}s: Process status={status}, File exists={file_exists}, Size={file_size} bytes")
    
    if status is not None:
        print(f"Process terminated with code: {status}")
        # Read stderr
        try:
            with open(stderr_file, "r") as f:
                error = f.read()
                if error:
                    print(f"Stderr: {error}")
        except Exception as e:
            print(f"Could not read stderr: {e}")
        break

# Kill if still running
if process.poll() is None:
    print("Killing process...")
    try:
        os.killpg(os.getpgid(process.pid), signal.SIGTERM)
        time.sleep(0.5)
        os.killpg(os.getpgid(process.pid), signal.SIGKILL)
    except Exception as e:
        print(f"Error killing: {e}")

print(f"\nFinal file size: {os.path.getsize(AUDIO_FILE) if os.path.exists(AUDIO_FILE) else 0} bytes")

