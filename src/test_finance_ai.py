import os
import sys
from dotenv import load_dotenv

# Load environment variables from .env
load_dotenv()

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), "."))

from agents.finance_agent import FinanceAgent

def test_ai_parsing():
    print("🚀 Starting Consigliere AI Integration Test...")
    
    # Check API Key
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        print("❌ Error: GEMINI_API_KEY not found in .env")
        return

    print(f"🔑 API Key detected: {api_key[:5]}... (masked)")

    agent = FinanceAgent(storage_mode="local")
    
    # Complex input that requires understanding
    # "Split 50,000 won for dinner with friends at Gangnam" -> Should act as 50000 expense
    input_text = "Gangnam BBQ dinner with friends, paid 50,000 won."
    
    print(f"\n📥 User Input: '{input_text}'")
    print("Thinking... (Calling Gemini API)")
    
    try:
        response = agent.process_transaction(input_text)
        print(f"\n📤 Agent Response:\n{response}")
        
        # Verify File Content
        from datetime import datetime
        year = datetime.now().year
        month = datetime.now().month
        file_path = f"Finance/Ledger_{year}_{month:02d}.md"
        
        if agent.storage.exists(file_path):
            print(f"\n✅ Ledger File Updated: {file_path}")
            print(agent.storage.read_file(file_path))
        else:
            print("❌ Ledger file not found!")
            
    except Exception as e:
        print(f"\n❌ Test Failed: {e}")

if __name__ == "__main__":
    test_ai_parsing()
