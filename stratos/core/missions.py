import json
import os
from typing import Dict, Optional

class MissionType:
    """Manager for extensible mission types and their associations."""
    _missions_cache: Optional[Dict] = None

    @classmethod
    def _load_missions(cls) -> Dict:
        if cls._missions_cache is None:
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            missions_path = os.path.join(base_dir, "assets", "missions.json")
            try:
                with open(missions_path, "r") as f:
                    cls._missions_cache = json.load(f)
            except Exception:
                cls._missions_cache = {}
        return cls._missions_cache

    @classmethod
    def get_mission_data(cls, mission_key: str) -> Optional[Dict]:
        """Returns metadata for a given mission (case-insensitive)."""
        missions = cls._load_missions()
        return missions.get(mission_key.upper())

    @classmethod
    def is_valid_mission(cls, mission_key: str) -> bool:
        """Checks if a mission is authorized in missions.json."""
        return mission_key.upper() in cls._load_missions()

    @classmethod
    def get_prompt_key(cls, mission_key: str) -> str:
        """Returns the prompt file key associated with the mission."""
        data = cls.get_mission_data(mission_key)
        if data and "prompt" in data:
            return data["prompt"]
        return f"mission_{mission_key.lower()}"
