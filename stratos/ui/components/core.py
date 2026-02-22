import json
from pathlib import Path
from rich.text import Text
from rich.color import Color

def load_asset(filename, is_json=True):
    path = Path(__file__).parent.parent.parent / "assets" / filename
    if is_json:
        with open(path, "r") as f: return json.load(f)
    else:
        with open(path, "r") as f: return f.read().splitlines()

THEME_PALETTES = load_asset("themes.json")
MENUS = load_asset("menus.json")
BANNER_ART = load_asset("banner.txt", is_json=False)

def get_palette(theme_id):
    return THEME_PALETTES.get(theme_id, THEME_PALETTES.get("one_dark"))

def interpolate_color(color1, color2, factor: float) -> str:
    try:
        c1 = Color.parse(color1).get_truecolor()
        c2 = Color.parse(color2).get_truecolor()
        r = int(c1.red + (c2.red - c1.red) * factor)
        g = int(c1.green + (c2.green - c1.green) * factor)
        b = int(c1.blue + (c2.blue - c1.blue) * factor)
        return f"#{r:02x}{g:02x}{b:02x}"
    except: return color1

def get_styles(palette):
    is_dark = palette.get("mode") == "dark"
    return {
        "base": "bold #FFFFFF" if is_dark else "bold #000000",
        "dim": "#CCCCCC" if is_dark else "#333333",
        "accent": palette['p1'],
        "accent2": palette['p2'],
        "border": "#FFFFFF" if is_dark else "#000000"
    }

class GradientLine:
    """Dynamic horizontal gradient line with alignment support."""
    def __init__(self, char, p1, p2, title="", align="left"):
        self.char = char; self.p1 = p1; self.p2 = p2; self.title = title; self.align = align
    def __rich_console__(self, console, options):
        width = options.max_width or 40
        line = Text()
        if self.title:
            t_text = f" {self.title.strip()} "
            if self.align == "left":
                line.append(self.char * 2, style=f"bold {self.p1}")
                line.append(t_text, style=f"bold black on {self.p1}")
                for i in range(len(t_text) + 2, width):
                    line.append(self.char, style=f"bold {interpolate_color(self.p1, self.p2, i/width)}")
            else: # Right align
                fill_len = width - len(t_text) - 2
                for i in range(fill_len):
                    line.append(self.char, style=f"bold {interpolate_color(self.p1, self.p2, i/width)}")
                line.append(t_text, style=f"bold black on {self.p2}")
                line.append(self.char * 2, style=f"bold {self.p2}")
        else:
            for i in range(width):
                line.append(self.char, style=f"bold {interpolate_color(self.p1, self.p2, i/width)}")
        yield line

class VerticalLine:
    def __init__(self, char, style):
        self.char = char; self.style = style
    def __rich_console__(self, console, options):
        height = options.height or 1
        for _ in range(height):
            yield Text(self.char, style=self.style)
