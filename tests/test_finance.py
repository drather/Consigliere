import sys
import os
from datetime import datetime

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), "../src"))

from modules.finance.service import FinanceAgent

def test_finance_mvp():
    print("🚀 Testing Finance Domain MVP (Repository Pattern)...")
    
    agent = FinanceAgent(storage_mode="local")
    
    # Simulate an SMS input
    input_text = "Just paid 12,000 won for Lunch at Kimbap Heaven"
    print(f"📥 Input: {input_text}")
    
    # Process
    response = agent.process_transaction(input_text)
    print(f"📤 Response:\n{response}")
    
    # Verify File (Integration Check)
    # We can check if the file exists using the storage provider
    repo = agent.repository
    # We need to access private method to construct path for checking
    # Or just hardcode for test
    from datetime import datetime
    year = datetime.now().year
    month = datetime.now().month
    file_path = f"Finance/Ledger_{year}_{month:02d}.md"
    
    if agent.storage.exists(file_path):
        print(f"✅ Ledger file verified: {file_path}")
        content = agent.storage.read_file(file_path)
        print("--- File Content Snippet ---")
        print(content)
        print("----------------------------")
    else:
        print("❌ Ledger file not found!")

if __name__ == "__main__":
    test_finance_mvp()