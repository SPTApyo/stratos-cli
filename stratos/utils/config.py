import json
import os
from pathlib import Path

# Standard Linux path for user config: ~/.config/stratos/
STRATOS_HOME = Path.home() / ".config" / "stratos"
CONFIG_FILE = STRATOS_HOME / "config.json"
ENV_FILE = STRATOS_HOME / ".env"

DEFAULT_CONFIG = {
    "projects_path": str(Path.home() / "StratosProjects"),
    "theme": "stratos_dark",
    "show_thoughts": True,
    "debug_mode": False,
    "display_mode": "dashboard",
    "show_results": True
}

def ensure_home():
    """Ensure the config directory exists."""
    if not STRATOS_HOME.exists():
        STRATOS_HOME.mkdir(parents=True, exist_ok=True)

def load_config():
    ensure_home()
    if not CONFIG_FILE.exists():
        save_config(DEFAULT_CONFIG)
        return DEFAULT_CONFIG
    try:
        with open(CONFIG_FILE, "r") as f:
            return {**DEFAULT_CONFIG, **json.load(f)}
    except Exception:
        return DEFAULT_CONFIG

def save_config(config):
    ensure_home()
    with open(CONFIG_FILE, "w") as f:
        json.dump(config, f, indent=4)

def get_env_var(key):
    """Loads variables from the global ~/.config/stratos/.env file."""
    if ENV_FILE.exists():
        with open(ENV_FILE, "r") as f:
            for line in f:
                if line.startswith(f"{key}="):
                    return line.strip().split("=")[1].strip("'").strip('"')
    return os.getenv(key)

def save_env_var(key, value):
    """Saves a variable to the global .env file."""
    ensure_home()
    vars = {}
    if ENV_FILE.exists():
        with open(ENV_FILE, "r") as f:
            for line in f:
                if "=" in line:
                    k, v = line.strip().split("=", 1)
                    vars[k] = v
    
    vars[key] = value
    with open(ENV_FILE, "w") as f:
        for k, v in vars.items():
            f.write(f"{k}={v}\n")

def get_user_id():
    """Retrieves the local username."""
    import getpass
    return getpass.getuser()
