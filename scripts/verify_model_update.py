import os
import sys
from dotenv import load_dotenv

# Add src to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))

from core.llm import GeminiClient

def main():
    load_dotenv()
    print(f"ENV GEMINI_MODEL: {os.getenv('GEMINI_MODEL')}")
    
    client = GeminiClient()
    print(f"Client Model Name: {client.model_name}")
    
    if hasattr(client, 'model'):
        print(f"GenAI Model Name: {client.model.model_name}")
    else:
        print("Model not initialized (missing API key?)")

if __name__ == "__main__":
    main()
