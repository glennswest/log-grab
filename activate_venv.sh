#!/bin/bash

# OpenShift Pod Log Viewer - Virtual Environment Activation
# Source this script to activate the virtual environment

# Check if we're already in the project directory
if [ ! -f "venv/bin/activate" ]; then
    echo "❌ Virtual environment not found. Please run from the project directory."
    echo "   Or create it with: python3 -m venv venv && source venv/bin/activate && pip install -r requirements.txt"
    return 1 2>/dev/null || exit 1
fi

# Activate the virtual environment
source venv/bin/activate

# Verify activation
if [ "$VIRTUAL_ENV" != "" ]; then
    echo "✅ Virtual environment activated: $(basename "$VIRTUAL_ENV")"
    echo "   Python: $(python --version)"
    
    # Test tkinter
    if python -c "import tkinter as tk; print(f'   Tkinter: Tk {tk.TkVersion}, Tcl {tk.TclVersion}')" 2>/dev/null; then
        echo "✅ Ready to run OpenShift Pod Log Viewer!"
        echo ""
        echo "Usage:"
        echo "  python pod_log_watcher.py <namespace>     # Start pod watcher"
        echo "  python log_viewer_gui.py --log-dir ./pod_logs  # Start GUI"
        echo "  python launcher.py both <namespace>       # Start both"
        echo ""
        echo "To deactivate: deactivate"
    else
        echo "⚠️  Tkinter not available - GUI will not work"
        echo "   You can still use the command-line pod watcher"
    fi
else
    echo "❌ Failed to activate virtual environment"
    return 1 2>/dev/null || exit 1
fi
