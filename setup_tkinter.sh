#!/bin/bash

# OpenShift Pod Log Viewer - Tkinter Setup Script
# This script helps install tkinter with Tcl/Tk 9.0.2 support

set -e

echo "🔧 OpenShift Pod Log Viewer - Tkinter Setup"
echo "============================================="

# Detect operating system
if [[ "$OSTYPE" == "darwin"* ]]; then
    OS="macOS"
elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
    OS="Linux"
elif [[ "$OSTYPE" == "msys" || "$OSTYPE" == "cygwin" ]]; then
    OS="Windows"
else
    OS="Unknown"
fi

echo "Detected OS: $OS"

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Function to test tkinter
test_tkinter() {
    echo "Testing tkinter installation..."
    python3 -c "
import sys
try:
    import tkinter as tk
    print(f'✅ tkinter is available')
    print(f'   Tk version: {tk.TkVersion}')
    print(f'   Tcl version: {tk.TclVersion}')
    
    # Test basic functionality
    root = tk.Tk()
    root.withdraw()  # Hide the window
    print('✅ tkinter basic functionality works')
    root.destroy()
    
    if tk.TkVersion >= 9.0:
        print('🎉 You have Tcl/Tk 9.0+! Excellent!')
    elif tk.TkVersion >= 8.6:
        print('✅ You have Tcl/Tk 8.6+. This will work well.')
    else:
        print('⚠️  You have an older Tcl/Tk version. Consider upgrading.')
    
except ImportError as e:
    print(f'❌ tkinter is not available: {e}')
    sys.exit(1)
"
}

# macOS setup
setup_macos() {
    echo ""
    echo "🍎 Setting up tkinter on macOS..."
    
    if ! command_exists brew; then
        echo "❌ Homebrew is not installed. Please install it first:"
        echo "   /bin/bash -c \"\$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)\""
        exit 1
    fi
    
    echo "📦 Installing Tcl/Tk via Homebrew..."
    brew install tcl-tk
    
    echo "🐍 Installing Python with tkinter support..."
    
    # Check if we should use pyenv or system python
    if command_exists pyenv; then
        echo "Found pyenv. Installing Python with tkinter support..."
        
        # Set environment variables for tkinter support
        export PATH="/opt/homebrew/opt/tcl-tk/bin:$PATH"
        export LDFLAGS="-L/opt/homebrew/opt/tcl-tk/lib $LDFLAGS"
        export CPPFLAGS="-I/opt/homebrew/opt/tcl-tk/include $CPPFLAGS"
        export PKG_CONFIG_PATH="/opt/homebrew/opt/tcl-tk/lib/pkgconfig:$PKG_CONFIG_PATH"
        
        # Install Python with tkinter
        pyenv install 3.11.0 || echo "Python 3.11.0 might already be installed"
        pyenv global 3.11.0
        
        echo "✅ Python installed with pyenv"
    else
        echo "Installing python-tk package..."
        brew install python-tk
        echo "✅ python-tk installed"
    fi
}

# Linux setup
setup_linux() {
    echo ""
    echo "🐧 Setting up tkinter on Linux..."
    
    if command_exists apt-get; then
        echo "📦 Installing tkinter via apt (Debian/Ubuntu)..."
        sudo apt-get update
        sudo apt-get install -y python3-tk tk-dev tcl-dev
        
        # Try to install newer Tcl/Tk if available
        sudo apt-get install -y tcl8.6-dev tk8.6-dev || echo "Newer Tcl/Tk not available in repos"
        
    elif command_exists yum; then
        echo "📦 Installing tkinter via yum (RHEL/CentOS)..."
        sudo yum install -y tkinter tk-devel tcl-devel
        
    elif command_exists dnf; then
        echo "📦 Installing tkinter via dnf (Fedora)..."
        sudo dnf install -y python3-tkinter tk-devel tcl-devel
        
    elif command_exists pacman; then
        echo "📦 Installing tkinter via pacman (Arch)..."
        sudo pacman -S tk
        
    else
        echo "❌ Unknown package manager. Please install tkinter manually:"
        echo "   - python3-tk or python3-tkinter package"
        echo "   - tk-dev and tcl-dev packages"
        exit 1
    fi
}

# Windows setup
setup_windows() {
    echo ""
    echo "🪟 Setting up tkinter on Windows..."
    echo "On Windows, tkinter is usually included with Python from python.org"
    echo ""
    echo "If tkinter is missing:"
    echo "1. Download Python from https://www.python.org/downloads/"
    echo "2. During installation, make sure 'tcl/tk and IDLE' is checked"
    echo "3. Or reinstall Python with all optional components"
    echo ""
    echo "Alternative: Use Windows Subsystem for Linux (WSL) and follow Linux instructions"
}

# Main setup logic
case $OS in
    "macOS")
        setup_macos
        ;;
    "Linux")
        setup_linux
        ;;
    "Windows")
        setup_windows
        ;;
    *)
        echo "❌ Unsupported operating system: $OS"
        echo "Please install tkinter manually for your system"
        exit 1
        ;;
esac

echo ""
echo "🧪 Testing installation..."
test_tkinter

echo ""
echo "🎉 Setup complete! You can now run the GUI:"
echo "   python3 log_viewer_gui.py --log-dir ./pod_logs"
echo ""
echo "💡 Tips:"
echo "   - Use 'python3 launcher.py gui' for easy launching"
echo "   - Use 'python3 launcher.py both <namespace>' to run watcher + GUI"
