from rich.text import Text
from stratos.ui.components.core import BANNER_ART, interpolate_color

def get_banner(palette):
    banner = Text("\n\n")
    if not BANNER_ART: return Text("\n\nSTRATOS", style=f"bold {palette['p1']}")
    max_len = max((len(line) for line in BANNER_ART), default=1)
    if max_len == 0: max_len = 1
    for line in BANNER_ART:
        for i, char in enumerate(line):
            if char == " ": banner.append(char)
            else:
                factor = i / max_len
                color = interpolate_color(palette['p1'], palette['p2'], factor)
                banner.append(char, style=f"bold {color}")
        banner.append("\n")
    return banner
