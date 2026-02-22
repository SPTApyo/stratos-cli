import os
import sys
import readchar
import subprocess
from rich.console import Console
from rich.live import Live
from rich.prompt import Prompt
from rich.text import Text
from stratos.utils.config import load_config, save_config, get_env_var
from stratos.ui.components.core import MENUS, get_palette, get_styles
from stratos.ui.components.panels import make_gradient_panel
from stratos.ui.components.banner import get_banner
from stratos.ui.views.launch_view import render_launch_dashboard
from stratos.core.engine import run_stratos

class StratosState:
    def __init__(self, cli_args=None):
        self.config = load_config()
        # Apply CLI overrides
        if cli_args:
            if cli_args.debug: self.config["debug_mode"] = True
            if cli_args.no_thoughts: self.config["show_thoughts"] = False
            if cli_args.theme: self.config["theme"] = cli_args.theme
            
        self.menu_state = "MAIN"; self.selected_index = 0; self.last_error = ""
        self.original_theme = self.config.get("theme", "one_dark")

class StratosDashboard:
    def __init__(self, cli_args=None):
        self.state = StratosState(cli_args); self.console = Console()
        self.cli_args = cli_args

    def handle_action(self, action_id):
        if action_id == "EXIT": sys.exit(0)
        if action_id == "SETTINGS": self.state.menu_state = "SETTINGS"; self.state.selected_index = 0; return False
        if action_id == "AUTH": self.state.menu_state = "AUTH"; self.state.selected_index = 0; return False
        if action_id == "THEME_MENU": self.state.menu_state = "THEME_MENU"; self.state.selected_index = 0; return False
        if action_id == "THEME_MODE": self.state.menu_state = "THEME_MODE"; self.state.selected_index = 0; return False
        if action_id == "THEME_SELECT": self.state.menu_state = "THEME_SELECT"; self.state.selected_index = 0; return False
        if action_id == "BACK": self.state.menu_state = "MAIN"; self.state.selected_index = 1; return False
        if action_id == "BACK_SETTINGS": self.state.menu_state = "SETTINGS"; self.state.selected_index = 1; return False
        if action_id == "BACK_THEME": self.state.config["theme"] = self.state.original_theme; self.state.menu_state = "THEME_MENU"; self.state.selected_index = 0; return False
        
        if action_id == "PATH":
            pass # Handled in run() loop
        elif action_id == "THOUGHTS": self.state.config["show_thoughts"] = not self.state.config.get("show_thoughts", True)
        elif action_id == "DEBUG": self.state.config["debug_mode"] = not self.state.config.get("debug_mode", False)
        elif action_id == "DISPLAY_MODE":
            self.state.config["display_mode"] = "console" if self.state.config.get("display_mode") == "dashboard" else "dashboard"
        elif action_id == "SHOW_RESULTS":
            self.state.config["show_results"] = not self.state.config.get("show_results", True)
        elif action_id == "key":
            pass # Handled in run() loop
        current_theme = self.state.config.get("theme", "one_dark")
        c_pal = current_theme.rsplit("_", 1)[0]; c_mod = current_theme.split("_")[-1]
        if action_id == "MODE_DARK": self.state.config["theme"] = f"{c_pal}_dark"; self.state.original_theme = self.state.config["theme"]
        elif action_id == "MODE_LIGHT": self.state.config["theme"] = f"{c_pal}_light"; self.state.original_theme = self.state.config["theme"]
        elif action_id in [opt["id"] for opt in MENUS["THEME_SELECT"]["options"]]:
            self.state.config["theme"] = f"{action_id}_{c_mod}"; self.state.original_theme = self.state.config["theme"]
        save_config(self.state.config)
        return True

    def get_filtered_options(self):
        options = MENUS[self.state.menu_state]["options"]
        if self.state.menu_state == "THEME_SELECT":
            current_theme = self.state.config.get("theme", "one_dark")
            is_dark = current_theme.endswith("_dark")
            # Filter out 'xcode' if we are in dark mode (it only has a light version)
            if is_dark:
                return [opt for opt in options if opt["id"] != "xcode"]
        return options

    def run(self):
        toggles = ["THOUGHTS", "DEBUG", "DISPLAY_MODE", "SHOW_RESULTS"]
        while True:
            options = self.get_filtered_options()
            # Boundary check for selected_index after filtering
            self.state.selected_index = min(self.state.selected_index, len(options) - 1)
            
            with Live(render_launch_dashboard(self.state, options), refresh_per_second=10, screen=True) as live:
                while True:
                    try: key = readchar.readkey()
                    except KeyboardInterrupt: sys.exit(0)
                    
                    if key == "\x1b" or key == readchar.key.ESC:
                        back_opt = next((o for o in options if "BACK" in o["id"]), None)
                        if back_opt: self.handle_action(back_opt["id"]); break
                        continue
                    
                    if key == readchar.key.UP: self.state.selected_index = (self.state.selected_index - 1) % len(options)
                    elif key == readchar.key.DOWN: self.state.selected_index = (self.state.selected_index + 1) % len(options)
                    elif key == readchar.key.ENTER:
                        opt = options[self.state.selected_index]
                        if opt["id"] in toggles: continue 
                        if opt["id"] == "LAUNCH":
                            live.stop(); self.console.clear()
                            
                            if not self.state.config.get("use_adc"):
                                api_key = get_env_var("GEMINI_API_KEY")
                                if not api_key:
                                    self.console.print(get_banner(get_palette(self.state.config.get("theme", "one_dark"))))
                                    self.console.print("\n[bold yellow] Configuration: GEMINI_API_KEY not found.[/bold yellow]")
                                    api_key = Prompt.ask(" Enter your Google Gemini API Key", password=True)
                                    if not api_key:
                                        self.console.print("[bold red]ERROR: API Key is required to proceed.[/bold red]")
                                        sys.exit(1)
                                    try:
                                        from stratos.utils.config import save_env_var
                                        save_env_var("GEMINI_API_KEY", api_key)
                                        self.console.print("[dim]API Key saved to global config[/dim]")
                                        from dotenv import load_dotenv; load_dotenv()
                                    except Exception: pass

                            palette = get_palette(self.state.config.get("theme", "one_dark"))
                            styles = get_styles(palette)
                            display_mode = self.state.config.get("display_mode", "dashboard")

                            if display_mode == "dashboard":
                                init_content = Text("\n Specify project details to begin development mission.\n Use '*' for quick MVP testing.\n", style=styles["dim"])
                                self.console.print(get_banner(palette))
                                self.console.print(make_gradient_panel(init_content, title=" MISSION INITIALIZATION ", palette=palette, expand=False))
                                p_name = Prompt.ask(f"\n [bold {styles['accent']}]› PROJECT_NAME[/]")
                            else:
                                self.console.print(f"\n[bold {styles['accent']}]› MISSION INITIALIZATION[/]")
                                self.console.print(f"[dim]Use '*' for quick MVP testing[/dim]\n")
                                p_name = Prompt.ask(f"[bold {styles['accent']}]› PROJECT_NAME[/]")

                            p_desc = "MVP_TEST: Create a simple HTML/JS clock." if p_name == "*" else Prompt.ask(f" [bold {styles['accent']}]› DESCRIPTION[/]")
                            run_stratos(p_name, p_desc); break
                        
                        if opt["id"] == "PATH":
                            # Try GUI first, then Terminal Fallback
                            res = None
                            try:
                                # Zenity (GTK)
                                res = subprocess.run(["zenity", "--file-selection", "--directory", "--title=STRATOS"], capture_output=True, text=True).stdout.strip()
                                if not res: # kdialog (Qt)
                                    res = subprocess.run(["kdialog", "--getexistingdirectory", "."], capture_output=True, text=True).stdout.strip()
                            except: pass
                            
                            if not res:
                                # TERMINAL FALLBACK within the dashboard aesthetic
                                live.stop(); self.console.clear()
                                palette = get_palette(self.state.config.get("theme", "one_dark"))
                                styles = get_styles(palette)
                                path_content = Text(f"\n Select the root directory where your projects are stored.\n Current: {self.state.config.get('projects_path')}\n", style=styles["dim"])
                                self.console.print(get_banner(palette))
                                self.console.print(make_gradient_panel(path_content, title=" DIRECTORY CONFIGURATION ", palette=palette, expand=False))
                                res = Prompt.ask(f"\n [bold {styles['accent']}]› ENTER ABSOLUTE PATH[/]")
                            
                            if res and os.path.isdir(os.path.expanduser(res)):
                                self.state.config["projects_path"] = os.path.expanduser(res)
                                save_config(self.state.config)
                            break

                        if opt["id"] == "key":
                            live.stop(); self.console.clear()
                            palette = get_palette(self.state.config.get("theme", "one_dark"))
                            styles = get_styles(palette)
                            setup_content = Text("\n Updating Gemini access credentials.\n Your key will be securely saved in the global config directory.\n", style=styles["dim"])
                            self.console.print(get_banner(palette))
                            self.console.print(make_gradient_panel(setup_content, title=" IDENTITY SETUP ", palette=palette, expand=False))
                            key = Prompt.ask(f"\n [bold {styles['accent']}]› ENTER GEMINI_API_KEY[/]")
                            if key:
                                from stratos.utils.config import save_env_var
                                save_env_var("GEMINI_API_KEY", key)
                                self.state.last_error = ""
                            if self.handle_action(opt["id"]):
                                self.state.menu_state = "SETTINGS"; self.state.selected_index = 4
                            break

                        if self.handle_action(opt["id"]):
                            if self.state.menu_state in ["THEME_SELECT", "THEME_MODE"]: self.state.menu_state = "THEME_MENU"; self.state.selected_index = 0
                            elif self.state.menu_state == "AUTH": self.state.menu_state = "SETTINGS"; self.state.selected_index = 4
                            elif self.state.menu_state == "SETTINGS": self.state.menu_state = "MAIN"; self.state.selected_index = 1
                        break 
                    elif key == " ":
                        opt = options[self.state.selected_index]
                        if opt["id"] in toggles: self.handle_action(opt["id"]); live.update(render_launch_dashboard(self.state, options))
                    
                    if self.state.menu_state == "THEME_SELECT":
                        h_id = options[self.state.selected_index]["id"]
                        if h_id != "BACK_THEME":
                            c_m = self.state.config.get("theme", "one_dark").split("_")[-1]
                            self.state.config["theme"] = f"{h_id}_{c_m}"
                    elif self.state.menu_state == "THEME_MODE":
                        h_id = options[self.state.selected_index]["id"]
                        if h_id != "BACK_THEME":
                            t_m = "dark" if h_id == "MODE_DARK" else "light"
                            c_p = self.state.config.get("theme", "one_dark").rsplit("_", 1)[0]
                            self.state.config["theme"] = f"{c_p}_{t_m}"
                    live.update(render_launch_dashboard(self.state, options))
