import time
from rich.text import Text
from rich.layout import Layout
from rich.table import Table
from rich.syntax import Syntax
from rich.align import Align
from rich.spinner import Spinner
from rich.tree import Tree
from stratos.ui.components.core import get_styles, get_palette, MENUS
from stratos.ui.components.panels import make_gradient_panel
from stratos.ui.components.banner import get_banner
from stratos.utils.config import get_env_var, get_user_id
from stratos import __version__

def get_user_header(palette, config):
    user = get_user_id()
    active_engine = config.get("active_engine")
    if not active_engine:
        styles = get_styles(palette)
        header = Text()
        header.append(f"Logged in as: ", style=styles["base"])
        header.append(f"{user} ", style="bold " + styles["accent"])
        header.append(f"  Status: ", style=styles["base"])
        header.append(f"NO ENGINE SELECTED", style="bold #FF0000")
        return header
        
    api_key = get_env_var(active_engine)
    styles = get_styles(palette)
    header = Text()
    header.append(f"Logged in as: ", style=styles["base"])
    header.append(f"{user} ", style="bold " + styles["accent"])
    if api_key: header.append(f"  Status: ", style=styles["base"]); header.append(f"Authenticated ({active_engine})", style="bold #00FF00")
    else: header.append(f"  Status: ", style=styles["base"]); header.append(f"{active_engine} Identity Config Required", style="bold #FF0000")
    return header

def get_notification(state, palette):
    styles = get_styles(palette)
    if state.last_error: return Text(f"ERROR: {state.last_error}", style="bold #FF0000")
    return Text(f"STRATOS CORE: READY", style=f"bold {styles['accent']}")

def get_status_content(palette, config):
    path = config.get("projects_path", "projects")
    if len(path) > 30: path = "..." + path[-27:]
    
    active_engine = config.get("active_engine")
    engine_label = active_engine.upper() if active_engine else "NOT SELECTED"
    
    styles = get_styles(palette)
    status = Text("\n", style=styles["base"])
    labels = ["Projects Path", "Active Theme", "Display Mode", "Active Engine", "Result Preview", "Thought Flow", "Debug Mode"]
    values = [path, config.get("theme", "one_dark").upper(), 
              config.get("display_mode", "dashboard").upper(),
              engine_label,
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

def get_engine_preview_content(provider, palette):
    import json
    import os
    from stratos.assets import ASSETS_DIR
    styles = get_styles(palette)
    provider = provider.upper()
    
    try:
        path = os.path.join(ASSETS_DIR, "engines.json")
        with open(path, "r") as f:
            engines_data = json.load(f)
            engine_conf = engines_data.get(provider, {})
            models = engine_conf.get("models", {})
            
            tree = Tree(f"[bold {styles['accent']}]{provider} ENGINE CORE", guide_style=styles["accent"])
            
            tiers = [
                ("HEAVY", "Strategy & Planning", "bold #FFD700"), 
                ("MEDIUM", "Architecture & Implementation", "bold #C0C0C0"), 
                ("LIGHT", "Audit & Review", "bold #CD7F32")
            ]
            
            for tier, desc, color in tiers:
                m_name = models.get(tier, "Unknown")
                branch = tree.add(f"[{color}]{tier}[/] : [bold white]{m_name}[/]")
                branch.add(f"[dim italic]{desc}[/]")
            
            return tree
            
    except Exception as e:
        return Text(f"Error loading engine tiers: {str(e)}", style="bold #FF0000")

def render_launch_dashboard(state, options=None, input_panel=None, loading=False):
    current_theme_id = state.config.get("theme", "one_dark")
    palette = get_palette(current_theme_id)
    styles = get_styles(palette)
    menu_data = MENUS[state.menu_state]
    
    if options is None:
        options = menu_data["options"]
        
    layout = Layout()
    
    main_column = [
        Layout(get_banner(palette), size=11),
        Layout(get_user_header(palette, state.config), size=1),
        Layout(get_notification(state, palette), size=1),
        Layout(make_gradient_panel(Text("> " + menu_data['path'], style=styles["base"]), palette=palette), size=3),
        Layout(name="main", ratio=1)
    ]
    
    if input_panel:
        main_column.append(Layout(input_panel, size=3))
        
    layout.split_column(*main_column)
    
    toggles = ["THOUGHTS", "DEBUG", "DISPLAY_MODE", "SHOW_RESULTS"]
    sel_idx = min(state.selected_index, len(options) - 1)
    
    menu_text = Text("\n")
    
    if loading:
        loading_area = Table.grid()
        loading_area.add_row(Text("\n"))
        loading_area.add_row(Spinner("dots", text=Text(" Fetching API data...", style=styles["base"]), style=f"bold {styles['accent']}"))
        nav_panel_content = loading_area
        nav_footer = " PLEASE WAIT "
    else:
        opt = options[sel_idx]
        nav_footer = " [SPACE] TOGGLE " if opt["id"] in toggles else " [ENTER/ESC] BACK " if "BACK" in opt["id"] else " [ENTER] SELECT "
        
        for i, opt_in in enumerate(options):
            label_raw = opt_in['label']
            desc_raw = opt_in['desc']
            
            label_rich = Text.from_markup(label_raw)
            desc_rich = Text.from_markup(desc_raw)
            
            if len(label_rich) < 32:
                label_rich.append(" " * (32 - len(label_rich)))
            elif len(label_rich) > 32:
                label_rich.truncate(32)

            if i == sel_idx:
                menu_text.append(f" • ", style=f"bold {styles['accent']}")
                label_rich.style = styles["base"] if not label_rich.style else label_rich.style
                menu_text.append(label_rich)
                menu_text.append(" ")
                desc_rich.style = f"bold {styles['accent']}"
                menu_text.append(desc_rich)
                menu_text.append("\n")
            else:
                menu_text.append(f"    ", style=styles["dim"])
                label_rich.style = styles["dim"]
                menu_text.append(label_rich)
                menu_text.append(" ")
                desc_rich.style = styles["dim"]
                menu_text.append(desc_rich)
                menu_text.append("\n")
        nav_panel_content = menu_text
            
    if state.menu_state in ["THEME_SELECT", "THEME_MODE"]:
        hovered_opt = options[sel_idx]
        p_id, p_pal = (state.original_theme, get_palette(state.original_theme)) if "BACK" in hovered_opt["id"] else (current_theme_id, palette)
        right_content = get_theme_preview_content(p_id, p_pal)
        right_title = " THEME PREVIEW "
        right_footer = ""
    elif state.menu_state == "AI_SELECT":
        hovered_opt = options[sel_idx]
        if hovered_opt["id"].startswith("SET_") or hovered_opt["id"].startswith("ENGINE_CONFIG_"):
            p_raw = hovered_opt["id"].replace("SET_", "").replace("ENGINE_CONFIG_", "")
            right_content = get_engine_preview_content(p_raw, palette)
            right_title = f" {p_raw.upper()} CONFIGURATION "
            right_footer = " Active models per tier "
        else:
            right_content = get_status_content(palette, state.config)
            right_title = " SYSTEM STATUS "
            right_footer = f" STRATOS CORE v{__version__} "
    else:
        right_content = get_status_content(palette, state.config)
        right_title = " SYSTEM STATUS "
        right_footer = f" STRATOS CORE v{__version__} "
        
    nav_panel = make_gradient_panel(
        nav_panel_content, title=" NAVIGATION ", footer=nav_footer, 
        palette=palette, expand=False, padding=(1, 4)
    )
    status_panel = make_gradient_panel(
        right_content, title=right_title, footer=right_footer, 
        palette=palette, expand=False, padding=(1, 4)
    )
    
    main_grid = Table.grid(expand=True)
    main_grid.add_column(ratio=1); main_grid.add_column(); main_grid.add_column(width=6); main_grid.add_column(); main_grid.add_column(ratio=1)
    main_grid.add_row(None, nav_panel, None, status_panel, None)
    
    layout["main"].update(Align.center(main_grid))
    
    return layout
