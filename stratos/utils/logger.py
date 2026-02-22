from rich.console import Console
from datetime import datetime
import time
import threading
from stratos.ui.views.execution_view import render_execution_dashboard

class ProjectLogger:
    def __init__(self, config, project_path=None):
        self.config = config
        self.debug_mode = config.get("debug_mode", False)
        self.show_thoughts = config.get("show_thoughts", True)
        self.display_mode = config.get("display_mode", "dashboard")
        self.show_results = config.get("show_results", True)
        self.project_path = project_path or config.get("projects_path", "projects")
        self.max_logs = config.get("max_logs", 100)
        self.start_time = time.time(); self.agent_start_time = time.time()
        self.current_agent = "SYSTEM"; self.current_thought = ""
        self.total_tokens = 0; self.error_count = 0; self.logs = []
        self.total_commands = 0; self.unique_agents = set()
        self.todo_list = []; self.todo_expanded = False; self.current_cycle = 0
        self.thoughts_expanded = False
        self.active_prompt = None; self.paused = False; self.pause_requested = False
        self.console = Console()
        self.prompt_session_id = 0

    def log(self, agent_name, message, style="info"):
        tstamp = datetime.now().strftime("%H:%M:%S")
        self.current_agent = agent_name; self.agent_start_time = time.time()
        style_map = {"exec": "EXEC", "cmd": "EXEC", "file": "FILE", "edit": "EDIT", "git": "GIT", "task": "TASK", "result": "RES", "res": "RES", "success": "OK", "error": "ERR", "debug": "DEBUG", "info": "INFO", "warning": "WARN"}
        tag = style_map.get(style.lower(), "INFO")
        clean_msg = str(message).strip()
        if ":" in clean_msg[:10]:
            pt, mp = clean_msg.split(":", 1); pu = pt.strip().upper()
            if pu in style_map.values() or pu in ["TASK", "RESULT", "SUCCESS", "ERROR"]:
                tag = "OK" if pu == "SUCCESS" else "ERR" if pu == "ERROR" else "RES" if pu == "RESULT" else pu
                clean_msg = mp.strip()
        if tag == "ERR": self.error_count += 1
        if tag == "EXEC" or tag == "CMD": self.total_commands += 1
        self.unique_agents.add(agent_name)
        
        if tag == "RES" and not self.show_results: return
        clean_msg = " ".join(clean_msg.replace("STDOUT:", "").replace("STDERR:", "").replace("\n", " ").split())
        log_entry = {"time": tstamp, "tag": f"{tag:<5}", "agent": agent_name, "msg": clean_msg}
        self.logs.append(log_entry)
        
        if self.display_mode == "console":
            from rich.text import Text
            ts = "bold green" if tag == "OK" else "bold yellow" if tag == "EXEC" else "bold red" if tag == "ERR" else "bold purple" if tag == "TASK" else "bold cyan" if tag == "DEBUG" else "bold blue"
            renderable = Text.assemble((f"[{tstamp}] ", "dim"), (f"[{tag}] ", ts), (f"{agent_name}: ", "bold blue"), (clean_msg, ""))
            
            if hasattr(self, 'live_instance') and self.live_instance and self.live_instance.is_started:
                self.live_instance.console.print(renderable)
            else:
                self.console.print(renderable)

        if len(self.logs) > self.max_logs:
            self.logs.pop(0)

    def render_dashboard(self, styles, palette_raw):
        term_height = self.console.size.height
        layout = render_execution_dashboard(self, styles, palette_raw, term_height)
        self.last_styles = styles
        self.last_palette = palette_raw
        return layout

    def set_todo(self, content):
        self.todo_list = []
        for line in str(content).split("\n"):
            line = line.strip()
            if not line: continue
            status = "done" if "[x]" in line.lower() or "done" in line.lower() else "active" if "[/]" in line or "active" in line.lower() else "pending"
            self.todo_list.append({"task": line.replace("[x]","").replace("[/]","").replace("[ ]","").strip(), "status": status})
    def update_tokens(self, t): self.total_tokens = t
    def debug(self, m): 
        # Always log debug messages as requested by user
        self.log("SYSTEM", m, style="debug")
    def update_spinner(self, t, thought=""): self.current_thought = thought
    
    def start_prompt(self, a, q, details=None, options=None, callback=None): 
        priority = 10 if a == "SYSTEM" else 0
        current_priority = getattr(self, '_current_prompt_priority', 0)
        
        if self.active_prompt and priority < current_priority:
            return -1 # Don't overwrite higher priority prompt
            
        self.prompt_session_id += 1
        sid = self.prompt_session_id
        
        self.active_prompt = {"agent": a, "question": q, "details": details, "sid": sid}
        self._current_prompt_priority = priority
        self.prompt_input = ""
        self.prompt_cursor_index = 0
        self.prompt_options = options or []
        self.prompt_selection = 0
        self.prompt_mode = 'menu' if options else 'text'
        self.prompt_ready = threading.Event()
        self.prompt_callback = callback
        return sid
        
    def stop_prompt(self): 
        self.active_prompt = None
        self._current_prompt_priority = 0
        self.prompt_input = ""
        self.prompt_cursor_index = 0
        self.prompt_options = []
        self.prompt_callback = None
        if hasattr(self, 'prompt_ready'):
            self.prompt_ready.clear()

    def start_cycle(self, n): self.current_cycle = n; sep = "─" * 40; self.log("SYSTEM", f"{sep} ITERATION {n} {sep}", style="success")
    def agent_takeover(self, n, r): self.log(n, f"Role: {r}", style="info")
    def success(self, m): self.log("SYSTEM", m, style="success")
    def error(self, m): self.log("SYSTEM", m, style="error")
    def info(self, m): self.log("SYSTEM", m, style="info")
    def warning(self, m): self.log("SYSTEM", m, style="warning")
    def section(self, m): self.log("SYSTEM", f"=== {m.upper()} ===", style="info")
    
    def wait_if_paused(self):
        """Block the execution if the mission is in a paused state."""
        if self.paused:
            self.agent_is_waiting = True
            # Update prompt text if it's an interrupt prompt
            if self.active_prompt and ("INTERRUPT" in self.active_prompt.get("question", "") or "WAITING" in self.active_prompt.get("question", "")):
                if getattr(self, 'instruction_mode_requested', False):
                    self.prompt_mode = 'text'
                    self.prompt_input = ""
                    self.prompt_cursor_index = 0
                    self.active_prompt["question"] = "PAUSED: Enter your instruction below:"
                    self.instruction_mode_requested = False
                else:
                    self.active_prompt["question"] = "INTERRUPT: Mission PAUSED. Choose an action:"
            
            self.debug("PAUSE_ACTIVE: Thread waiting for resume signal...")
            while self.paused:
                time.sleep(0.5)
            self.agent_is_waiting = False
            self.debug("RESUME_SIGNAL: Continuing execution.")

    def print_current_frame(self):
        if hasattr(self, 'last_styles') and hasattr(self, 'last_palette'):
            self.console.print(self.render_dashboard(self.last_styles, self.last_palette))
