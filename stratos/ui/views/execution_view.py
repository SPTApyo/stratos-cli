import time
from rich.text import Text
from rich.layout import Layout
from rich.table import Table
from stratos.ui.components.panels import make_gradient_panel, make_interaction_box

class DashboardRenderer:
    """Refactored UI Renderer: decouples layout logic from component rendering."""

    @staticmethod
    def render_header(state, styles):
        header = Text(f" MISSION: {state.project_path}", style=styles["base"])
        if state.paused:
            status = "SYSTEM_PAUSED" if state.agent_is_waiting else "PAUSE_PENDING"
            color = "red" if state.agent_is_waiting else "yellow"
            header.append(f"  |  {status}", style=f"bold blink {color}")
            
        header.append(f"  |  ITERATION: ", style=styles["dim"])
        header.append(f"{state.current_cycle}", style="bold " + styles["accent"])
        header.append(f"  |  PROCESSOR: ", style=styles["dim"])
        header.append(f"{state.current_agent}", style="bold " + styles["accent"])
        return header

    @staticmethod
    def render_log_table(state, styles, max_logs):
        table = Table.grid(expand=True, padding=(0, 1))
        table.add_column(width=10); table.add_column(width=8); table.add_column(width=18); table.add_column()
        
        tag_styles = {"OK": "bold green", "EXEC": "bold yellow", "ERR": "bold red", "TASK": "bold purple", "DEBUG": "bold cyan"}
        
        for l in state.logs[-max_logs:]:
            tag = l["tag"].strip()
            style = tag_styles.get(tag, styles["accent"])
            table.add_row(
                Text(f" {l['time']} ", style=styles["dim"]),
                Text(f" {l['tag']} ", style=style),
                Text(f" {l['agent']:<16} ", style=styles["accent"]),
                Text(f" {l['msg']}", style=styles["base"], no_wrap=True)
            )
            
        if state.current_thought and state.show_thoughts:
            th = state.current_thought.strip().replace("\n", " ")
            if not state.thoughts_expanded: th = th[:120] + "..." if len(th) > 123 else th
            table.add_row(
                Text(f" {time.strftime('%H:%M:%S')} ", style="dim italic"),
                Text(f" THINK ", style="bold magenta"),
                Text(f" {state.current_agent:<16} ", style="dim magenta"),
                Text(f" {th}", style="dim italic", no_wrap=not state.thoughts_expanded)
            )
        return table

    @staticmethod
    def render_roadmap(state, styles):
        todo = Text()
        if not state.todo_list: return Text("Initializing...", style=styles["dim"])
        
        if not state.todo_expanded:
            active = next((t for t in state.todo_list if t["status"] == "active"), 
                          next((t for t in state.todo_list if t["status"] != "done"), state.todo_list[-1]))
            icon = "▶" if active["status"] == "active" else "○" if active["status"] == "pending" else "✔"
            style = styles["accent"] if active["status"] == "active" else styles["dim"] if active["status"] == "pending" else styles["base"]
            todo.append(f" {icon} {active['task']}", style=style)
        else:
            for t in state.todo_list:
                icon = "✔" if t["status"]=="done" else "▶" if t["status"]=="active" else "○"
                style = styles["accent"] if t["status"] == "active" else styles["base"] if t["status"]=="done" else styles["dim"]
                todo.append(f" {icon} {t['task']}\n", style=style)
        return todo

    @staticmethod
    def calculate_prompt_height(state, term_height):
        if not state.active_prompt: return 0
        q_lines = (len(state.active_prompt.get('question', '')) // 100) + 1
        needed = 4 + q_lines
        if state.active_prompt.get('details'): needed += 3
        if state.prompt_mode == 'menu': needed += 2 + len(state.prompt_options)
        else: needed += 2 + (len(state.prompt_input) // 80) + 1
        return min(max(needed, 8), max(10, term_height - 15))

def render_execution_dashboard(state, styles, palette, term_height):
    """Entry point for rendering, orchestrating specialized sub-renderers."""
    
    prompt_height = DashboardRenderer.calculate_prompt_height(state, term_height)
    todo_height = len(state.todo_list) + 2 if state.todo_expanded else 5
    reserved = 3 + todo_height + 8 + (prompt_height if prompt_height > 0 else 0)
    max_logs = max(3, term_height - reserved)

    header = DashboardRenderer.render_header(state, styles)
    logs = DashboardRenderer.render_log_table(state, styles, max_logs)
    roadmap = DashboardRenderer.render_roadmap(state, styles)
    
    m_left = Text(f"TOTAL: {int(time.time() - state.start_time)}s | STEP: {int(time.time() - state.agent_start_time)}s", style=styles["base"])
    m_right = Text(f"TOKENS: {state.total_tokens} | ERRORS: {state.error_count}", style=styles["base"])

    layout = Layout()
    sections = [
        Layout(make_gradient_panel(header, palette=palette), size=3),
        Layout(make_gradient_panel(logs, title=" MISSION LOGS ", palette=palette), ratio=1)
    ]
    
    if state.active_prompt:
        interaction = make_interaction_box(state.active_prompt, state.prompt_mode, state.prompt_input, state.prompt_options, state.prompt_selection, palette, state.prompt_cursor_index)
        sections.append(Layout(interaction, size=prompt_height))
        
    sections.append(Layout(name="footer", size=todo_height))
    layout.split_column(*sections)
    
    layout["footer"].split_row(
        Layout(make_gradient_panel(m_left, title=" DURATION ", palette=palette), ratio=1),
        Layout(make_gradient_panel(roadmap, title=" ROADMAP (TAB/T) ", palette=palette), ratio=2),
        Layout(make_gradient_panel(m_right, title=" MONITORING ", palette=palette), ratio=1)
    )
    
    return layout
