from google import genai
import os
from stratos.utils.config import get_env_var

class ModelManager:
    """Manages Gemini model listing and filtering."""
    
    def __init__(self, api_key: str = None):
        self.api_key = api_key or get_env_var("GEMINI_API_KEY")
        self.client = genai.Client(api_key=self.api_key) if self.api_key else None

    def get_gemini_models(self) -> list:
        """Retrieves only Gemini-family models."""
        if not self.client: return []
        
        try:
            return [m for m in self.client.models.list() if "gemini" in m.name.lower()]
        except Exception:
            return []

    def print_table(self):
        """Displays available models in a clean table format."""
        models = self.get_gemini_models()
        if not models:
            print("ERROR: Could not retrieve models. Check your API Key.")
            return

        print(f"\n{'NAME':<40} {'DISPLAY NAME'}")
        print("-" * 75)
        for m in models:
            print(f"{m.name:<40} {m.display_name}")
        print()

if __name__ == "__main__":
    ModelManager().print_table()
