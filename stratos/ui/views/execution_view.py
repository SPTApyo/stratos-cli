import time
from rich.text import Text
from rich.layout import Layout
from rich.table import Table
from stratos.ui.components.panels import make_gradient_panel, make_interaction_box

def render_execution_dashboard(logger_state, styles, palette_raw, term_height):
    todo_size = len(logger_state.todo_list) + 2 if logger_state.todo_expanded else 5
    reserved = 3 + todo_size + 8 
    if logger_state.active_prompt: reserved += 8
    max_logs = max(3, term_height - reserved)

    header = Text(f" MISSION: {logger_state.project_path}", style=styles["base"])
    if getattr(logger_state, 'sandbox', None) and getattr(logger_state.sandbox, 'auto_approve', False):
        header.append("  |  AUTO_MODE", style="bold blink green")
    if logger_state.paused: header.append("  |  SYSTEM_PAUSED", style="bold blink red")
    header.append(f"  |  ITERATION: ", style=styles["dim"]); header.append(f"{logger_state.current_cycle}", style="bold " + styles["accent"])
    header.append(f"  |  PROCESSOR: ", style=styles["dim"]); header.append(f"{logger_state.current_agent}", style="bold " + styles["accent"])
    
    table = Table.grid(expand=True, padding=(0, 1))
    table.add_column(width=10); table.add_column(width=8); table.add_column(width=18); table.add_column()
    for l in logger_state.logs[-max_logs:]:
        tr = l["tag"].strip(); ts = "bold green" if tr == "OK" else "bold yellow" if tr == "EXEC" else "bold red" if tr == "ERR" else "bold purple" if tr == "TASK" else "bold cyan" if tr == "DEBUG" else styles["accent"]
        table.add_row(Text(f" {l['time']} ", style=styles["dim"]), Text(f" {l['tag']} ", style=ts), Text(f" {l['agent']:<16} ", style=styles["accent"]), Text(f" {l['msg']}", style=styles["base"], no_wrap=True))
    
    if logger_state.current_thought and logger_state.show_thoughts:
        th = logger_state.current_thought.strip().replace("\n", " ")
        if not logger_state.thoughts_expanded:
            th = th[:120] + "..." if len(th) > 123 else th
        table.add_row(Text(f" {time.strftime('%H:%M:%S')} ", style="dim italic"), Text(f" THINK ", style="bold magenta"), Text(f" {logger_state.current_agent:<16} ", style="dim magenta"), Text(f" {th}", style="dim italic", no_wrap=not logger_state.thoughts_expanded))

    m_left = Text(f"TOTAL: {int(time.time() - logger_state.start_time)}s | STEP: {int(time.time() - logger_state.agent_start_time)}s", style=styles["base"])
    m_right = Text(f"TOKENS: {logger_state.total_tokens} | ERRORS: {logger_state.error_count}", style=styles["base"])
    todo = Text()
    if logger_state.todo_list:
        if not logger_state.todo_expanded:
            active = next((t for t in logger_state.todo_list if t["status"] == "active"), logger_state.todo_list[-1])
            todo.append(f" {'▶' if active['status']=='active' else '✔'} {active['task']}", style=styles["accent"] if active["status"] == "active" else styles["base"])
        else:
            for t in logger_state.todo_list:
                icon = "✔" if t["status"]=="done" else "▶" if t["status"]=="active" else "○"
                todo.append(f" {icon} {t['task']}\n", style=styles["accent"] if t["status"] == "active" else styles["base"] if t["status"]=="done" else styles["dim"])
    else: todo.append("Initializing...", style=styles["dim"])

    layout = Layout()
    layout.split_column(
        Layout(make_gradient_panel(header, palette=palette_raw), size=3),
        Layout(make_gradient_panel(table, title=" MISSION LOGS ", palette=palette_raw), ratio=1),
        Layout(name="footer", size=todo_size)
    )
    
    if logger_state.active_prompt:
        # Calculate dynamic height for interaction panel based on content
        prompt_mode = getattr(logger_state, 'prompt_mode', 'text')
        prompt_options = getattr(logger_state, 'prompt_options', [])
        is_details = logger_state.active_prompt.get('details') is not None
        
        # Base height calculation:
        # - 3 lines for box borders (approx)
        # - 2 lines for question text
        # - 2 lines for generic padding
        needed_height = 7
        
        if is_details:
             needed_height += 4 # Command + Agent lines
             
        if prompt_mode == 'menu':
            needed_height += 2 # Header text
            needed_height += len(prompt_options) # One line per option
        else:
            needed_height += 3 # Input area
            
        # Clamp height to reasonable bounds (min 8, max 20)
        panel_height = min(max(needed_height, 8), 20)

        interaction_panel = make_interaction_box(
            logger_state.active_prompt,
            prompt_mode,
            getattr(logger_state, 'prompt_input', ''),
            prompt_options,
            getattr(logger_state, 'prompt_selection', 0),
            palette_raw,
            getattr(logger_state, 'prompt_cursor_index', None)
        )
        
        prompt_layout = Layout()
        prompt_layout.split_column(
            Layout(make_gradient_panel(header, palette=palette_raw), size=3),
            Layout(make_gradient_panel(table, title=" MISSION LOGS ", palette=palette_raw), ratio=1),
            Layout(interaction_panel, size=panel_height),
            Layout(name="footer", size=todo_size)
        )
        prompt_layout["footer"].split_row(
            Layout(make_gradient_panel(m_left, title=" DURATION ", palette=palette_raw), ratio=1),
            Layout(make_gradient_panel(todo, title=" ROADMAP (TAB/P) ", palette=palette_raw), ratio=2),
            Layout(make_gradient_panel(m_right, title=" MONITORING ", palette=palette_raw), ratio=1)
        )
        return prompt_layout
    
    layout["footer"].split_row(
        Layout(make_gradient_panel(m_left, title=" DURATION ", palette=palette_raw), ratio=1),
        Layout(make_gradient_panel(todo, title=" ROADMAP (TAB/P) ", palette=palette_raw), ratio=2),
        Layout(make_gradient_panel(m_right, title=" MONITORING ", palette=palette_raw), ratio=1)
    )
    
    return layout
