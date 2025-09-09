#!/bin/bash

# OpenShift Pod Log Viewer - GUI Launcher with Virtual Environment
# This script uses the virtual environment for consistent dependencies

set -e

echo "🚀 Starting OpenShift Pod Log Viewer GUI..."

# Check if we're in the project directory
if [ ! -f "log_viewer_gui.py" ]; then
    echo "❌ Please run this script from the project directory"
    exit 1
fi

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv venv
    
    echo "📥 Installing dependencies..."
    source venv/bin/activate
    pip install -r requirements.txt
    deactivate
fi

# Activate virtual environment
echo "🔧 Activating virtual environment..."
source venv/bin/activate

# Verify tkinter is available
echo "🧪 Testing tkinter..."
if ! python -c "import tkinter as tk; print(f'✅ Tk {tk.TkVersion}, Tcl {tk.TclVersion}')" 2>/dev/null; then
    echo "❌ Tkinter not available in virtual environment"
    echo ""
    echo "This might be because your system Python doesn't have tkinter support."
    echo "Try one of these solutions:"
    echo ""
    echo "1. Install tkinter for your system Python:"
    echo "   macOS: brew install python-tk"
    echo "   Ubuntu/Debian: sudo apt-get install python3-tk"
    echo ""
    echo "2. Use a different Python installation:"
    echo "   rm -rf venv"
    echo "   /opt/homebrew/bin/python3 -m venv venv  # Use Homebrew Python"
    echo "   source venv/bin/activate"
    echo "   pip install -r requirements.txt"
    echo ""
    echo "3. Run the setup script:"
    echo "   ./setup_tkinter.sh"
    
    deactivate
    exit 1
fi

# Check if kubernetes is installed
if ! python -c "import kubernetes" >/dev/null 2>&1; then
    echo "📦 Installing missing dependencies..."
    pip install -r requirements.txt
fi

# Launch the GUI
echo "🖥️  Launching GUI..."
echo "   Virtual environment: $VIRTUAL_ENV"
echo "   Python: $(python --version)"
echo ""

exec python log_viewer_gui.py "$@"
