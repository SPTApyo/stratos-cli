import json
import os
from enum import Enum
from typing import Dict, Optional

class AgentRole:
    """Manager for extensible agent roles and their associations."""
    _roles_cache: Optional[Dict] = None

    @classmethod
    def _load_roles(cls) -> Dict:
        if cls._roles_cache is None:
            # Get path to assets/roles.json relative to this file
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            roles_path = os.path.join(base_dir, "assets", "roles.json")
            try:
                with open(roles_path, "r") as f:
                    cls._roles_cache = json.load(f)
            except Exception:
                cls._roles_cache = {}
        return cls._roles_cache

    @classmethod
    def get_role_data(cls, role_name: str) -> Optional[Dict]:
        """Returns metadata for a given role (case-insensitive)."""
        roles = cls._load_roles()
        return roles.get(role_name.upper())

    @classmethod
    def is_valid_role(cls, role_name: str) -> bool:
        """Checks if a role is authorized in roles.json."""
        return role_name.upper() in cls._load_roles()

    @classmethod
    def get_prompt_key(cls, role_name: str) -> str:
        """Returns the prompt file key associated with the role."""
        data = cls.get_role_data(role_name)
        if data and "prompt" in data:
            return data["prompt"]
        return f"{role_name.lower()}_strategy" # Fallback pattern

    @classmethod
    def get_default_roles(cls) -> Dict:
        """Returns a dict of all roles marked as 'is_default': true."""
        roles = cls._load_roles()
        return {name: data for name, data in roles.items() if data.get("is_default")}
