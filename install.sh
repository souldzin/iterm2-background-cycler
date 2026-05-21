#!/bin/bash

# iTerm2 Background Cycler - Installation Script

set -e

echo "🎨 Installing iTerm2 Background Cycler..."
echo ""

# Check if iTerm2 is installed
if [ ! -d "/Applications/iTerm.app" ]; then
    echo "❌ Error: iTerm2 not found in /Applications/"
    echo "   Please install iTerm2 first: https://iterm2.com/"
    exit 1
fi

# Check if Python 3 is available
if ! command -v python3 &> /dev/null; then
    echo "❌ Error: Python 3 not found"
    echo "   Please install Python 3 first"
    exit 1
fi

# Install iterm2 Python package
echo "📦 Installing iterm2 Python package..."
pip3 install --user iterm2 || {
    echo "❌ Failed to install iterm2 package"
    exit 1
}

# Create AutoLaunch directory
AUTOLAUNCH_DIR="$HOME/Library/Application Support/iTerm2/Scripts/AutoLaunch"
mkdir -p "$AUTOLAUNCH_DIR"

# Copy the script
SCRIPT_PATH="$AUTOLAUNCH_DIR/background_cycler.py"
cp background_cycler.py "$SCRIPT_PATH"
chmod +x "$SCRIPT_PATH"

echo ""
echo "✅ Installation complete!"
echo ""
echo "📋 Next steps:"
echo "   1. Restart iTerm2"
echo "   2. Right-click a terminal and choose Cycler: Add Images"
echo "   3. Choose your background images"
echo ""
echo "🎮 Available commands (right-click context menu):"
echo "   • Cycler: Add Images      - Add images to current list"
echo "   • Cycler: Next Image      - Skip to next background"
echo "   • Cycler: Previous Image  - Go to previous background"
echo "   • Cycler: Clear Images    - Remove all backgrounds"
echo ""
echo "💡 Tip: Images will cycle automatically every 5 minutes by default"
