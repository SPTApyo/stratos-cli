import os

ASSETS_DIR = os.path.dirname(__file__)
PROMPTS_DIR = os.path.join(ASSETS_DIR, "prompts")

def load_prompt(name: str, **kwargs) -> str:
    """Loads a prompt from assets and formats it with provided kwargs."""
    path = os.path.join(PROMPTS_DIR, f"{name}.txt")
    if not os.path.exists(path):
        return f"ERROR: Prompt {name} not found."
    
    with open(path, "r", encoding="utf-8") as f:
        content = f.read()
    
    return content.format(**kwargs)

def load_tools() -> dict:
    """Loads all tool definitions and schemas from assets."""
    import json
    path = os.path.join(ASSETS_DIR, "tools.json")
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)
