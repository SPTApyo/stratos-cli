import os
import sys
import time
import select
import termios
import subprocess
from rich.console import Console
from rich.live import Live
from rich.text import Text
from rich.align import Align

from stratos.utils.config import load_config, save_config, get_env_var, save_env_var
from stratos.ui.components.core import MENUS, get_palette, get_styles
from stratos.ui.components.panels import make_gradient_panel, make_input_panel
from stratos.ui.components.banner import get_banner
from stratos.ui.views.launch_view import render_launch_dashboard
from stratos.core.engine import run_stratos

class StratosState:
    def __init__(self, cli_args=None):
        self.config = load_config()
        if cli_args:
            if cli_args.debug: self.config["debug_mode"] = True
            if cli_args.no_thoughts: self.config["show_thoughts"] = False
            if cli_args.theme: self.config["theme"] = cli_args.theme
        self.menu_state = "MAIN"; self.selected_index = 0; self.last_error = ""
        self.original_theme = self.config.get("theme", "one_dark")
        self.mission_mode = "NEW"

class StratosDashboard:
    def __init__(self, cli_args=None):
        self.state = StratosState(cli_args); self.console = Console()
        self.cli_args = cli_args
        self.should_exit_dashboard = False

    def _navigate_back(self):
        current_menu = MENUS.get(self.state.menu_state)
        if not current_menu: return
        current_path = current_menu.get("path", "/main")
        if current_path == "/main": return
        parent_path = "/".join(current_path.split("/")[:-1])
        if not parent_path: parent_path = "/main"
        for key, menu in MENUS.items():
            if menu.get("path") == parent_path:
                self.state.menu_state = key; self.selected_index = 0; return

    def handle_action(self, action_id, live=None):
        if action_id == "EXIT": sys.exit(0)
        if action_id in MENUS: self.state.menu_state = action_id; self.state.selected_index = 0; return True
        if action_id.startswith("BACK"): self._navigate_back(); return True
        
        if action_id == "NEW_PROJECT" or action_id.startswith("MISSION_"):
            self.should_exit_dashboard = True
            if live: live.stop()
            if action_id == "NEW_PROJECT": self._launch_new_project(live)
            else: self._launch_existing_project(action_id.replace("MISSION_", ""), live)
            return False

        if action_id == "PATH":
            self._change_path(live); return False

        if action_id == "key":
            self._update_api_key(live); return False

        if action_id.startswith("SET_"):
            provider = action_id.replace("SET_", "")
            self.state.config["active_engine"] = provider
            save_config(self.state.config)
            return True

        if action_id.startswith("ENGINE_CONFIG_"):
            provider = action_id.replace("ENGINE_CONFIG_", "")
            return self._show_engine_tiers(provider, live)

        if action_id.startswith("TIER_CONFIG_"):
            # action_id is TIER_CONFIG_{provider}_{tier}
            parts = action_id.split("_")
            provider = parts[2]
            tier = parts[3]
            return self._show_model_list(provider, tier, live)

        if action_id.startswith("FAMILY_CONFIG_"):
            # action_id is FAMILY_CONFIG_{provider}_{tier}_{family}
            _, _, provider, tier, family = action_id.split("_", 4)
            return self._show_family_models(provider, tier, family, live)

        if action_id.startswith("SELECT_MODEL_"):
            _, _, provider, tier, model = action_id.split("_", 4)
            from stratos.core.engines.factory import EngineFactory
            EngineFactory.save_engine_config(provider, tier, model)
            return "TO_TIERS" 

        if action_id == "THOUGHTS": self.state.config["show_thoughts"] = not self.state.config.get("show_thoughts", True)
        elif action_id == "DEBUG": self.state.config["debug_mode"] = not self.state.config.get("debug_mode", False)
        elif action_id == "DISPLAY_MODE":
            self.state.config["display_mode"] = "console" if self.state.config.get("display_mode") == "dashboard" else "dashboard"
        elif action_id == "SHOW_RESULTS":
            self.state.config["show_results"] = not self.state.config.get("show_results", True)
        
        current_theme = self.state.config.get("theme", "one_dark")
        c_pal = current_theme.rsplit("_", 1)[0]; c_mod = current_theme.split("_")[-1]
        if action_id == "MODE_DARK": self.state.config["theme"] = f"{c_pal}_dark"; self.state.original_theme = self.state.config["theme"]
        elif action_id == "MODE_LIGHT": self.state.config["theme"] = f"{c_pal}_light"; self.state.original_theme = self.state.config["theme"]
        elif action_id in [opt["id"] for opt in MENUS["THEME_SELECT"]["options"]]:
            self.state.config["theme"] = f"{action_id}_{c_mod}"; self.state.original_theme = self.state.config["theme"]
        
        save_config(self.state.config); return True

    def run(self):
        fd = sys.stdin.fileno(); old_settings = termios.tcgetattr(fd)
        try:
            sys.stdout.write("\x1b[?1003h\x1b[?1006h"); sys.stdout.flush()
            while not self.should_exit_dashboard:
                options = self.get_filtered_options()
                self.state.selected_index = min(self.state.selected_index, len(options) - 1)
                with Live(render_launch_dashboard(self.state, options), refresh_per_second=15, screen=True) as live:
                    new_settings = termios.tcgetattr(fd)
                    new_settings[3] = new_settings[3] & ~(termios.ECHO | termios.ICANON)
                    termios.tcsetattr(fd, termios.TCSADRAIN, new_settings)
                    if not self._menu_loop(fd, live):
                        if self.should_exit_dashboard: break
        finally:
            sys.stdout.write("\x1b[?1003l\x1b[?1006l"); sys.stdout.flush()
            termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)

    def _menu_loop(self, fd, live):
        self.should_exit_menu = False
        while not self.should_exit_menu:
            options = self.get_filtered_options()
            if options:
                self.state.selected_index = max(0, min(self.state.selected_index, len(options) - 1))
            
            if select.select([sys.stdin], [], [], 0.05)[0]:
                keys = os.read(fd, 1024).decode('utf-8', errors='ignore')
                if keys == '\x1b': self._handle_esc(options, live)
                elif keys.startswith('\x1b[<'): self._handle_mouse(keys, options, live)
                else:
                    if keys.startswith('\x1b['): self._handle_key(keys, options, live)
                    else:
                        for char in keys: self._handle_key(char, options, live)
                
                if not live.is_started: return False

                options = self.get_filtered_options()
                if self.state.menu_state == "THEME_SELECT":
                    h_id = options[self.state.selected_index]["id"]
                    if h_id not in ["BACK", "BACK_THEME", "BACK_SETTINGS"]:
                        c_m = self.state.original_theme.split("_")[-1]
                        self.state.config["theme"] = f"{h_id}_{c_m}"
                    else: self.state.config["theme"] = self.state.original_theme
                elif self.state.menu_state == "THEME_MODE":
                    h_id = options[self.state.selected_index]["id"]
                    if h_id in ["MODE_DARK", "MODE_LIGHT"]:
                        t_m = "dark" if h_id == "MODE_DARK" else "light"
                        c_p = self.state.original_theme.rsplit("_", 1)[0]
                        self.state.config["theme"] = f"{c_p}_{t_m}"
                    else: self.state.config["theme"] = self.state.original_theme
                live.update(render_launch_dashboard(self.state, options))
            time.sleep(0.01)
        return True

    def _handle_mouse(self, sequence, options, live):
        try:
            suffix = sequence[-1]; parts = sequence[3:-1].split(';'); button = int(parts[0]); x = int(parts[1]); y = int(parts[2])
            clicked_row = y - 20
            if 0 <= clicked_row < len(options):
                self.state.selected_index = clicked_row
                if suffix == 'M' and button == 0:
                    opt = options[clicked_row]
                    interaction = opt.get("interaction") or {"trigger": "enter", "back": False}
                    should_continue = self.handle_action(opt["id"], live)
                    if interaction.get("back"): self._navigate_back()
                    elif not should_continue: self.should_exit_menu = True
            if suffix == 'M':
                if button == 64: self.state.selected_index = (self.state.selected_index - 1) % len(options)
                elif button == 65: self.state.selected_index = (self.state.selected_index + 1) % len(options)
        except: pass

    def _handle_key(self, key, options, live):
        if not options: return
        self.state.selected_index = max(0, min(self.state.selected_index, len(options) - 1))
        
        if '\x1b[A' in key: self.state.selected_index = (self.state.selected_index - 1) % len(options)
        elif '\x1b[B' in key: self.state.selected_index = (self.state.selected_index + 1) % len(options)
        elif key == '\x1b': self._handle_esc(options, live)
        else:
            opt = options[self.state.selected_index]
            interaction = opt.get("interaction") or {"trigger": "enter", "back": False}
            trigger_key = '\r' if interaction.get("trigger") == "enter" else ' '
            if key == trigger_key or (trigger_key == '\r' and key == '\n'):
                should_continue = self.handle_action(opt["id"], live)
                if interaction.get("back"): self._navigate_back()
                elif not should_continue: self.should_exit_menu = True

    def _handle_esc(self, options, live):
        shortcut = MENUS.get("GLOBAL_SHORTCUTS", {}).get("escape", {})
        if shortcut.get("action") == "BACK": self._navigate_back()

    def get_filtered_options(self):
        options = MENUS[self.state.menu_state]["options"]
        if self.state.menu_state == "THEME_SELECT":
            is_dark = self.state.config.get("theme", "one_dark").endswith("_dark")
            if is_dark: return [opt for opt in options if opt["id"] != "xcode"]
        return options

    def _pick_directory(self, title, default_path, live):
        res = None
        try:
            p = subprocess.run(["zenity", "--file-selection", "--directory", f"--title={title}"], capture_output=True, text=True)
            if p.returncode == 0: res = p.stdout.strip()
            elif p.returncode == 1: return None
        except: pass
        
        if not res:
            try:
                p = subprocess.run(["kdialog", "--getexistingdirectory", default_path, "--title", title], capture_output=True, text=True)
                if p.returncode == 0: res = p.stdout.strip()
            except: pass

        if not res:
            if live and live.is_started: live.stop()
            palette = get_palette(self.state.config.get("theme", "one_dark"))
            res = self.custom_prompt(f"› {title}", palette, default=default_path)
        return res

    def _launch_new_project(self, live):
        palette = get_palette(self.state.config.get("theme", "one_dark"))
        active_engine = self.state.config.get("active_engine")
        if not active_engine:
            self.state.last_error = "NO AI ENGINE SELECTED. Go to Settings > AI Engine."
            return
            
        if not get_env_var(active_engine):
            if live and live.is_started: live.stop()
            p = self.custom_prompt(f"ENTER {active_engine} API KEY", palette, password=True)
            if p: save_env_var(f"STRATOS_{active_engine}_API_KEY", p)
            else: return
        if live and live.is_started: live.stop()
        p_name = self.custom_prompt("› NEW PROJECT NAME", palette)
        if not p_name: return
        
        if p_name == "*":
            from stratos.utils.config import QUICK_MISSION_DESC
            p_desc = QUICK_MISSION_DESC
        else:
            p_desc = self.custom_prompt("› DESCRIPTION", palette, default="MISSION: ")
            if not p_desc: return
            
        run_stratos(p_name, p_desc)

    def _launch_existing_project(self, mode, live):
        palette = get_palette(self.state.config.get("theme", "one_dark"))
        active_engine = self.state.config.get("active_engine")
        if not active_engine:
            self.state.last_error = "NO AI ENGINE SELECTED. Go to Settings > AI Engine."
            return
            
        if not get_env_var(active_engine):
            if live and live.is_started: live.stop()
            p = self.custom_prompt(f"ENTER {active_engine} API KEY", palette, password=True)
            if p: save_env_var(f"STRATOS_{active_engine}_API_KEY", p)
            else: return
        e_path = self._pick_directory("MISSION TARGET FOLDER", self.state.config.get("projects_path", ""), live)
        if not e_path or not os.path.isdir(os.path.expanduser(e_path)): return
        if live and live.is_started: live.stop()
        p_name = os.path.basename(os.path.abspath(os.path.expanduser(e_path)))
        prefix_map = {"REFACTOR": "REFACTORING_MISSION: ", "IMPROVE": "EVOLUTION_MISSION: ", "ANALYZE": "ANALYSIS_MISSION: ", "DOCS": "DOCUMENTATION_MISSION: ", "COMMENTS": "DOCUMENTATION_MISSION: "}
        p_desc = self.custom_prompt("› MISSION OBJECTIVE", palette, default=prefix_map.get(mode, f"{mode}_MISSION: "))
        if not p_desc: return
        run_stratos(p_name, p_desc, existing_path=e_path)

    def _change_path(self, live):
        res = self._pick_directory("PROJECTS PATH", self.state.config.get("projects_path", ""), live)
        if res and os.path.isdir(os.path.expanduser(res)):
            self.state.config["projects_path"] = os.path.expanduser(res)
            save_config(self.state.config)

    def _update_api_key(self, live):
        if live and live.is_started: live.stop()
        palette = get_palette(self.state.config.get("theme", "one_dark"))
        active_engine = self.state.config.get("active_engine")
        if not active_engine:
            self.state.last_error = "NO AI ENGINE SELECTED. Go to Settings > AI Engine."
            return
            
        key = self.custom_prompt(f"› {active_engine}_API_KEY", palette, password=True)
        if key: save_env_var(f"STRATOS_{active_engine}_API_KEY", key)

    def _has_gui(self):
        try: return subprocess.run(["which", "zenity"], capture_output=True).returncode == 0
        except: return False

    def _show_engine_tiers(self, provider, live):
        from stratos.core.engines.factory import EngineFactory
        tiers = EngineFactory.get_tier_models(provider)
        
        options = []
        options.append({
            "id": f"SET_{provider}",
            "label": "[bold green]ACTIVATE[/]",
            "desc": f"Set {provider} as active engine"
        })
        for t, m in tiers.items():
            options.append({
                "id": f"TIER_CONFIG_{provider}_{t}",
                "label": t,
                "desc": f"Current: {m}"
            })
        options.append({"id": "BACK_SETTINGS", "label": "BACK", "desc": "Return to settings"})
        
        return self._run_dynamic_menu(f"{provider} TIERS", options, live)

    def _show_model_list(self, provider, tier, live):
        from stratos.core.engines.factory import EngineFactory
        live.update(render_launch_dashboard(self.state, loading=True))
        
        models = []
        error_msg = ""
        try:
            key = get_env_var(provider)
            if not key: raise ValueError(f"No API key found for {provider}")
            engine = EngineFactory.create_engine(provider, tier, key)
            models = engine.list_models()
        except Exception as e:
            error_msg = f"API ERROR: {str(e)}"

        if error_msg:
            options = [{"id": "ERROR", "label": "[bold red]FAILED[/]", "desc": error_msg}]
            options.append({"id": "BACK_SETTINGS", "label": "BACK", "desc": "Return to tiers"})
            self._run_dynamic_menu(f"SELECT {tier} MODEL", options, live)
            return

        families = {}
        for m in models:
            family = "Other"
            m_lower = m.lower()
            if provider.upper() == "CLAUDE":
                if "opus" in m_lower: family = "Opus"
                elif "sonnet" in m_lower: family = "Sonnet"
                elif "haiku" in m_lower: family = "Haiku"
            elif provider.upper() == "OPENAI":
                if "gpt-4" in m_lower: family = "GPT-4"
                elif "gpt-3.5" in m_lower: family = "GPT-3.5"
                elif "o1" in m_lower: family = "o1"
                elif "o3" in m_lower: family = "o3"
                else: family = "Experimental"
            elif provider.upper() == "GEMINI":
                if "flash" in m_lower: family = "Flash"
                elif "pro" in m_lower: family = "Pro"
                elif "nano" in m_lower: family = "Nano"
                elif "research" in m_lower: family = "Research"
                elif "gemma" in m_lower: family = "Gemma"
                elif "robotics" in m_lower: family = "Robotics"
                elif "compute" in m_lower: family = "Compute"
                elif "learnlm" in m_lower: family = "LearnLM"
                elif "aqa" in m_lower: family = "AQA"
                else: family = "Experimental"
            
            if family not in families: families[family] = []
            families[family].append(m)

        if len(families) <= 1:
            return self._show_family_models(provider, tier, list(families.keys())[0] if families else "Models", live, models_override=models)

        options = []
        for f in sorted(families.keys()):
            options.append({
                "id": f"FAMILY_CONFIG_{provider}_{tier}_{f}",
                "label": f.upper(),
                "desc": f"View {len(families[f])} models in this family"
            })
        options.append({"id": "BACK_SETTINGS", "label": "BACK", "desc": "Return to tiers"})
        
        self.state._temp_families = families 
        return self._run_dynamic_menu(f"SELECT {provider} FAMILY", options, live)

    def _show_family_models(self, provider, tier, family, live, models_override=None):
        import re
        families = getattr(self.state, '_temp_families', {})
        models = models_override or families.get(family, [])
        
        def natural_sort_key(s):
            return [int(text) if text.isdigit() else text.lower()
                    for text in re.split('([0-9]+)', s)]
        
        models.sort(key=natural_sort_key, reverse=True)
        
        options = []
        for m in models:
            options.append({
                "id": f"SELECT_MODEL_{provider}_{tier}_{m}",
                "label": m[:30],
                "desc": f"Set as {tier} model"
            })
        options.append({"id": "BACK_SETTINGS", "label": "BACK", "desc": "Return to families"})
        return self._run_dynamic_menu(f"{family.upper()} MODELS", options, live)

    def _run_dynamic_menu(self, title, options, live):
        """Runs a blocking sub-menu loop with dynamic options and mouse support."""
        local_idx = 0
        
        while True:
            self.state.selected_index = local_idx
            live.update(render_launch_dashboard(self.state, options=options))
            
            if select.select([sys.stdin], [], [], 0.05)[0]:
                keys = os.read(sys.stdin.fileno(), 1024).decode('utf-8', errors='ignore')
                
                if keys.startswith('\x1b[<'):
                    try:
                        suffix = keys[-1]; parts = keys[3:-1].split(';'); button = int(parts[0]); x = int(parts[1]); y = int(parts[2])
                        clicked_row = y - 20 
                        if 0 <= clicked_row < len(options):
                            local_idx = clicked_row
                            self.state.selected_index = local_idx
                            if suffix == 'M' and button == 0:
                                opt = options[clicked_row]
                                if opt["id"] == "BACK_SETTINGS": return "BACK"
                                res = self.handle_action(opt["id"], live)
                                
                                if res == "TO_TIERS":
                                    if "MODELS" in title: return "TO_TIERS"
                                    return False
                                    
                                if res == "BACK": continue
                                if res != False: return res
                        if suffix == 'M':
                            if button == 64: local_idx = (local_idx - 1) % len(options)
                            elif button == 65: local_idx = (local_idx + 1) % len(options)
                    except: pass
                
                elif '\x1b[A' in keys: local_idx = (local_idx - 1) % len(options)
                elif '\x1b[B' in keys: local_idx = (local_idx + 1) % len(options)
                elif keys in ['\r', '\n']:
                    opt = options[local_idx]
                    if opt["id"] == "BACK_SETTINGS": return "BACK"
                    res = self.handle_action(opt["id"], live)
                    
                    if res == "TO_TIERS":
                        if "MODELS" in title: return "TO_TIERS"
                        return False 
                        
                    if res == "BACK": continue
                    if res != False: return res 
                elif keys == '\x1b': return "BACK"
            
            time.sleep(0.01)

    def custom_prompt(self, label, palette, default="", password=False):
        input_text = default; cursor_pos = len(input_text)
        with Live(auto_refresh=False, screen=True) as live:
            while True:
                options = self.get_filtered_options()
                input_panel = make_input_panel(label, input_text, cursor_pos, password)
                live.update(render_launch_dashboard(self.state, options, input_panel=input_panel))
                live.refresh()
                if select.select([sys.stdin], [], [], 0.1)[0]:
                    k = os.read(sys.stdin.fileno(), 1024).decode('utf-8', errors='ignore')
                    if k in ['\r', '\n']: return input_text
                    if k == '\x7f':
                        if cursor_pos > 0: input_text = input_text[:cursor_pos-1] + input_text[cursor_pos:]; cursor_pos -= 1
                    elif k == '\x1b[D': cursor_pos = max(0, cursor_pos - 1)
                    elif k == '\x1b[C': cursor_pos = min(len(input_text), cursor_pos + 1)
                    elif k.isprintable() and not k.startswith('\x1b'): 
                        input_text = input_text[:cursor_pos] + k + input_text[cursor_pos:]; cursor_pos += len(k)
