import time
import threading
from dataclasses import dataclass
from datetime import datetime
from rich.console import Console

@dataclass
class LogEntry:
    time: str; tag: str; agent: str; msg: str

class LogParser:
    """Parses raw messages and styles into standardized LogEntry objects."""
    STYLE_MAP = {
        "exec": "EXEC", "cmd": "EXEC", "file": "FILE", "edit": "EDIT", 
        "git": "GIT", "task": "TASK", "result": "RES", "res": "RES", 
        "success": "OK", "error": "ERR", "debug": "DEBUG", 
        "info": "INFO", "warning": "WARN"
    }

    @classmethod
    def parse(cls, agent, message, style) -> tuple:
        tag = cls.STYLE_MAP.get(style.lower(), "INFO")
        msg = str(message).strip()
        
        if ":" in msg[:10]:
            parts = msg.split(":", 1)
            header = parts[0].strip().upper()
            if header in ["SUCCESS", "OK"]: tag = "OK"; msg = parts[1].strip()
            elif header in ["ERROR", "ERR"]: tag = "ERR"; msg = parts[1].strip()
            elif header in cls.STYLE_MAP.values(): tag = header; msg = parts[1].strip()

        msg = " ".join(msg.replace("STDOUT:", "").replace("STDERR:", "").replace("\n", " ").split())
        return tag, msg

class MissionState:
    """Holds the live state of a development mission."""
    def __init__(self, config, project_path):
        self.project_path = project_path
        self.start_time = time.time(); self.agent_start_time = time.time()
        self.current_agent = "SYSTEM"; self.current_thought = ""
        self.total_tokens = 0; self.error_count = 0; self.total_commands = 0
        self.logs = []; self.todo_list = []; self.current_cycle = 0
        self.unique_agents = set()
        
        self.paused = False; self.agent_is_waiting = False; self.pause_requested = False
        self.instruction_mode_requested = False
        
        self.active_prompt = None; self.prompt_mode = 'text'; self.prompt_input = ""
        self.prompt_cursor_index = 0; self.prompt_options = []; self.prompt_selection = 0
        self.prompt_ready = threading.Event(); self.prompt_session_id = 0
        
        self.show_thoughts = config.get("show_thoughts", True)
        self.show_results = config.get("show_results", True)
        self.display_mode = config.get("display_mode", "dashboard")
        self.todo_expanded = False; self.thoughts_expanded = False

class ProjectLogger:
    """Orchestrates logging and UI state synchronization."""
    def __init__(self, config, project_path=None):
        self.state = MissionState(config, project_path or config.get("projects_path"))
        self.console = Console(); self.max_logs = config.get("max_logs", 100)

    def log(self, agent_name, message, style="info"):
        tag, clean_msg = LogParser.parse(agent_name, message, style)
        entry = LogEntry(time=datetime.now().strftime("%H:%M:%S"), tag=f"{tag:<5}", agent=agent_name, msg=clean_msg)
        
        self.state.current_agent = agent_name; self.state.agent_start_time = time.time()
        if tag == "ERR": self.state.error_count += 1
        if tag == "EXEC": self.state.total_commands += 1
        self.state.unique_agents.add(agent_name)
        
        if tag == "RES" and not self.state.show_results: return
        self.state.logs.append(entry.__dict__)
        if len(self.state.logs) > self.max_logs: self.state.logs.pop(0)

        if self.state.display_mode == "console": self._print_console(entry)

    def _print_console(self, entry):
        from rich.text import Text
        colors = {"OK": "bold green", "EXEC": "bold yellow", "ERR": "bold red", "TASK": "bold purple", "DEBUG": "bold cyan"}
        style = colors.get(entry.tag.strip(), "bold blue")
        renderable = Text.assemble((f"[{entry.time}] ", "dim"), (f"[{entry.tag}] ", style), (f"{entry.agent}: ", "bold blue"), (entry.msg, ""))
        if hasattr(self, 'live_instance') and self.live_instance and self.live_instance.is_started:
            self.live_instance.console.print(renderable)
        else: self.console.print(renderable)

    def set_todo(self, content):
        self.state.todo_list = []
        for line in str(content).split("\n"):
            line = line.strip()
            if not line: continue
            status = "done" if "[x]" in line.lower() else "active" if "[/]" in line else "pending"
            task = line.replace("[x]","").replace("[/]","").replace("[ ]","").strip()
            self.state.todo_list.append({"task": task, "status": status})

    def start_prompt(self, agent, question, details=None, options=None, callback=None):
        priority = 10 if agent == "SYSTEM" else 0
        if self.state.active_prompt and priority < getattr(self.state, '_priority', 0): return -1
        
        self.state.prompt_session_id += 1
        self.state.active_prompt = {"agent": agent, "question": question, "details": details, "sid": self.state.prompt_session_id}
        self.state._priority = priority; self.state.prompt_input = ""; self.state.prompt_cursor_index = 0
        self.state.prompt_options = options or []; self.state.prompt_selection = 0
        self.state.prompt_mode = 'menu' if options else 'text'; self.state.prompt_callback = callback
        self.state.prompt_ready.clear()
        return self.state.prompt_session_id

    def stop_prompt(self):
        self.state.active_prompt = None; self.state._priority = 0; self.state.prompt_ready.clear()

    def wait_if_paused(self):
        if self.state.paused:
            self.state.agent_is_waiting = True
            while self.state.paused:
                if self.state.instruction_mode_requested:
                    self.state.prompt_mode = 'text'
                    self.state.active_prompt["question"] = "PAUSED: Enter your instruction below:"
                    self.state.instruction_mode_requested = False
                time.sleep(0.5)
            self.state.agent_is_waiting = False

    def render_dashboard(self, styles, palette):
        from stratos.ui.views.execution_view import render_execution_dashboard
        return render_execution_dashboard(self.state, styles, palette, self.console.size.height)

    def debug(self, m): self.log("SYSTEM", m, style="debug")
    def info(self, m): self.log("SYSTEM", m, style="info")
    def success(self, m): self.log("SYSTEM", m, style="success")
    def error(self, m): self.log("SYSTEM", m, style="error")
    def warning(self, m): self.log("SYSTEM", m, style="warning")
    def start_cycle(self, n): self.state.current_cycle = n; self.log("SYSTEM", f"─── ITERATION {n} ───", style="success")
    def update_spinner(self, t, thought=""): self.state.current_thought = thought
    def update_tokens(self, t): self.state.total_tokens = t
    def agent_takeover(self, n, r): self.log(n, f"Role: {r}", style="info")
    def section(self, m): self.log("SYSTEM", f"=== {m.upper()} ===", style="info")
