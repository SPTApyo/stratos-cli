import os
import sys
import time
import json
import threading
import signal
import termios
from rich.console import Console
from rich.prompt import Prompt

from stratos.utils.logger import ProjectLogger
from stratos.core.sandbox import Sandbox
from stratos.core.pool import AIPool
from stratos.utils.config import load_config, get_env_var
from stratos.ui.controllers.execution_controller import ExecutionController

class MissionMetadata:
    """Handles persistence of mission results and statistics."""
    @staticmethod
    def save(project_name, project_desc, original_request, logger, session_root, sandbox_path):
        try:
            duration = time.time() - logger.state.start_time
            file_count = sum([len(files) for r, d, files in os.walk(sandbox_path)])
            meta = {
                "project_name": project_name,
                "created_at": time.strftime("%Y-%m-%d %H:%M:%S"),
                "duration_seconds": round(duration, 2),
                "original_request": original_request,
                "mvp_specification": project_desc,
                "stats": {
                    "total_files": file_count,
                    "total_commands": logger.state.total_commands,
                    "total_tokens": logger.state.total_tokens,
                    "unique_agents": list(logger.state.unique_agents)
                }
            }
            with open(os.path.join(session_root, "metadata.json"), "w") as f:
                json.dump(meta, f, indent=4)
        except Exception: pass

class SignalManager:
    """Handles OS signals and user interruptions."""
    def __init__(self, logger, sandbox, metadata_callback):
        self.logger = logger
        self.sandbox = sandbox
        self.metadata_callback = metadata_callback
        self.last_interrupt = 0

    def register(self):
        signal.signal(signal.SIGINT, self._handle_sigint)

    def _handle_sigint(self, sig, frame):
        now = time.time()
        if now - self.last_interrupt < 3:
            self.metadata_callback()
            self._restore_terminal()
            os._exit(0)
        
        self.last_interrupt = now
        self.logger.state.paused = True
        
        from stratos.ui.components.core import MENUS
        interrupt_menu = MENUS.get("INTERRUPT", {})
        options = [{"label": o["label"], "value": o["id"]} for o in interrupt_menu.get("options", [])]
        title = interrupt_menu.get("title", "INTERRUPT: Mission paused.")

        old_ctx = {
            "prompt": getattr(self.logger.state, 'active_prompt', None),
            "options": getattr(self.logger.state, 'prompt_options', None),
            "mode": getattr(self.logger.state, 'prompt_mode', 'text'),
            "ready": getattr(self.logger.state, 'prompt_ready', None),
            "callback": getattr(self.logger.state, 'prompt_callback', None)
        }

        self.logger.start_prompt("SYSTEM", title, options=options, 
                                 callback=lambda c: self._process_interrupt(c, old_ctx))

    def _process_interrupt(self, choice, old_ctx):
        if choice == "exit":
            self.metadata_callback()
            self._restore_terminal()
            os._exit(0)
        elif choice == "instruct":
            self._setup_instruction_mode()
        else:
            self.logger.state.paused = False
            if old_ctx["prompt"]:
                self.logger.state.active_prompt = old_ctx["prompt"]
                self.logger.state.prompt_options = old_ctx["options"]
                self.logger.state.prompt_mode = old_ctx["mode"]
                self.logger.state.prompt_ready = old_ctx["ready"]
                self.logger.state.prompt_callback = old_ctx["callback"]
            else:
                self.logger.stop_prompt()

    def _setup_instruction_mode(self):
        if self.logger.state.agent_is_waiting:
            self.logger.state.prompt_mode = 'text'
            self.logger.state.active_prompt["question"] = "PAUSED: Enter your instruction:"
        else:
            self.logger.state.instruction_mode_requested = True
            self.logger.state.active_prompt["question"] = "WAITING: Switching to instruction mode..."

    def _restore_terminal(self):
        try:
            fd = sys.stdin.fileno()
            attrs = termios.tcgetattr(fd)
            attrs[3] |= (termios.ECHO | termios.ICANON)
            termios.tcsetattr(fd, termios.TCSADRAIN, attrs)
        except Exception: pass

class MissionEngine:
    """Core engine orchestrating the development mission."""
    def __init__(self):
        self.config = load_config()
        self.console = Console()
        self.api_key = self._ensure_api_key()

    def _ensure_api_key(self):
        active_engine = self.config.get("active_engine")
        if not active_engine:
            return None
            
        key = get_env_var(active_engine)
        if not key:
            key = Prompt.ask(f"[bold yellow]Enter {active_engine} API Key[/]", password=True)
            if key:
                from stratos.utils.config import save_env_var
                save_env_var(f"STRATOS_{active_engine.upper()}_API_KEY", key)
        return key

    def run(self, project_name=None, project_desc=None, existing_path=None, mission_type="NEW_PROJECT"):
        if not project_name: project_name = Prompt.ask("PROJECT_NAME")
        if not project_desc: project_desc = self._get_default_desc(project_name)
        
        if existing_path:
            sandbox_path = os.path.abspath(os.path.expanduser(existing_path))
            session_root = sandbox_path
        else:
            base = self.config.get("projects_path", "projects")
            session_root = os.path.join(base, project_name)
            sandbox_path = os.path.join(session_root, "project")
            
        os.makedirs(sandbox_path, exist_ok=True)

        sandbox = Sandbox(sandbox_path)
        logger = ProjectLogger(self.config, project_path=sandbox_path)
        logger.sandbox = sandbox
        sandbox.logger_instance = logger
        
        original_request = project_desc
        project_desc = self._enrich_specification(project_desc, logger)

        meta_saver = lambda: MissionMetadata.save(project_name, project_desc, original_request, logger, session_root, sandbox_path)
        SignalManager(logger, sandbox, meta_saver).register()

        pool = AIPool(sandbox, logger, self.api_key, {"name": project_name, "desc": project_desc}, mission_type=mission_type)
        pool.setup_default_pool()
        
        def mission_task():
            try:
                pool.broadcast_task(f"DEVELOP_PROJECT: {project_name}. SPECS: {project_desc}")
                logger.success("MISSION_COMPLETED")
            except Exception as e:
                logger.error(f"CRASH: {str(e)}")

        threading.Thread(target=mission_task, daemon=True).start()

        from stratos.ui.components.core import get_palette, get_styles
        palette = get_palette(self.config.get("theme", "one_dark"))
        ui_active = threading.Event(); ui_active.set()
        sandbox.ui_active_event = ui_active
        
        ExecutionController(logger, sandbox, threading.current_thread(), ui_active, get_styles(palette), palette).run()
        
        meta_saver()
        from rich.panel import Panel
        from rich.text import Text
        from rich.rule import Rule
        
        self.console.print("\n")
        self.console.print(Rule(style="dim green"))
        success_msg = Text.from_markup(f" [bold green]✓[/] [bold white]MISSION SUCCESSFUL[/] [dim]•[/] [gray]Output saved to:[/] [cyan]{sandbox_path}[/]")
        self.console.print(Panel(success_msg, border_style="bold green", expand=False, padding=(0, 2)))
        self.console.print(Text(f"  › SYSTEM STANDBY | {time.strftime('%H:%M:%S')}\n", style="bold green"))

    def _get_default_desc(self, name):
        if name == "*":
            from stratos.utils.config import QUICK_MISSION_DESC
            return QUICK_MISSION_DESC
        return Prompt.ask("DESCRIPTION")

    def _enrich_specification(self, desc, logger):
        if desc.startswith("MVP_TEST"): return desc
        active_engine = self.config.get("active_engine")
        if not active_engine: return desc

        try:
            with self.console.status(f"[bold blue]Enriching Spec with {active_engine}..."):
                from stratos.core.engines.factory import EngineFactory
                from stratos.assets import load_prompt
                from stratos.core.engines.protocol import Message, MessagePart
                
                engine = EngineFactory.create_engine(active_engine, "MEDIUM", self.api_key)
                
                prompt = load_prompt("pm_enrichment", project_desc=desc)
                messages = [Message(role="user", parts=[MessagePart(text=prompt)])]
                
                response_parts = engine.generate_content(messages, [], 1, logger)
                
                if isinstance(response_parts, list):
                    text = "".join([p.text for p in response_parts if p.text])
                    if text:
                        logger.info(f"Specification enriched by {active_engine} PM.")
                        return text.strip()
        except Exception: pass
        return desc

def run_stratos(project_name=None, project_desc=None, existing_path=None, mission_type="NEW_PROJECT"):
    MissionEngine().run(project_name, project_desc, existing_path, mission_type=mission_type)
