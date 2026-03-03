import os

ASSETS_DIR = os.path.dirname(__file__)
PROMPTS_DIR = os.path.join(ASSETS_DIR, "prompts")

def load_prompt(name: str, **kwargs) -> str:
    """Loads a prompt from assets and formats it with provided kwargs.
    Supports search in sub-folders (roles, missions).
    """
    path = os.path.join(PROMPTS_DIR, f"{name}.txt")
    
    if not os.path.exists(path):
        path = os.path.join(PROMPTS_DIR, "roles", f"{name}.txt")
        
    if not os.path.exists(path):
        path = os.path.join(PROMPTS_DIR, "missions", f"{name}.txt")
        
    if not os.path.exists(path):
        return f"ERROR: Prompt {name} not found."
    
    with open(path, "r", encoding="utf-8") as f:
        content = f.read()
    
    try:
        return content.format(**kwargs)
    except KeyError:
        return content

def load_tools() -> dict:
    """Loads all tool definitions and schemas from assets."""
    import json
    path = os.path.join(ASSETS_DIR, "tools.json")
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)
