#!/bin/bash
# Setup script for Voice-to-Text utility on Rocky Linux
# Installs system dependencies and sets up Python virtual environment

set -e  # Exit on error

echo "=== Voice-to-Text Utility Setup for Rocky Linux ==="
echo ""

# Check if running as root (we'll use sudo for dnf)
if [ "$EUID" -eq 0 ]; then
    SUDO=""
else
    SUDO="sudo"
    echo "Note: This script will use sudo for system package installation"
fi

# Install system dependencies
echo "Step 1: Installing system dependencies..."
$SUDO dnf install -y \
    python3 \
    python3-pip \
    sox \
    ffmpeg \
    xclip \
    libnotify \
    alsa-utils

echo ""
echo "Step 2: Creating Python virtual environment..."
# Create venv in the current directory
python3 -m venv venv

echo ""
echo "Step 3: Activating virtual environment and installing Python packages..."
source venv/bin/activate

# Upgrade pip
pip install --upgrade pip

# Install Python dependencies
pip install -r requirements.txt

echo ""
echo "Step 4: Making scripts executable..."
chmod +x voice_tool.py
chmod +x voice_toggle.sh

# Get the current directory for instructions
CURRENT_DIR="$(pwd)"

echo ""
echo "=== Setup Complete! ==="
echo ""
echo "To use the voice tool:"
echo ""
echo "Option 1: Use the wrapper script (recommended for keyboard shortcuts):"
echo "  $CURRENT_DIR/voice_toggle.sh"
echo ""
echo "Option 2: Manual activation:"
echo "  1. Activate the virtual environment: source venv/bin/activate"
echo "  2. Run the script: ./voice_tool.py"
echo ""
echo "To set up a keyboard shortcut in KDE:"
echo "  1. Go to System Settings > Shortcuts > Custom Shortcuts"
echo "  2. Add a new command shortcut"
echo "  3. Set the command to: $CURRENT_DIR/voice_toggle.sh"
echo "  4. Assign your preferred key combination"
echo ""
echo "Note: The first run will download the Whisper model (~150MB for base.en)"

