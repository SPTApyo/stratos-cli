import time
from rich.text import Text
from rich.layout import Layout
from rich.table import Table
from rich.syntax import Syntax
from stratos.ui.components.core import get_styles, get_palette, MENUS
from stratos.ui.components.panels import make_gradient_panel
from stratos.ui.components.banner import get_banner
from stratos.utils.config import get_env_var, get_user_id
from stratos import __version__

def get_user_header(palette, config):
    user = get_user_id()
    api_key = get_env_var("GEMINI_API_KEY")
    styles = get_styles(palette)
    header = Text()
    header.append(f"Logged in as: ", style=styles["base"])
    header.append(f"{user} ", style="bold " + styles["accent"])
    if api_key: header.append(f"  Status: ", style=styles["base"]); header.append(f"Authenticated", style="bold #00FF00")
    else: header.append(f"  Status: ", style=styles["base"]); header.append(f"Identity Config Required", style="bold #FF0000")
    return header

def get_notification(state, palette):
    styles = get_styles(palette)
    if state.last_error: return Text(f"ERROR: {state.last_error}", style="bold #FF0000")
    return Text(f"STRATOS CORE: READY", style=f"bold {styles['accent']}")

def get_status_content(palette, config):
    path = config.get("projects_path", "projects")
    if len(path) > 30: path = "..." + path[-27:]
    styles = get_styles(palette)
    status = Text("\n", style=styles["base"])
    labels = ["Projects Path", "Active Theme", "Display Mode", "Result Preview", "Thought Flow", "Debug Mode"]
    values = [path, config.get("theme", "one_dark").upper(), 
              config.get("display_mode", "dashboard").upper(),
              "ON" if config.get("show_results", True) else "OFF",
              "ON" if config.get("show_thoughts") else "OFF",
              "ACTIVE" if config.get("debug_mode") else "INACTIVE"]
    for l, v in zip(labels, values):
        status.append(f"{l:<20}", style=styles["base"])
        status.append(f"{v}\n", style=f"bold {styles['accent']}" if v in ["ON", "ACTIVE", "DASHBOARD"] else styles["dim"])
    return status

def get_theme_preview_content(theme_id, palette):
    styles = get_styles(palette)
    pygments_theme = palette.get("pygments", "one-dark")
    t = time.strftime("%H:%M:%S")
    logs = Text("\n")
    logs.append(f" {t} ", style=styles["dim"])
    logs.append(" TASK ", style="bold #FF00FF")
    logs.append(" MISSION COMPLETED\n", style="bold #00FF00")
    code_text = f"@stratos_v2.decorator(theme=\"{theme_id}\")\ndef launch():\n    return True"
    code_preview = Syntax(code_text, "python", theme=pygments_theme, line_numbers=True, background_color="default")
    preview_table = Table.grid(expand=True)
    preview_table.add_row(logs)
    preview_table.add_row(code_preview)
    return preview_table

def render_launch_dashboard(state):
    current_theme_id = state.config.get("theme", "one_dark")
    palette = get_palette(current_theme_id)
    styles = get_styles(palette)
    menu_data = MENUS[state.menu_state]
    layout = Layout()
    
    layout.split_column(
        Layout(get_banner(palette), size=11),
        Layout(get_user_header(palette, state.config), size=2),
        Layout(get_notification(state, palette), size=1),
        Layout(make_gradient_panel(Text("> " + menu_data['path'], style=styles["base"]), palette=palette), size=3),
        Layout(name="main", ratio=1)
    )
    
    toggles = ["THOUGHTS", "DEBUG", "DISPLAY_MODE", "SHOW_RESULTS"]
    opt = menu_data["options"][state.selected_index]
    nav_footer = " [SPACE] TOGGLE " if opt["id"] in toggles else " [ENTER/ESC] BACK " if "BACK" in opt["id"] else " [ENTER] SELECT "
    menu_text = Text("\n")
    
    for i, opt_in in enumerate(menu_data["options"]):
        if i == state.selected_index:
            menu_text.append(f" • ", style=f"bold {styles['accent']}")
            menu_text.append(f"{opt_in['label']:<18} ", style=styles["base"])
            menu_text.append(f" {opt_in['desc']}\n", style=f"bold {styles['accent']}")
        else:
            menu_text.append(f"    {opt_in['label']:<18} ", style=styles["dim"])
            menu_text.append(f" {opt_in['desc']}\n", style=styles["dim"])
            
    if state.menu_state in ["THEME_SELECT", "THEME_MODE"]:
        hovered_opt = menu_data["options"][state.selected_index]
        p_id, p_pal = (state.original_theme, get_palette(state.original_theme)) if "BACK" in hovered_opt["id"] else (current_theme_id, palette)
        right_content = get_theme_preview_content(p_id, p_pal)
        right_title = " THEME PREVIEW "
        right_footer = ""
    else:
        right_content = get_status_content(palette, state.config)
        right_title = " SYSTEM STATUS "
        right_footer = " STRATOS CORE v2.5 "
        
    layout["main"].split_row(
        Layout(make_gradient_panel(menu_text, title=" NAVIGATION ", footer=nav_footer, palette=palette), ratio=2),
        Layout(make_gradient_panel(right_content, title=right_title, footer=right_footer, palette=palette), ratio=3)
    )
    return layout
