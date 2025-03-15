"""
Dark Epoch Bot - Graphical User Interface
Provides a simple GUI for controlling the Dark Epoch bot.
"""

import logging
import threading
import time
import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
import os
from PIL import Image, ImageTk

logger = logging.getLogger('DarkEpochBot')

class LogHandler(logging.Handler):
    """Custom log handler to redirect logs to the GUI"""
    def __init__(self, text_widget):
        super().__init__()
        self.text_widget = text_widget
        
    def emit(self, record):
        msg = self.format(record)
        
        # Queue the log update to avoid threading issues
        self.text_widget.after(0, self._add_log, msg, record.levelname)
        
    def _add_log(self, msg, level):
        self.text_widget.configure(state='normal')
        
        # Add timestamp
        self.text_widget.insert(tk.END, msg + '\n')
        
        # Apply color based on log level
        line_count = int(self.text_widget.index('end-1c').split('.')[0])
        line_start = f'{line_count-1}.0'
        line_end = f'{line_count-1}.end'
        
        # Color based on log level
        if level == 'ERROR' or level == 'CRITICAL':
            self.text_widget.tag_add("error", line_start, line_end)
        elif level == 'WARNING':
            self.text_widget.tag_add("warning", line_start, line_end)
        elif level == 'INFO':
            self.text_widget.tag_add("info", line_start, line_end)
        
        # Scroll to the end
        self.text_widget.see(tk.END)
        self.text_widget.configure(state='disabled')

class BotGUI(tk.Tk):
    def __init__(self, bot):
        """
        Initialize the Bot GUI.
        
        Args:
            bot: DarkEpochBot instance
        """
        super().__init__()
        
        self.bot = bot
        self.bot_thread = None
        self.stop_flag = threading.Event()
        
        # Set up the window
        self.title("Dark Epoch Bot")
        self.geometry("800x600")
        self.minsize(700, 500)
        
        # Set up the style
        self.style = ttk.Style()
        self.style.theme_use('clam')  # Use a theme that works well with custom colors
        
        # Configure colors
        self.bg_color = "#2b2b2b"
        self.text_color = "#e6e6e6"
        self.accent_color = "#3c719f"
        self.button_color = "#3c719f"
        self.warning_color = "#d9b51c"
        self.error_color = "#cf6679"
        
        self.configure(bg=self.bg_color)
        
        # Configure styles
        self.style.configure('TFrame', background=self.bg_color)
        self.style.configure('TLabel', background=self.bg_color, foreground=self.text_color)
        self.style.configure('TButton', background=self.button_color, foreground=self.text_color)
        self.style.map('TButton', background=[('active', self.accent_color)])
        
        # Create main frame
        self.main_frame = ttk.Frame(self)
        self.main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Create content
        self._create_header()
        self._create_control_panel()
        self._create_status_panel()
        self._create_log_panel()
        
        # Configure log handler
        self._configure_logging()
        
        # Set up update timer
        self._update_timer()
        
        # Bind close event
        self.protocol("WM_DELETE_WINDOW", self._on_close)
        
        logger.info("Dark Epoch Bot GUI initialized")
    
    def _create_header(self):
        """Create the header section of the GUI"""
        header_frame = ttk.Frame(self.main_frame)
        header_frame.pack(fill=tk.X, pady=(0, 10))
        
        title_label = ttk.Label(
            header_frame, 
            text="Dark Epoch Bot", 
            font=("Arial", 16, "bold")
        )
        title_label.pack(side=tk.LEFT)
        
        # Create SVG icon
        self.icon_path = "templates/icon.svg"
        if os.path.exists(self.icon_path):
            try:
                icon_img = Image.open(self.icon_path)
                icon_img = icon_img.resize((32, 32))
                self.icon = ImageTk.PhotoImage(icon_img)
                icon_label = ttk.Label(header_frame, image=self.icon)
                icon_label.pack(side=tk.RIGHT)
            except Exception as e:
                logger.error(f"Error loading icon: {e}")
    
    def _create_control_panel(self):
        """Create the control panel section of the GUI"""
        control_frame = ttk.Frame(self.main_frame)
        control_frame.pack(fill=tk.X, pady=10)
        
        # Start button
        self.start_button = ttk.Button(
            control_frame, 
            text="Start Bot", 
            command=self._start_bot
        )
        self.start_button.pack(side=tk.LEFT, padx=(0, 5))
        
        # Stop button
        self.stop_button = ttk.Button(
            control_frame, 
            text="Stop Bot", 
            command=self._stop_bot,
            state=tk.DISABLED
        )
        self.stop_button.pack(side=tk.LEFT, padx=5)
        
        # Pause/Resume button
        self.pause_button = ttk.Button(
            control_frame, 
            text="Pause", 
            command=self._toggle_pause,
            state=tk.DISABLED
        )
        self.pause_button.pack(side=tk.LEFT, padx=5)
        
        # Scan windows button
        self.scan_button = ttk.Button(
            control_frame, 
            text="Scan Windows", 
            command=self._scan_windows
        )
        self.scan_button.pack(side=tk.LEFT, padx=5)
        
        # Arrange windows button
        self.arrange_button = ttk.Button(
            control_frame, 
            text="Arrange Windows", 
            command=self._arrange_windows
        )
        self.arrange_button.pack(side=tk.LEFT, padx=5)
    
    def _create_status_panel(self):
        """Create the status panel section of the GUI"""
        status_frame = ttk.Frame(self.main_frame)
        status_frame.pack(fill=tk.X, pady=10)
        
        # Status label
        status_label = ttk.Label(status_frame, text="Status:")
        status_label.pack(side=tk.LEFT, padx=(0, 5))
        
        self.status_text = tk.StringVar()
        self.status_text.set("Idle")
        status_value = ttk.Label(
            status_frame, 
            textvariable=self.status_text,
            font=("Arial", 10, "bold")
        )
        status_value.pack(side=tk.LEFT, padx=5)
        
        # Client count label
        client_label = ttk.Label(status_frame, text="Clients:")
        client_label.pack(side=tk.LEFT, padx=(20, 5))
        
        self.client_count = tk.StringVar()
        self.client_count.set("0/0")
        client_value = ttk.Label(
            status_frame, 
            textvariable=self.client_count,
            font=("Arial", 10, "bold")
        )
        client_value.pack(side=tk.LEFT, padx=5)
        
        # Current task label
        task_label = ttk.Label(status_frame, text="Task:")
        task_label.pack(side=tk.LEFT, padx=(20, 5))
        
        self.current_task = tk.StringVar()
        self.current_task.set("None")
        task_value = ttk.Label(
            status_frame, 
            textvariable=self.current_task,
            font=("Arial", 10, "bold")
        )
        task_value.pack(side=tk.LEFT, padx=5)
        
        # Error count label
        error_label = ttk.Label(status_frame, text="Errors:")
        error_label.pack(side=tk.LEFT, padx=(20, 5))
        
        self.error_count = tk.StringVar()
        self.error_count.set("0")
        error_value = ttk.Label(
            status_frame, 
            textvariable=self.error_count,
            font=("Arial", 10, "bold")
        )
        error_value.pack(side=tk.LEFT, padx=5)
    
    def _create_log_panel(self):
        """Create the log panel section of the GUI"""
        log_frame = ttk.Frame(self.main_frame)
        log_frame.pack(fill=tk.BOTH, expand=True, pady=10)
        
        # Log label
        log_label = ttk.Label(log_frame, text="Activity Log:")
        log_label.pack(anchor=tk.W)
        
        # Log text area
        self.log_text = scrolledtext.ScrolledText(
            log_frame, 
            wrap=tk.WORD, 
            bg="#1e1e1e", 
            fg=self.text_color,
            height=15
        )
        self.log_text.pack(fill=tk.BOTH, expand=True, pady=(5, 0))
        
        # Configure log text tags for colorizing
        self.log_text.tag_configure("error", foreground=self.error_color)
        self.log_text.tag_configure("warning", foreground=self.warning_color)
        self.log_text.tag_configure("info", foreground=self.text_color)
        
        # Make log text read-only
        self.log_text.configure(state='disabled')
    
    def _configure_logging(self):
        """Configure logging to display in the GUI"""
        # Create and add custom handler
        log_handler = LogHandler(self.log_text)
        log_handler.setLevel(logging.INFO)
        
        # Create formatter
        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s', '%H:%M:%S')
        log_handler.setFormatter(formatter)
        
        # Add handler to logger
        logger.addHandler(log_handler)
    
    def _update_timer(self):
        """Update GUI elements regularly"""
        # Update status
        if self.bot.running:
            if self.bot.paused:
                self.status_text.set("Paused")
            else:
                self.status_text.set("Running")
        else:
            self.status_text.set("Idle")
        
        # Update client count
        active_clients = self.bot.client_manager.clients
        active_count = len(active_clients)
        if active_count > 0:
            self.client_count.set(f"{min(2, active_count)} active / {active_count} total")
        else:
            self.client_count.set("0/0")
        
        # Update current task
        if self.bot.current_task:
            self.current_task.set(self.bot.current_task.capitalize())
        else:
            self.current_task.set("None")
        
        # Update error count
        self.error_count.set(str(self.bot.error_count))
        
        # Schedule next update
        self.after(500, self._update_timer)
    
    def _start_bot(self):
        """Start the bot"""
        if self.bot_thread and self.bot_thread.is_alive():
            logger.warning("Bot is already running")
            return
        
        # Clear stop flag
        self.stop_flag.clear()
        
        # Start the bot
        if self.bot.start():
            # Start bot thread
            self.bot_thread = threading.Thread(target=self._bot_worker)
            self.bot_thread.daemon = True
            self.bot_thread.start()
            
            # Update buttons
            self.start_button.configure(state=tk.DISABLED)
            self.stop_button.configure(state=tk.NORMAL)
            self.pause_button.configure(state=tk.NORMAL)
            self.scan_button.configure(state=tk.DISABLED)
            self.arrange_button.configure(state=tk.DISABLED)
            
            logger.info("Bot started")
        else:
            messagebox.showerror(
                "Start Error", 
                "Failed to start bot. Check log for details."
            )
    
    def _stop_bot(self):
        """Stop the bot"""
        if not self.bot_thread or not self.bot_thread.is_alive():
            logger.warning("Bot is not running")
            return
        
        # Set stop flag and stop bot
        self.stop_flag.set()
        self.bot.stop()
        
        # Update buttons
        self.start_button.configure(state=tk.NORMAL)
        self.stop_button.configure(state=tk.DISABLED)
        self.pause_button.configure(state=tk.DISABLED)
        self.scan_button.configure(state=tk.NORMAL)
        self.arrange_button.configure(state=tk.NORMAL)
        
        # Reset pause button text
        self.pause_button.configure(text="Pause")
        
        logger.info("Bot stopped")
    
    def _toggle_pause(self):
        """Toggle pause state of the bot"""
        if not self.bot.running:
            return
            
        if self.bot.paused:
            self.bot.resume()
            self.pause_button.configure(text="Pause")
            logger.info("Bot resumed")
        else:
            self.bot.pause()
            self.pause_button.configure(text="Resume")
            logger.info("Bot paused")
    
    def _scan_windows(self):
        """Scan for game client windows"""
        clients = self.bot.client_manager.scan_for_clients()
        
        if clients:
            messagebox.showinfo(
                "Window Scan", 
                f"Found {len(clients)} client windows."
            )
        else:
            messagebox.showwarning(
                "Window Scan", 
                "No client windows found. Make sure Dark Epoch is running."
            )
    
    def _arrange_windows(self):
        """Arrange client windows"""
        if not self.bot.client_manager.clients:
            self._scan_windows()
            
        if self.bot.client_manager.clients:
            self.bot.client_manager.arrange_clients()
            messagebox.showinfo(
                "Window Arrangement", 
                "Client windows have been arranged."
            )
        else:
            messagebox.showwarning(
                "Window Arrangement", 
                "No client windows to arrange."
            )
    
    def _bot_worker(self):
        """Worker thread function for bot operation"""
        try:
            logger.info("Bot worker thread started")
            
            # Main bot loop
            while not self.stop_flag.is_set() and self.bot.running:
                # Check if paused
                if not self.bot.paused:
                    self.bot.run_cycle()
                
                # Prevent CPU overload
                time.sleep(0.1)
                
            logger.info("Bot worker thread finished")
            
        except Exception as e:
            logger.error(f"Error in bot worker thread: {e}", exc_info=True)
            
            # Show error message
            self.after(0, lambda: messagebox.showerror(
                "Bot Error", 
                f"An error occurred in the bot worker thread:\n{str(e)}"
            ))
            
            # Stop the bot
            self.after(0, self._stop_bot)
    
    def _on_close(self):
        """Handle window close event"""
        if self.bot_thread and self.bot_thread.is_alive():
            # Ask for confirmation if bot is running
            if messagebox.askyesno(
                "Confirm Exit", 
                "Bot is still running. Are you sure you want to exit?"
            ):
                self._stop_bot()
                self.destroy()
        else:
            self.destroy()
