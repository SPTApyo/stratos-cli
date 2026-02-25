import os
import sys
import time
import select
import termios
from rich.live import Live

class ExecutionController:
    """
    Refactored ExecutionController: manages user input and UI state orchestration.
    Following Clean Code: handle_key is decomposed into specific handlers.
    """
    
    def __init__(self, logger, sandbox, mission_thread, ui_active, styles, palette):
        self.logger = logger
        self.sandbox = sandbox
        self.mission_thread = mission_thread
        self.ui_active = ui_active
        self.styles = styles
        self.palette = palette

    def run(self):
        """Starts the UI loop based on the configured display mode."""
        display_mode = getattr(self.logger.state, 'display_mode', 'dashboard')
        
        if display_mode == "dashboard":
            self.logger.console.clear()
            self._run_dashboard()
        else:
            self._run_console()

    def _run_dashboard(self):
        fd = sys.stdin.fileno()
        old_settings = termios.tcgetattr(fd)
        try:
            self._set_raw_mode(fd)
            with Live(get_renderable=lambda: self.logger.render_dashboard(self.styles, self.palette), 
                      refresh_per_second=15, screen=True) as live:
                self.sandbox.live_instance = live
                self.logger.live_instance = live
                self._input_loop(fd)
        finally:
            termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)

    def _run_console(self):
        self.logger.console.print(f"[bold blue]› STARTING STRATOS IN CONSOLE MODE[/bold blue]")
        fd = sys.stdin.fileno()
        old_settings = termios.tcgetattr(fd)
        try:
            self._set_raw_mode(fd)
            from stratos.ui.components.panels import make_console_interaction
            
            while self.mission_thread.is_alive():
                if self.logger.state.active_prompt:
                    self._handle_console_prompt(fd, make_console_interaction)
                else:
                    time.sleep(0.1)
        finally:
            termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)

    def _set_raw_mode(self, fd):
        new_settings = termios.tcgetattr(fd)
        new_settings[3] = new_settings[3] & ~(termios.ECHO | termios.ICANON)
        termios.tcsetattr(fd, termios.TCSADRAIN, termios.TCSADRAIN, new_settings)

    def _handle_console_prompt(self, fd, render_func):
        with Live(get_renderable=lambda: render_func(self.logger.state, self.logger.state.prompt_mode, self.logger.state.prompt_input, self.logger.state.prompt_options, self.logger.state.prompt_selection, self.palette, self.logger.state.prompt_cursor_index),
                  refresh_per_second=15, screen=False, transient=True) as live:
            self.logger.live_instance = live
            while self.logger.state.active_prompt and self.mission_thread.is_alive():
                self._check_input(fd)
                time.sleep(0.05)
        self.logger.live_instance = None

    def _input_loop(self, fd):
        while self.mission_thread.is_alive():
            if self.ui_active.is_set():
                self._check_input(fd)
            time.sleep(0.05)

    def _check_input(self, fd):
        while select.select([sys.stdin], [], [], 0)[0]:
            keys = os.read(fd, 1024).decode('utf-8', errors='ignore')
            i = 0
            while i < len(keys):
                if keys[i] == '\x1b': # Escape sequences
                    if i + 2 < len(keys) and keys[i+1] == '[':
                        end = i + 4 if i + 3 < len(keys) and keys[i+3] == '~' else i + 3
                        self.handle_key(keys[i:end])
                        i = end
                    else:
                        self.handle_key(keys[i]); i += 1
                else:
                    self.handle_key(keys[i]); i += 1

    def handle_key(self, key):
        """Entry point for key handling, routes to specialized handlers."""
        state = self.logger.state
        
        # 1. Global Shortcuts
        if self._handle_global_shortcuts(key, state):
            return

        # 2. Prompt Handling
        if state.active_prompt:
            self._handle_prompt_logic(key, state)

    def _handle_global_shortcuts(self, key, state) -> bool:
        if key == '\x01': # Ctrl+A
            self.sandbox.auto_approve = not self.sandbox.auto_approve
            return True
        if key in ['\t', '\x09']: # TAB
            state.todo_expanded = not state.todo_expanded
            return True
        if not state.active_prompt and key.lower() == 't':
            state.thoughts_expanded = not state.thoughts_expanded
            return True
        return False

    def _handle_prompt_logic(self, key, state):
        if state.prompt_cursor_index is None:
            state.prompt_cursor_index = len(state.prompt_input)
            
        if state.prompt_mode == 'menu':
            self._handle_menu_navigation(key, state)
        else:
            self._handle_text_input(key, state)

    def _handle_menu_navigation(self, key, state):
        if key == '\x1b[A': # Up
            state.prompt_selection = max(0, state.prompt_selection - 1)
        elif key in ['\x1b[B', '\t', '\x09']: # Down or Tab
            state.prompt_selection = (state.prompt_selection + 1) % len(state.prompt_options)
        elif key in ['\r', '\n']:
            selected = state.prompt_options[state.prompt_selection]
            if selected.get('require_text'):
                self._switch_to_text_mode(state)
            else:
                self._submit_prompt(state, selected['value'])

    def _handle_text_input(self, key, state):
        idx = state.prompt_cursor_index
        
        if key in ['\r', '\n']:
            self._submit_prompt(state, state.prompt_input)
        elif key in ['\x7f', '\b']: # Backspace
            if idx > 0:
                state.prompt_input = state.prompt_input[:idx-1] + state.prompt_input[idx:]
                state.prompt_cursor_index = idx - 1
        elif key == '\x1b[3~': # Delete
            if idx < len(state.prompt_input):
                state.prompt_input = state.prompt_input[:idx] + state.prompt_input[idx+1:]
        elif key == '\x1b[D': # Left
            state.prompt_cursor_index = max(0, idx - 1)
        elif key == '\x1b[C': # Right
            state.prompt_cursor_index = min(len(state.prompt_input), idx + 1)
        elif key.isprintable():
            state.prompt_input = state.prompt_input[:idx] + key + state.prompt_input[idx:]
            state.prompt_cursor_index += 1

    def _switch_to_text_mode(self, state):
        state.prompt_mode = 'text'
        state.prompt_input = ""
        state.prompt_cursor_index = 0
        if "question" in state.active_prompt:
            state.active_prompt["question"] = "EDIT MODE: Provide instructions below"

    def _submit_prompt(self, state, value):
        state.prompt_input = value
        if hasattr(state, 'prompt_ready'):
            state.prompt_ready.set()
        if getattr(state, 'prompt_callback', None):
            state.prompt_callback(value)
