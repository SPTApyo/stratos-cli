import os
import sys
import time
import json
import threading
import signal
import termios  # Added for terminal restoration
from rich.prompt import Prompt
from rich.console import Console
from google import genai
from stratos.utils.logger import ProjectLogger
from stratos.core.sandbox import Sandbox
from stratos.core.pool import AIPool
from stratos.utils.config import load_config, get_env_var
from stratos.ui.controllers.execution_controller import ExecutionController

def run_stratos(project_name=None, project_desc=None):
    config = load_config()
    console = Console()
    
    api_key = None
    if not config.get("use_adc"):
        api_key = get_env_var("GEMINI_API_KEY")
        if not api_key:
            console.print("[bold yellow]Configuration: GEMINI_API_KEY not found in environment.[/bold yellow]")
            api_key = Prompt.ask("Enter your Google Gemini API Key", password=True)
            if not api_key:
                console.print("[bold red]ERROR: API Key is required to proceed.[/bold red]")
                return
            # Optional: Save to .env for future use
            try:
                with open(".env", "a") as f:
                    f.write(f"\nGEMINI_API_KEY={api_key}\n")
                console.print("[dim]API Key saved to .env file[/dim]")
            except Exception:
                pass

    # Credentials retrieval
    if not project_name:
        project_name = Prompt.ask("PROJECT_NAME")
    
    if not project_desc:
        if project_name == "*":
            project_desc = "MVP_TEST: Create a simple HTML/JS clock that updates every second. Single file, high-contrast design."
            console.print(f"[bold yellow]› QUICK_TEST MODE ACTIVATED[/bold yellow]")
        else:
            project_desc = Prompt.ask("DESCRIPTION")
    
    # Initialization
    base_path = config.get("projects_path", "projects")
    
    # NEW STRUCTURE
    session_root = os.path.join(base_path, project_name)
    os.makedirs(session_root, exist_ok=True)
    
    # Code folder where agents work
    sandbox_path = os.path.join(session_root, "project")
    
    sandbox = Sandbox(sandbox_path)
    logger = ProjectLogger(config, project_path=sandbox_path)
    logger.sandbox = sandbox # Link for UI status
    sandbox.logger_instance = logger # Link for manual frames
    
    original_request = project_desc
    # ... preprocessing overwrites project_desc -> this will be our MVP SPEC
    
    from stratos.ui.components.core import get_palette, get_styles
    palette = get_palette(config.get("theme", "one_dark"))
    styles = get_styles(palette)
    
    # === PRE-PROCESSING: ENRICH USER REQUEST ===
    if project_desc and project_name != "*":
        try:
            with console.status("[bold blue]Analyzing request and generating MVP spec..."):
                client = genai.Client(api_key=api_key)
                enrichment_prompt = (
                    "You are a Product Manager AI. Transform this simple user request into a comprehensive MVP specification. "
                    "Focus on core features, user flow, and key functionality. Do not focus on specific implementation technology unless requested. "
                    "Output a clear, structured list of requirements. Keep it under 200 words but make it complete.\n\n"
                    f"USER REQUEST: {project_desc}"
                )
                response = client.models.generate_content(
                    model="gemini-2.0-flash",
                    contents=enrichment_prompt
                )
                if response.text:
                    expanded_desc = response.text.strip()
                    console.print(f"\n[bold green]SPECIFICATION EXPANDED:[/bold green]\n{expanded_desc}\n")
                    logger.log("SYSTEM", f"Original Request: {project_desc}", style="info")
                    project_desc = expanded_desc
        except Exception as e:
            console.print(f"[bold red]Warning: Spec expansion failed ({str(e)}). Using original request.[/bold red]")

    ui_active = threading.Event()
    ui_active.set()
    sandbox.ui_active_event = ui_active

    # Interruption Management
    last_interrupt = 0
    def restore_terminal_echo():
        try:
            fd = sys.stdin.fileno()
            attrs = termios.tcgetattr(fd)
            # Restore ECHO and ICANON
            attrs[3] = attrs[3] | termios.ECHO | termios.ICANON
            termios.tcsetattr(fd, termios.TCSADRAIN, attrs)
        except Exception:
            pass
            
    def save_metadata():
        try:
            end_time = time.time()
            duration = end_time - logger.start_time
            file_count = sum([len(files) for r, d, files in os.walk(sandbox_path)])
            
            meta = {
                "project_name": project_name,
                "created_at": time.strftime("%Y-%m-%d %H:%M:%S"),
                "duration_seconds": round(duration, 2),
                "original_request": original_request,
                "mvp_specification": project_desc,
                "stats": {
                    "total_files": file_count,
                    "total_commands_executed": getattr(logger, 'total_commands', 0),
                    "total_tokens_used": logger.total_tokens,
                    "unique_agents_count": len(getattr(logger, 'unique_agents', [])),
                    "unique_agents_list": list(getattr(logger, 'unique_agents', []))
                }
            }
            
            with open(os.path.join(session_root, "metadata.json"), "w") as f:
                json.dump(meta, f, indent=4)
        except Exception as e:
            # Last ditch attempt to print error if logging fails
            pass

    def signal_handler(sig, frame):
        nonlocal last_interrupt
        now = time.time()
        if now - last_interrupt < 3:
            save_metadata()
            restore_terminal_echo()
            os._exit(0)
        last_interrupt = now
        
        # Save current prompt state if any

        old_prompt = getattr(logger, 'active_prompt', None)
        old_options = getattr(logger, 'prompt_options', None)
        old_mode = getattr(logger, 'prompt_mode', 'text')
        old_ready = getattr(logger, 'prompt_ready', None)
        old_callback = getattr(logger, 'prompt_callback', None)
        
        def handle_interrupt(choice):
            if choice == "exit":
                save_metadata()
                restore_terminal_echo()
                os._exit(0)
            elif choice == "instruct":
                logger.pause_requested = True
                if old_prompt:
                    logger.active_prompt = old_prompt
                    logger.prompt_options = old_options
                    logger.prompt_mode = old_mode
                    logger.prompt_ready = old_ready
                    logger.prompt_callback = old_callback
                    logger.prompt_input = ""
                    logger.prompt_selection = 0
                else:
                    logger.stop_prompt()
            else:
                if old_prompt:
                    # Restore old prompt
                    logger.active_prompt = old_prompt
                    logger.prompt_options = old_options
                    logger.prompt_mode = old_mode
                    logger.prompt_ready = old_ready
                    logger.prompt_callback = old_callback
                    logger.prompt_input = ""
                    logger.prompt_selection = 0
                else:
                    logger.stop_prompt()
                
        options = [
            {"label": "Resume Mission", "value": "resume"},
            {"label": "Add Instruction", "value": "instruct"},
            {"label": "Exit Stratos", "value": "exit"}
        ]
        logger.start_prompt("SYSTEM", "INTERRUPT: Pausing mission. Choose an action:", options=options, callback=handle_interrupt)

    signal.signal(signal.SIGINT, signal_handler)

    project_info = {"name": project_name, "desc": project_desc}
    pool = AIPool(sandbox, logger, api_key, project_info)
    pool.setup_default_pool()
    
    task = f"DEVELOP_PROJECT: {project_name}. SPECS: {project_desc}"
    
    def run_mission():
        try:
            pool.broadcast_task(task)
            logger.success("MISSION_COMPLETED")
        except Exception as e:
            logger.error(f"ENGINE_CRASH: {str(e)}")
            import traceback
            logger.debug(traceback.format_exc())

    mission_thread = threading.Thread(target=run_mission)
    mission_thread.daemon = True
    mission_thread.start()

    # Main dashboard loop
    controller = ExecutionController(logger, sandbox, mission_thread, ui_active, styles, palette)
    controller.run()
    
    save_metadata()
            
    console.print(f"\n[bold green]MISSION TERMINATED.[/bold green] Files: {sandbox_path}")
    Prompt.ask("\nPress Enter to return")
