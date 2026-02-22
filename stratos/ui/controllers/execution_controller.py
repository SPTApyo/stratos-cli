import os
import sys
import time
import select
import termios
import tty
from rich.live import Live

class ExecutionController:
    def __init__(self, logger, sandbox, mission_thread, ui_active, styles, palette):
        self.logger = logger
        self.sandbox = sandbox
        self.mission_thread = mission_thread
        self.ui_active = ui_active
        self.styles = styles
        self.palette = palette

    def run(self):
        self.logger.console.clear()
        
        fd = sys.stdin.fileno()
        old_settings = termios.tcgetattr(fd)
        
        try:
            # Set terminal to cbreak mode and disable echo
            new_settings = termios.tcgetattr(fd)
            new_settings[3] = new_settings[3] & ~(termios.ECHO | termios.ICANON)
            termios.tcsetattr(fd, termios.TCSADRAIN, new_settings)
            
            def get_renderable():
                return self.logger.render_dashboard(self.styles, self.palette)
                
            with Live(get_renderable=get_renderable, refresh_per_second=15, screen=True) as live:
                self.sandbox.live_instance = live
                self.logger.live_instance = live
                
                while self.mission_thread.is_alive():
                    if self.ui_active.is_set():
                        # Read all available keys without blocking
                        while True:
                            rlist, _, _ = select.select([sys.stdin], [], [], 0)
                            if rlist:
                                keys = os.read(fd, 1024).decode('utf-8', errors='ignore')
                                i = 0
                                while i < len(keys):
                                    # Handle escape sequences
                                    if keys[i] == '\x1b':
                                        if i + 3 < len(keys) and keys[i+1] == '[' and keys[i+3] == '~':
                                            self.handle_key(keys[i:i+4])
                                            i += 4
                                        elif i + 2 < len(keys) and keys[i+1] == '[':
                                            self.handle_key(keys[i:i+3])
                                            i += 3
                                        else:
                                            self.handle_key(keys[i])
                                            i += 1
                                    else:
                                        self.handle_key(keys[i])
                                        i += 1
                            else:
                                break
                    
                    time.sleep(0.05) # slightly faster for typing responsiveness
                
                time.sleep(1.0)
        finally:
            # Restore terminal settings
            termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)

    def handle_key(self, key):
        # Global Shortcuts
        if key == '\x01': # Ctrl+A
            self.sandbox.auto_approve = not self.sandbox.auto_approve
            status = "ENABLED" if self.sandbox.auto_approve else "DISABLED"
            # Flash a message or reliance on dashboard update
            if hasattr(self.logger, 'live_instance'):
                 # Force a refresh or simply let the next frame handle it
                 pass
            return

        if self.logger.active_prompt:
            prompt_mode = getattr(self.logger, 'prompt_mode', 'text')

            if prompt_mode == 'menu':
                if key == '\x1b[A': # Up
                    self.logger.prompt_selection = max(0, self.logger.prompt_selection - 1)
                elif key == '\x1b[B' or key == '\t' or key == '\x09': # Down or Tab
                    self.logger.prompt_selection = (self.logger.prompt_selection + 1) % len(self.logger.prompt_options)
                elif key == '\r' or key == '\n':
                    selected = self.logger.prompt_options[self.logger.prompt_selection]
                    if selected.get('require_text'):
                        self.logger.prompt_mode = 'text'
                        self.logger.prompt_input = ""
                    else:
                        self.logger.prompt_input = selected['value']
                        if hasattr(self.logger, 'prompt_ready'):
                            self.logger.prompt_ready.set()
                        if getattr(self.logger, 'prompt_callback', None):
                            self.logger.prompt_callback(self.logger.prompt_input)
            else:
                if not hasattr(self.logger, 'prompt_cursor_index'):
                    self.logger.prompt_cursor_index = len(self.logger.prompt_input)
                idx = self.logger.prompt_cursor_index
                
                if key == '\r' or key == '\n':
                    if hasattr(self.logger, 'prompt_ready'):
                        self.logger.prompt_ready.set()
                    if getattr(self.logger, 'prompt_callback', None):
                        self.logger.prompt_callback(self.logger.prompt_input)
                elif key == '\x7f' or key == '\b': # Backspace
                    if idx > 0:
                        self.logger.prompt_input = self.logger.prompt_input[:idx-1] + self.logger.prompt_input[idx:]
                        self.logger.prompt_cursor_index = max(0, idx - 1)
                elif key == '\x1b[3~': # Delete key
                    if idx < len(self.logger.prompt_input):
                        self.logger.prompt_input = self.logger.prompt_input[:idx] + self.logger.prompt_input[idx+1:]
                elif key == '\x1b[D': # Left Arrow
                    self.logger.prompt_cursor_index = max(0, idx - 1)
                elif key == '\x1b[C': # Right Arrow
                    self.logger.prompt_cursor_index = min(len(self.logger.prompt_input), idx + 1)
                elif key.isprintable():
                    self.logger.prompt_input = self.logger.prompt_input[:idx] + key + self.logger.prompt_input[idx:]
                    self.logger.prompt_cursor_index += 1
        else:
            if key == '\t' or key == '\x09': # TAB
                self.logger.todo_expanded = not self.logger.todo_expanded
            elif key.lower() == 't':
                self.logger.thoughts_expanded = not self.logger.thoughts_expanded
