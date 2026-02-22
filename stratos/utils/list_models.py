from google import genai
import os
from dotenv import load_dotenv

def list_available_models():
    load_dotenv()
    api_key = os.getenv("GEMINI_API_KEY")
    client = genai.Client(api_key=api_key)
    
    print(f"{'NAME':<40} {'DISPLAY NAME'}")
    print("-" * 60)
    
    for model in client.models.list():
        if model.name.startswith("models/gemini"):
            print(f"{model.name:<40} {model.display_name}")

if __name__ == "__main__":
    list_available_models()
