#!/bin/bash

# OpenShift Pod Log Viewer - GUI Launcher
# This script ensures the GUI runs with the correct Python/Tcl/Tk version

set -e

echo "🚀 Starting OpenShift Pod Log Viewer GUI..."

# Function to check if Python has tkinter with Tcl/Tk 9.0+
check_python_tkinter() {
    local python_cmd="$1"
    
    if ! command -v "$python_cmd" >/dev/null 2>&1; then
        return 1
    fi
    
    # Test tkinter availability and version
    if "$python_cmd" -c "
import sys
try:
    import tkinter as tk
    if tk.TkVersion >= 8.6:
        print(f'✅ {sys.executable}: Tk {tk.TkVersion}, Tcl {tk.TclVersion}')
        exit(0)
    else:
        print(f'⚠️  {sys.executable}: Tk {tk.TkVersion} (too old)')
        exit(1)
except ImportError:
    print(f'❌ {sys.executable}: No tkinter')
    exit(1)
" 2>/dev/null; then
        return 0
    else
        return 1
    fi
}

# Try different Python installations in order of preference
PYTHON_CANDIDATES=(
    "/opt/homebrew/bin/python3"     # Homebrew Python (macOS)
    "/usr/local/bin/python3"        # Alternative Homebrew location
    "python3.11"                    # Specific version
    "python3.12"                    # Newer version
    "python3.13"                    # Latest version
    "python3"                       # System default
)

PYTHON_CMD=""

echo "🔍 Searching for Python with Tcl/Tk 9.0+ support..."

for candidate in "${PYTHON_CANDIDATES[@]}"; do
    if check_python_tkinter "$candidate"; then
        PYTHON_CMD="$candidate"
        break
    fi
done

if [ -z "$PYTHON_CMD" ]; then
    echo ""
    echo "❌ No suitable Python installation found with tkinter support."
    echo ""
    echo "Please run the setup script first:"
    echo "  ./setup_tkinter.sh"
    echo ""
    echo "Or install manually:"
    echo "  brew install python-tk  # macOS"
    echo "  sudo apt-get install python3-tk  # Ubuntu/Debian"
    exit 1
fi

echo ""
echo "🎯 Using: $PYTHON_CMD"

# Install dependencies if needed
if ! "$PYTHON_CMD" -c "import kubernetes" >/dev/null 2>&1; then
    echo "📦 Installing Python dependencies..."
    "$PYTHON_CMD" -m pip install -r requirements.txt
fi

# Launch the GUI
echo "🖥️  Launching GUI..."
exec "$PYTHON_CMD" log_viewer_gui.py "$@"
