import asyncio
import json
import os
from datetime import date
from dotenv import load_dotenv

# Load environment variables from .env
load_dotenv()

from src.modules.real_estate.service import RealEstateAgent

async def test_insight_report():
    print("🚀 Testing Real Estate Insight Report Generation...")
    agent = RealEstateAgent()
    
    # Use a recent date or today (Note: API data might be delayed, but for testing logic it's fine)
    target_date = date(2025, 3, 10) # Using a known date for consistency if possible
    
    # Test for Gangnam-gu (11680)
    blocks = agent.generate_insight_report(district_code="11680", target_date=target_date)
    
    print("\n--- Generated Slack Blocks ---")
    print(json.dumps(blocks, indent=2, ensure_ascii=False))
    
    if blocks and len(blocks) > 0:
        print("\n✅ Success: Blocks generated.")
    else:
        print("\n❌ Failure: No blocks generated.")

if __name__ == "__main__":
    asyncio.run(test_insight_report())
