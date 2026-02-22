from rich.panel import Panel
from rich.text import Text
from rich.layout import Layout
from rich.table import Table
from rich.padding import Padding
from rich.align import Align
from stratos.ui.components.core import GradientLine

def make_gradient_panel(content, title="", footer="", palette=None, padding=(0, 2), expand=True):
    if not palette: return Panel(content, title=title, padding=padding)
    p1, p2 = palette['p1'], palette['p2']
    if expand:
        panel = Layout()
        panel.split_column(Layout(name="top", size=1), Layout(name="mid", ratio=1), Layout(name="bottom", size=1))
        top_grid = Table.grid(expand=True)
        top_grid.add_column(width=1); top_grid.add_column(ratio=1); top_grid.add_column(width=1)
        top_grid.add_row(Text("╭", style=f"bold {p1}"), GradientLine("─", p1, p2, title=title, align="left"), Text("╮", style=f"bold {p2}"))
        panel["top"].update(top_grid)
        panel["mid"].update(Align(Padding(content, padding), align="left"))
        bot_grid = Table.grid(expand=True)
        bot_grid.add_column(width=1); bot_grid.add_column(ratio=1); bot_grid.add_column(width=1)
        bot_grid.add_row(Text("╰", style=f"bold {p1}"), GradientLine("─", p1, p2, title=footer, align="right"), Text("╯", style=f"bold {p2}"))
        panel["bottom"].update(bot_grid)
        return panel
    else:
        table = Table.grid(expand=True)
        table.add_column(width=1); table.add_column(ratio=1); table.add_column(width=1)
        table.add_row(Text("╭", style=f"bold {p1}"), GradientLine("─", p1, p2, title=title, align="left"), Text("╮", style=f"bold {p2}"))
        table.add_row(Text("│", style=f"bold {p1}"), Padding(content, padding), Text("│", style=f"bold {p2}"))
        table.add_row(Text("╰", style=f"bold {p1}"), GradientLine("─", p1, p2, title=footer, align="right"), Text("╯", style=f"bold {p2}"))
        return table

def make_interaction_box(prompt_data, prompt_mode, prompt_input, prompt_options, prompt_selection, palette, prompt_cursor_index=None):
    """Creates the bright yellow interaction box for AI questions and command approvals."""
    p_content = Text("\n")
    det = prompt_data.get("details")
    
    if det:
        p_content.append(f" COMMAND: ", style="bold yellow")
        p_content.append(f"{det['command']}\n", style="bold white")
        p_content.append(f" BY:      ", style="bold yellow")
        p_content.append(f"{prompt_data['agent']}\n", style="bold cyan")
    else:
        p_content.append(f" {prompt_data['agent']} ", style="bold black on yellow")
        p_content.append(f" is asking: {prompt_data['question']}\n", style="bold white")
        
    if prompt_mode == 'menu':
        p_content.append(f"\n › SELECT ACTION (Arrows/Tab to move, Enter to select):\n", style="bold yellow")
        for i, opt in enumerate(prompt_options):
            cursor = " ❯ " if i == prompt_selection else "   "
            style = "bold green" if i == prompt_selection else "white"
            p_content.append(f"{cursor}{opt['label']}\n", style=style)
    else:
        p_content.append(f"\n › YOUR ANSWER: ", style="bold yellow")
        
        # Cursor rendering logic
        idx = prompt_cursor_index if prompt_cursor_index is not None else len(prompt_input)
        # Ensure idx is within bounds
        idx = max(0, min(idx, len(prompt_input)))
        
        before_cursor = prompt_input[:idx]
        at_cursor = prompt_input[idx] if idx < len(prompt_input) else " "
        after_cursor = prompt_input[idx+1:] if idx < len(prompt_input) else ""
        
        p_content.append(before_cursor, style="bold white")
        p_content.append(at_cursor, style="bold black on white") # Cursor effect
        p_content.append(after_cursor, style="bold white")
    
    return make_gradient_panel(
        p_content, 
        title=" INTERACTION REQUIRED ", 
        footer=" WAITING FOR HUMAN ", 
        palette=palette,
        expand=True
    )
