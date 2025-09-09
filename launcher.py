#!/usr/bin/env python3
"""
OpenShift Pod Log Tools Launcher

A simple launcher script that can start either the pod watcher or the GUI viewer.
"""

import sys
import argparse
import subprocess
from pathlib import Path


def main():
    """Main launcher function."""
    parser = argparse.ArgumentParser(
        description="Launch OpenShift Pod Log Tools",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python launcher.py watcher my-project          # Start pod watcher
  python launcher.py gui                         # Start GUI viewer
  python launcher.py gui --log-dir /path/logs    # Start GUI with custom directory
  python launcher.py both my-project             # Start both watcher and GUI
        """
    )
    
    parser.add_argument(
        'mode',
        choices=['watcher', 'gui', 'both'],
        help='What to launch: watcher, gui, or both'
    )
    
    parser.add_argument(
        'namespace',
        nargs='?',
        help='OpenShift namespace/project (required for watcher mode)'
    )
    
    parser.add_argument(
        '--log-dir',
        default='./pod_logs',
        help='Directory for pod logs (default: ./pod_logs)'
    )
    
    parser.add_argument(
        '--kubeconfig',
        help='Path to kubeconfig file'
    )
    
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Enable verbose logging for watcher'
    )
    
    args = parser.parse_args()
    
    # Get script directory
    script_dir = Path(__file__).parent
    
    # Validate arguments
    if args.mode in ['watcher', 'both'] and not args.namespace:
        parser.error("namespace is required for watcher mode")
    
    try:
        if args.mode == 'watcher':
            launch_watcher(script_dir, args)
        elif args.mode == 'gui':
            launch_gui(script_dir, args)
        elif args.mode == 'both':
            launch_both(script_dir, args)
    
    except KeyboardInterrupt:
        print("\nShutting down...")
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


def launch_watcher(script_dir: Path, args):
    """Launch the pod watcher."""
    cmd = [sys.executable, str(script_dir / 'pod_log_watcher.py'), args.namespace]
    
    if args.log_dir != './pod_logs':
        cmd.extend(['--log-dir', args.log_dir])
    
    if args.kubeconfig:
        cmd.extend(['--kubeconfig', args.kubeconfig])
    
    if args.verbose:
        cmd.append('--verbose')
    
    print(f"Starting pod watcher for namespace: {args.namespace}")
    print(f"Command: {' '.join(cmd)}")
    
    subprocess.run(cmd)


def launch_gui(script_dir: Path, args):
    """Launch the GUI viewer."""
    # Check if we have a virtual environment
    venv_python = script_dir / 'venv' / 'bin' / 'python'
    
    if venv_python.exists():
        # Use virtual environment Python
        python_cmd = str(venv_python)
        print(f"Using virtual environment Python: {python_cmd}")
    else:
        # Fallback to system Python detection
        python_candidates = [
            "/opt/homebrew/bin/python3",  # Homebrew Python (macOS)
            "/usr/local/bin/python3",     # Alternative location
            sys.executable                # Current Python
        ]
        
        python_cmd = sys.executable
        for candidate in python_candidates:
            try:
                import subprocess
                result = subprocess.run([candidate, "-c", "import tkinter"], 
                                      capture_output=True, timeout=5)
                if result.returncode == 0:
                    python_cmd = candidate
                    break
            except (FileNotFoundError, subprocess.TimeoutExpired):
                continue
        
        print(f"Using system Python: {python_cmd}")
    
    cmd = [python_cmd, str(script_dir / 'log_viewer_gui.py')]
    
    if args.log_dir != './pod_logs':
        cmd.extend(['--log-dir', args.log_dir])
    
    print(f"Starting GUI log viewer")
    print(f"Log directory: {args.log_dir}")
    print(f"Command: {' '.join(cmd)}")
    
    subprocess.run(cmd)


def launch_both(script_dir: Path, args):
    """Launch both watcher and GUI."""
    import threading
    import time
    
    print(f"Starting both pod watcher and GUI viewer")
    print(f"Namespace: {args.namespace}")
    print(f"Log directory: {args.log_dir}")
    
    # Start watcher in background thread
    def run_watcher():
        watcher_cmd = [sys.executable, str(script_dir / 'pod_log_watcher.py'), args.namespace]
        
        if args.log_dir != './pod_logs':
            watcher_cmd.extend(['--log-dir', args.log_dir])
        
        if args.kubeconfig:
            watcher_cmd.extend(['--kubeconfig', args.kubeconfig])
        
        if args.verbose:
            watcher_cmd.append('--verbose')
        
        subprocess.run(watcher_cmd)
    
    watcher_thread = threading.Thread(target=run_watcher, daemon=True)
    watcher_thread.start()
    
    # Give watcher a moment to start
    time.sleep(2)
    
    # Start GUI in main thread
    gui_cmd = [sys.executable, str(script_dir / 'log_viewer_gui.py')]
    
    if args.log_dir != './pod_logs':
        gui_cmd.extend(['--log-dir', args.log_dir])
    
    subprocess.run(gui_cmd)


if __name__ == '__main__':
    main()
