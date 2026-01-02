#!/bin/bash
# Wrapper script for voice-to-text toggle utility
# Activates virtual environment and runs the Python script
# Suitable for keyboard shortcuts

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Activate virtual environment and run the script
cd "$SCRIPT_DIR" || exit 1
source venv/bin/activate
exec python3 voice_tool.py

