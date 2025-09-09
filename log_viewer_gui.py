#!/usr/bin/env python3
"""
OpenShift Pod Log Viewer GUI

A Tkinter-based graphical user interface for viewing and navigating pod logs
collected by the OpenShift Pod Log Watcher.

Features:
- Browse logs by project/namespace
- Navigate multiple pods per project
- View multiple log files per pod
- Search and filter functionality
- Real-time log refresh
- Syntax highlighting for log levels
"""

import os
import sys
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import threading
import time
from datetime import datetime
from pathlib import Path
import re
from typing import Dict, List, Optional, Tuple
import json


class LogViewerGUI:
    """Main GUI application for viewing pod logs."""
    
    def __init__(self, log_directory: str = "./pod_logs"):
        """
        Initialize the log viewer GUI.
        
        Args:
            log_directory: Directory containing pod log files
        """
        self.log_directory = Path(log_directory)
        self.current_log_file = None
        self.auto_refresh = False
        self.refresh_interval = 5  # seconds
        self.search_results = []
        self.current_search_index = 0
        
        # Create main window
        self.root = tk.Tk()
        self.root.title("OpenShift Pod Log Viewer")
        self.root.geometry("1400x900")
        self.root.minsize(800, 600)
        
        # Configure styles
        self.setup_styles()
        
        # Create GUI components
        self.create_widgets()
        
        # Load initial data
        self.refresh_log_list()
        
        # Bind events
        self.bind_events()
    
    def setup_styles(self):
        """Configure ttk styles for better appearance."""
        style = ttk.Style()
        
        # Configure treeview style
        style.configure("Treeview", rowheight=25)
        style.configure("Treeview.Heading", font=('Arial', 10, 'bold'))
        
        # Configure button styles
        style.configure("Action.TButton", font=('Arial', 9))
        
        # Configure treeview tags for watcher logs
        self.root.after(100, self.setup_tree_tags)
    
    def setup_tree_tags(self):
        """Setup treeview tags for different log types."""
        if hasattr(self, 'log_tree'):
            # Configure watcher log styling
            self.log_tree.tag_configure('watcher', background='#2d3748', foreground='#90cdf4')
    
    def create_widgets(self):
        """Create and layout all GUI widgets."""
        # Create main paned window
        main_paned = ttk.PanedWindow(self.root, orient=tk.HORIZONTAL)
        main_paned.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Left panel for navigation
        left_frame = ttk.Frame(main_paned, width=400)
        main_paned.add(left_frame, weight=1)
        
        # Right panel for log content
        right_frame = ttk.Frame(main_paned)
        main_paned.add(right_frame, weight=3)
        
        self.create_navigation_panel(left_frame)
        self.create_log_panel(right_frame)
        self.create_status_bar()
    
    def create_navigation_panel(self, parent):
        """Create the left navigation panel."""
        # Navigation header
        nav_header = ttk.LabelFrame(parent, text="Log Navigation", padding=10)
        nav_header.pack(fill=tk.X, padx=5, pady=5)
        
        # Refresh button
        refresh_btn = ttk.Button(
            nav_header, 
            text="🔄 Refresh", 
            command=self.refresh_log_list,
            style="Action.TButton"
        )
        refresh_btn.pack(side=tk.LEFT)
        
        # Auto-refresh checkbox
        self.auto_refresh_var = tk.BooleanVar()
        auto_refresh_cb = ttk.Checkbutton(
            nav_header,
            text="Auto-refresh",
            variable=self.auto_refresh_var,
            command=self.toggle_auto_refresh
        )
        auto_refresh_cb.pack(side=tk.LEFT, padx=(10, 0))
        
        # Log directory button
        dir_btn = ttk.Button(
            nav_header,
            text="📁 Change Directory",
            command=self.change_log_directory,
            style="Action.TButton"
        )
        dir_btn.pack(side=tk.RIGHT)
        
        # Project/Pod tree
        tree_frame = ttk.LabelFrame(parent, text="Projects & Pods", padding=5)
        tree_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Create treeview with scrollbars
        tree_container = ttk.Frame(tree_frame)
        tree_container.pack(fill=tk.BOTH, expand=True)
        
        self.log_tree = ttk.Treeview(tree_container, columns=('size', 'modified'), show='tree headings')
        self.log_tree.heading('#0', text='Pod / Log File', anchor=tk.W)
        self.log_tree.heading('size', text='Size', anchor=tk.E)
        self.log_tree.heading('modified', text='Modified', anchor=tk.W)
        
        self.log_tree.column('#0', width=250, minwidth=200)
        self.log_tree.column('size', width=80, minwidth=60)
        self.log_tree.column('modified', width=120, minwidth=100)
        
        # Scrollbars for treeview
        tree_v_scroll = ttk.Scrollbar(tree_container, orient=tk.VERTICAL, command=self.log_tree.yview)
        tree_h_scroll = ttk.Scrollbar(tree_container, orient=tk.HORIZONTAL, command=self.log_tree.xview)
        self.log_tree.configure(yscrollcommand=tree_v_scroll.set, xscrollcommand=tree_h_scroll.set)
        
        self.log_tree.grid(row=0, column=0, sticky='nsew')
        tree_v_scroll.grid(row=0, column=1, sticky='ns')
        tree_h_scroll.grid(row=1, column=0, sticky='ew')
        
        tree_container.grid_rowconfigure(0, weight=1)
        tree_container.grid_columnconfigure(0, weight=1)
        
        # Filter frame
        filter_frame = ttk.LabelFrame(parent, text="Filter", padding=5)
        filter_frame.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Label(filter_frame, text="Pod name:").pack(anchor=tk.W)
        self.filter_var = tk.StringVar()
        self.filter_var.trace('w', self.on_filter_change)
        filter_entry = ttk.Entry(filter_frame, textvariable=self.filter_var)
        filter_entry.pack(fill=tk.X, pady=(2, 0))
    
    def create_log_panel(self, parent):
        """Create the right log viewing panel."""
        # Log header
        log_header = ttk.LabelFrame(parent, text="Log Content", padding=5)
        log_header.pack(fill=tk.X, padx=5, pady=5)
        
        # Current file label
        self.current_file_var = tk.StringVar(value="No log file selected")
        current_file_label = ttk.Label(log_header, textvariable=self.current_file_var, font=('Arial', 10, 'bold'))
        current_file_label.pack(side=tk.LEFT)
        
        # Search frame
        search_frame = ttk.Frame(log_header)
        search_frame.pack(side=tk.RIGHT)
        
        ttk.Label(search_frame, text="Search:").pack(side=tk.LEFT)
        self.search_var = tk.StringVar()
        search_entry = ttk.Entry(search_frame, textvariable=self.search_var, width=20)
        search_entry.pack(side=tk.LEFT, padx=(5, 0))
        search_entry.bind('<Return>', self.search_logs)
        
        search_btn = ttk.Button(search_frame, text="🔍", command=self.search_logs, width=3)
        search_btn.pack(side=tk.LEFT, padx=(2, 0))
        
        # Navigation buttons for search results
        self.prev_btn = ttk.Button(search_frame, text="↑", command=self.prev_search_result, width=3, state=tk.DISABLED)
        self.prev_btn.pack(side=tk.LEFT, padx=(5, 0))
        
        self.next_btn = ttk.Button(search_frame, text="↓", command=self.next_search_result, width=3, state=tk.DISABLED)
        self.next_btn.pack(side=tk.LEFT, padx=(2, 0))
        
        self.search_info_var = tk.StringVar()
        search_info_label = ttk.Label(search_frame, textvariable=self.search_info_var, font=('Arial', 8))
        search_info_label.pack(side=tk.LEFT, padx=(5, 0))
        
        # Log content area
        content_frame = ttk.Frame(parent)
        content_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Create text widget with scrollbars
        self.log_text = tk.Text(
            content_frame,
            wrap=tk.NONE,
            font=('Consolas', 10),
            bg='#1e1e1e',
            fg='#d4d4d4',
            insertbackground='white',
            selectbackground='#264f78'
        )
        
        # Scrollbars for text widget
        text_v_scroll = ttk.Scrollbar(content_frame, orient=tk.VERTICAL, command=self.log_text.yview)
        text_h_scroll = ttk.Scrollbar(content_frame, orient=tk.HORIZONTAL, command=self.log_text.xview)
        self.log_text.configure(yscrollcommand=text_v_scroll.set, xscrollcommand=text_h_scroll.set)
        
        self.log_text.grid(row=0, column=0, sticky='nsew')
        text_v_scroll.grid(row=0, column=1, sticky='ns')
        text_h_scroll.grid(row=1, column=0, sticky='ew')
        
        content_frame.grid_rowconfigure(0, weight=1)
        content_frame.grid_columnconfigure(0, weight=1)
        
        # Configure text tags for syntax highlighting
        self.setup_text_tags()
    
    def create_status_bar(self):
        """Create the bottom status bar."""
        self.status_bar = ttk.Frame(self.root)
        self.status_bar.pack(fill=tk.X, side=tk.BOTTOM)
        
        self.status_var = tk.StringVar(value="Ready")
        status_label = ttk.Label(self.status_bar, textvariable=self.status_var)
        status_label.pack(side=tk.LEFT, padx=5, pady=2)
        
        # Log directory info
        self.log_dir_var = tk.StringVar(value=f"Log directory: {self.log_directory}")
        log_dir_label = ttk.Label(self.status_bar, textvariable=self.log_dir_var, font=('Arial', 8))
        log_dir_label.pack(side=tk.RIGHT, padx=5, pady=2)
    
    def setup_text_tags(self):
        """Configure text tags for log syntax highlighting."""
        # Error messages (red)
        self.log_text.tag_configure('error', foreground='#f44747')
        
        # Warning messages (yellow)
        self.log_text.tag_configure('warning', foreground='#ffcc02')
        
        # Info messages (blue)
        self.log_text.tag_configure('info', foreground='#75beff')
        
        # Debug messages (gray)
        self.log_text.tag_configure('debug', foreground='#9cdcfe')
        
        # Timestamps (green)
        self.log_text.tag_configure('timestamp', foreground='#4ec9b0')
        
        # Search highlights (yellow background)
        self.log_text.tag_configure('search_highlight', background='#ffff00', foreground='#000000')
        
        # Watcher log specific tags
        self.log_text.tag_configure('watcher_info', foreground='#4fc3f7')
        self.log_text.tag_configure('watcher_error', foreground='#ef5350')
        self.log_text.tag_configure('watcher_warning', foreground='#ffb74d')
        self.log_text.tag_configure('watcher_success', foreground='#66bb6a')
    
    def bind_events(self):
        """Bind GUI events."""
        self.log_tree.bind('<<TreeviewSelect>>', self.on_tree_select)
        self.log_tree.bind('<Double-1>', self.on_tree_double_click)
        self.root.bind('<Control-f>', lambda e: self.search_var.get() or self.focus_search())
        self.root.bind('<F5>', lambda e: self.refresh_log_list())
    
    def focus_search(self):
        """Focus the search entry widget."""
        for widget in self.root.winfo_children():
            if isinstance(widget, ttk.PanedWindow):
                for pane in widget.panes():
                    frame = self.root.nametowidget(pane)
                    for child in frame.winfo_children():
                        if isinstance(child, ttk.LabelFrame) and "Log Content" in str(child['text']):
                            for subchild in child.winfo_children():
                                if isinstance(subchild, ttk.Frame):
                                    for entry in subchild.winfo_children():
                                        if isinstance(entry, ttk.Entry):
                                            entry.focus_set()
                                            return
    
    def refresh_log_list(self):
        """Refresh the list of log files in the tree view."""
        self.status_var.set("Refreshing log list...")
        
        # Clear existing items
        for item in self.log_tree.get_children():
            self.log_tree.delete(item)
        
        if not self.log_directory.exists():
            self.status_var.set("Log directory does not exist")
            return
        
        # Group log files by pod name
        pod_logs = self.group_logs_by_pod()
        
        # Add items to tree - watcher log first, then sorted pods
        watcher_logs = {}
        regular_pods = {}
        
        for pod_name, log_files in pod_logs.items():
            if pod_name == "🔍 Pod Log Watcher":
                watcher_logs[pod_name] = log_files
            else:
                regular_pods[pod_name] = log_files
        
        # Add watcher logs first
        for pod_name, log_files in watcher_logs.items():
            pod_id = self.log_tree.insert('', 'end', text=pod_name, values=('', ''), tags=('pod', 'watcher'))
            
            for log_file in sorted(log_files, key=lambda x: x.stat().st_mtime, reverse=True):
                file_size = self.format_file_size(log_file.stat().st_size)
                file_time = datetime.fromtimestamp(log_file.stat().st_mtime).strftime('%Y-%m-%d %H:%M')
                
                self.log_tree.insert(
                    pod_id, 'end',
                    text=log_file.name,
                    values=(file_size, file_time),
                    tags=('logfile', 'watcher')
                )
        
        # Add regular pods
        for pod_name, log_files in sorted(regular_pods.items()):
            pod_id = self.log_tree.insert('', 'end', text=pod_name, values=('', ''), tags=('pod',))
            
            for log_file in sorted(log_files, key=lambda x: x.stat().st_mtime, reverse=True):
                file_size = self.format_file_size(log_file.stat().st_size)
                file_time = datetime.fromtimestamp(log_file.stat().st_mtime).strftime('%Y-%m-%d %H:%M')
                
                self.log_tree.insert(
                    pod_id, 'end',
                    text=log_file.name,
                    values=(file_size, file_time),
                    tags=('logfile',)
                )
        
        # Expand all pod nodes
        for item in self.log_tree.get_children():
            self.log_tree.item(item, open=True)
        
        total_files = sum(len(files) for files in pod_logs.values())
        self.status_var.set(f"Found {len(pod_logs)} pods with {total_files} log files")
    
    def group_logs_by_pod(self) -> Dict[str, List[Path]]:
        """Group log files by pod name."""
        pod_logs = {}
        
        # Get all .log files
        for log_file in self.log_directory.glob("*.log"):
            if log_file.name == "watcher.log":
                # Add watcher log as a special entry
                pod_logs["🔍 Pod Log Watcher"] = [log_file]
                continue
            
            # Extract pod name from filename (remove timestamp suffix)
            pod_name = self.extract_pod_name(log_file.name)
            
            if pod_name not in pod_logs:
                pod_logs[pod_name] = []
            pod_logs[pod_name].append(log_file)
        
        return pod_logs
    
    def extract_pod_name(self, filename: str) -> str:
        """Extract pod name from log filename."""
        # Remove .log extension
        name = filename.replace('.log', '')
        
        # Remove timestamp suffix (format: _YYYYMMDD_HHMMSS)
        timestamp_pattern = r'_\d{8}_\d{6}$'
        pod_name = re.sub(timestamp_pattern, '', name)
        
        return pod_name
    
    def format_file_size(self, size_bytes: int) -> str:
        """Format file size in human-readable format."""
        if size_bytes == 0:
            return "0 B"
        
        size_names = ["B", "KB", "MB", "GB"]
        i = 0
        while size_bytes >= 1024 and i < len(size_names) - 1:
            size_bytes /= 1024.0
            i += 1
        
        return f"{size_bytes:.1f} {size_names[i]}"
    
    def on_tree_select(self, event):
        """Handle tree selection events."""
        selection = self.log_tree.selection()
        if not selection:
            return
        
        item = selection[0]
        item_tags = self.log_tree.item(item, 'tags')
        
        if 'logfile' in item_tags:
            # Get the log file path
            parent = self.log_tree.parent(item)
            pod_name = self.log_tree.item(parent, 'text')
            filename = self.log_tree.item(item, 'text')
            log_path = self.log_directory / filename
            
            self.load_log_file(log_path)
    
    def on_tree_double_click(self, event):
        """Handle tree double-click events."""
        item = self.log_tree.identify('item', event.x, event.y)
        if item:
            item_tags = self.log_tree.item(item, 'tags')
            if 'pod' in item_tags:
                # Toggle pod node expansion
                if self.log_tree.item(item, 'open'):
                    self.log_tree.item(item, open=False)
                else:
                    self.log_tree.item(item, open=True)
    
    def load_log_file(self, log_path: Path):
        """Load and display a log file."""
        if not log_path.exists():
            messagebox.showerror("Error", f"Log file not found: {log_path}")
            return
        
        self.current_log_file = log_path
        
        # Special display for watcher log
        if log_path.name == "watcher.log":
            self.current_file_var.set(f"🔍 {log_path.name} (Pod Log Watcher)")
        else:
            self.current_file_var.set(f"📄 {log_path.name}")
        
        self.status_var.set(f"Loading {log_path.name}...")
        
        try:
            # Read file content
            with open(log_path, 'r', encoding='utf-8', errors='replace') as f:
                content = f.read()
            
            # Clear text widget
            self.log_text.delete(1.0, tk.END)
            
            # Insert content with syntax highlighting
            self.insert_with_highlighting(content)
            
            # For watcher log, scroll to bottom to see recent activity
            # For pod logs, scroll to top to see the beginning
            if log_path.name == "watcher.log":
                self.log_text.see(tk.END)
            else:
                self.log_text.see(1.0)
            
            file_size = self.format_file_size(log_path.stat().st_size)
            line_count = content.count('\n') + 1
            self.status_var.set(f"Loaded {log_path.name} ({file_size}, {line_count} lines)")
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load log file: {e}")
            self.status_var.set("Error loading file")
    
    def insert_with_highlighting(self, content: str):
        """Insert text content with syntax highlighting."""
        lines = content.split('\n')
        is_watcher_log = self.current_log_file and self.current_log_file.name == "watcher.log"
        
        for i, line in enumerate(lines):
            line_start = f"{i + 1}.0"
            
            # Insert the line
            self.log_text.insert(tk.END, line + '\n')
            
            # Apply highlighting based on content
            line_lower = line.lower()
            
            # Highlight timestamps (ISO format or common log formats)
            timestamp_patterns = [
                r'\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2}',
                r'\d{2}/\d{2}/\d{4} \d{2}:\d{2}:\d{2}',
                r'\w{3} \d{2} \d{2}:\d{2}:\d{2}'
            ]
            
            for pattern in timestamp_patterns:
                for match in re.finditer(pattern, line):
                    start_idx = f"{i + 1}.{match.start()}"
                    end_idx = f"{i + 1}.{match.end()}"
                    self.log_text.tag_add('timestamp', start_idx, end_idx)
            
            # Special handling for watcher logs
            if is_watcher_log:
                self.highlight_watcher_log_line(line, line_lower, line_start, i + 1)
            else:
                self.highlight_pod_log_line(line, line_lower, line_start, i + 1)
    
    def highlight_watcher_log_line(self, line: str, line_lower: str, line_start: str, line_num: int):
        """Apply highlighting specific to watcher log lines."""
        # Watcher log format: TIMESTAMP - LOGGER - LEVEL - MESSAGE
        if ' - podlogwatcher - ' in line_lower:
            if ' - error - ' in line_lower:
                self.log_text.tag_add('watcher_error', line_start, f"{line_num}.end")
            elif ' - warning - ' in line_lower:
                self.log_text.tag_add('watcher_warning', line_start, f"{line_num}.end")
            elif ' - info - ' in line_lower:
                if any(keyword in line_lower for keyword in ['saved', 'completed', 'successful', 'loaded']):
                    self.log_text.tag_add('watcher_success', line_start, f"{line_num}.end")
                else:
                    self.log_text.tag_add('watcher_info', line_start, f"{line_num}.end")
            else:
                self.log_text.tag_add('watcher_info', line_start, f"{line_num}.end")
        else:
            # Fallback to general highlighting
            self.highlight_pod_log_line(line, line_lower, line_start, line_num)
    
    def highlight_pod_log_line(self, line: str, line_lower: str, line_start: str, line_num: int):
        """Apply highlighting for regular pod log lines."""
        # Highlight log levels
        if any(keyword in line_lower for keyword in ['error', 'err', 'exception', 'failed', 'fatal']):
            self.log_text.tag_add('error', line_start, f"{line_num}.end")
        elif any(keyword in line_lower for keyword in ['warn', 'warning']):
            self.log_text.tag_add('warning', line_start, f"{line_num}.end")
        elif any(keyword in line_lower for keyword in ['info', 'information']):
            self.log_text.tag_add('info', line_start, f"{line_num}.end")
        elif any(keyword in line_lower for keyword in ['debug', 'trace']):
            self.log_text.tag_add('debug', line_start, f"{line_num}.end")
    
    def search_logs(self, event=None):
        """Search for text in the current log."""
        search_term = self.search_var.get().strip()
        if not search_term:
            return
        
        # Clear previous search highlights
        self.log_text.tag_remove('search_highlight', 1.0, tk.END)
        self.search_results = []
        
        # Search for all occurrences
        start_pos = 1.0
        while True:
            pos = self.log_text.search(search_term, start_pos, tk.END, nocase=True)
            if not pos:
                break
            
            end_pos = f"{pos}+{len(search_term)}c"
            self.log_text.tag_add('search_highlight', pos, end_pos)
            self.search_results.append(pos)
            start_pos = end_pos
        
        # Update search info and navigation
        if self.search_results:
            self.current_search_index = 0
            self.update_search_info()
            self.goto_search_result(0)
            self.prev_btn.config(state=tk.NORMAL)
            self.next_btn.config(state=tk.NORMAL)
        else:
            self.search_info_var.set("Not found")
            self.prev_btn.config(state=tk.DISABLED)
            self.next_btn.config(state=tk.DISABLED)
    
    def prev_search_result(self):
        """Go to previous search result."""
        if self.search_results and self.current_search_index > 0:
            self.current_search_index -= 1
            self.goto_search_result(self.current_search_index)
            self.update_search_info()
    
    def next_search_result(self):
        """Go to next search result."""
        if self.search_results and self.current_search_index < len(self.search_results) - 1:
            self.current_search_index += 1
            self.goto_search_result(self.current_search_index)
            self.update_search_info()
    
    def goto_search_result(self, index: int):
        """Go to a specific search result."""
        if 0 <= index < len(self.search_results):
            pos = self.search_results[index]
            self.log_text.see(pos)
            self.log_text.mark_set(tk.INSERT, pos)
    
    def update_search_info(self):
        """Update search result information."""
        if self.search_results:
            self.search_info_var.set(f"{self.current_search_index + 1}/{len(self.search_results)}")
        else:
            self.search_info_var.set("")
    
    def on_filter_change(self, *args):
        """Handle filter text changes."""
        filter_text = self.filter_var.get().lower()
        
        # Show/hide tree items based on filter
        for pod_item in self.log_tree.get_children():
            pod_name = self.log_tree.item(pod_item, 'text').lower()
            
            if not filter_text or filter_text in pod_name:
                # Show pod and all its children
                self.show_tree_item(pod_item)
                for log_item in self.log_tree.get_children(pod_item):
                    self.show_tree_item(log_item)
            else:
                # Hide pod and all its children
                self.hide_tree_item(pod_item)
                for log_item in self.log_tree.get_children(pod_item):
                    self.hide_tree_item(log_item)
    
    def show_tree_item(self, item):
        """Show a tree item."""
        self.log_tree.reattach(item, '', tk.END)
    
    def hide_tree_item(self, item):
        """Hide a tree item."""
        self.log_tree.detach(item)
    
    def toggle_auto_refresh(self):
        """Toggle auto-refresh functionality."""
        self.auto_refresh = self.auto_refresh_var.get()
        
        if self.auto_refresh:
            self.start_auto_refresh()
            self.status_var.set("Auto-refresh enabled")
        else:
            self.status_var.set("Auto-refresh disabled")
    
    def start_auto_refresh(self):
        """Start auto-refresh in a separate thread."""
        def refresh_worker():
            while self.auto_refresh:
                time.sleep(self.refresh_interval)
                if self.auto_refresh:
                    self.root.after(0, self.refresh_log_list)
        
        thread = threading.Thread(target=refresh_worker, daemon=True)
        thread.start()
    
    def change_log_directory(self):
        """Change the log directory."""
        new_dir = filedialog.askdirectory(
            title="Select Log Directory",
            initialdir=self.log_directory
        )
        
        if new_dir:
            self.log_directory = Path(new_dir)
            self.log_dir_var.set(f"Log directory: {self.log_directory}")
            self.refresh_log_list()
    
    def run(self):
        """Start the GUI application."""
        try:
            self.root.mainloop()
        except KeyboardInterrupt:
            pass


def main():
    """Main entry point for the GUI application."""
    import argparse
    
    parser = argparse.ArgumentParser(description="OpenShift Pod Log Viewer GUI")
    parser.add_argument(
        '--log-dir',
        default=os.environ.get('POD_LOG_DIR', './pod_logs'),
        help='Directory containing pod log files (default: ./pod_logs)'
    )
    
    args = parser.parse_args()
    
    # Create and run the GUI
    app = LogViewerGUI(args.log_dir)
    app.run()


if __name__ == '__main__':
    main()
