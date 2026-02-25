import json
import os
import getpass
from pathlib import Path

class ConfigFileHandler:
    """Handles low-level file IO for configuration."""
    @staticmethod
    def read_json(path: Path, default: dict) -> dict:
        if not path.exists(): return default
        try:
            with open(path, "r") as f:
                return {**default, **json.load(f)}
        except (json.JSONDecodeError, IOError):
            return default

    @staticmethod
    def write_json(path: Path, data: dict):
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w") as f:
            json.dump(data, f, indent=4)

    @staticmethod
    def read_env(path: Path, key: str) -> str:
        if not path.exists(): return os.getenv(key)
        with open(path, "r") as f:
            for line in f:
                if line.startswith(f"{key}="):
                    return line.strip().split("=", 1)[1].strip("'").strip('"')
        return os.getenv(key)

class ConfigManager:
    """Business logic for Stratos configuration."""
    HOME = Path.home() / ".config" / "stratos"
    CONFIG_PATH = HOME / "config.json"
    ENV_PATH = HOME / ".env"
    
    DEFAULTS = {
        "projects_path": str(Path.home() / "StratosProjects"),
        "theme": "stratos_dark",
        "show_thoughts": True,
        "debug_mode": False,
        "display_mode": "dashboard",
        "show_results": True
    }

    def load(self) -> dict:
        return ConfigFileHandler.read_json(self.CONFIG_PATH, self.DEFAULTS)

    def save(self, config: dict):
        ConfigFileHandler.write_json(self.CONFIG_PATH, config)

    def get_api_key(self, key="GEMINI_API_KEY") -> str:
        return ConfigFileHandler.read_env(self.ENV_PATH, key)

    def save_env(self, key: str, value: str):
        vars = {}
        if self.ENV_PATH.exists():
            with open(self.ENV_PATH, "r") as f:
                for line in f:
                    if "=" in line:
                        k, v = line.strip().split("=", 1)
                        vars[k] = v
        vars[key] = value
        with open(self.ENV_PATH, "w") as f:
            for k, v in vars.items():
                f.write(f"{k}={v}\n")

# Singletons and legacy support
_manager = ConfigManager()
def load_config(): return _manager.load()
def save_config(config): return _manager.save(config)
def get_env_var(key): return _manager.get_api_key(key)
def save_env_var(key, value): return _manager.save_env(key, value)
def get_user_id(): return getpass.getuser()
STRATOS_HOME = ConfigManager.HOME
ensure_home = lambda: ConfigManager.HOME.mkdir(parents=True, exist_ok=True)
