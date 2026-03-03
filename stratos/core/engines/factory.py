import json
import os
import importlib
from typing import Any, Dict

class EngineFactory:
    """Central factory to instantiate AI engines from configuration."""
    _engines_config: Dict = {}

    @classmethod
    def _load_config(cls):
        if not cls._engines_config:
            base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            path = os.path.join(base_dir, "assets", "engines.json")
            try:
                with open(path, "r") as f:
                    cls._engines_config = json.load(f)
            except Exception:
                cls._engines_config = {}

    @classmethod
    def create_engine(cls, provider: str, tier: str, api_key: str) -> Any:
        """Instantiates the correct engine class for the given provider and tier."""
        cls._load_config()
        provider = provider.upper()
        tier = tier.upper()
        
        config = cls._engines_config.get(provider)
        if not config:
            raise ValueError(f"Unknown engine provider: {provider}")
            
        model_id = config["models"].get(tier, config["models"]["MEDIUM"])
        module_path = config["module"]
        class_name = config["class"]
        
        module = importlib.import_module(module_path)
        engine_class = getattr(module, class_name)
        
        return engine_class(api_key=api_key, model_id=model_id)

    @classmethod
    def list_providers(cls) -> list:
        """Returns a list of all configured engine providers."""
        cls._load_config()
        return list(cls._engines_config.keys())

    @classmethod
    def get_tier_models(cls, provider: str) -> dict:
        """Returns the current model mapping for a provider."""
        cls._load_config()
        return cls._engines_config.get(provider.upper(), {}).get("models", {})

    @classmethod
    def save_engine_config(cls, provider: str, tier: str, model_id: str):
        """Updates and saves the model for a specific tier in engines.json."""
        cls._load_config()
        provider = provider.upper()
        tier = tier.upper()
        
        if provider in cls._engines_config:
            cls._engines_config[provider]["models"][tier] = model_id
            
            base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            path = os.path.join(base_dir, "assets", "engines.json")
            with open(path, "w") as f:
                json.dump(cls._engines_config, f, indent=2)

    @classmethod
    def get_tier_for_role(cls, role: str) -> str:
        """Determines which model tier should be used for a specific role."""
        from stratos.core.roles import AgentRole
        return AgentRole.get_tier(role)
