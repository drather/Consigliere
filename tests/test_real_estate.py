import os
import sys
import time
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), "../src"))

from modules.real_estate.service import RealEstateAgent

def test_real_estate_flow():
    print("🚀 Starting Real Estate Integration Test...")
    
    agent = RealEstateAgent()
    
    # 1. Log Tour Report (Complex A)
    input_text_1 = "단대오거리 e편한세상 금광그랑메종 임장 다녀옴. 매매가 10억 정도이고 단지 안에 초등학교가 있어서 초품아임. 근데 언덕이 너무 심해서 걸어다니기는 좀 힘들듯."
    print(f"\n📝 Logging Tour 1: {input_text_1[:30]}...")
    response_1 = agent.log_tour(input_text_1)
    print(f"📤 Response:\n{response_1}")
    
   # 2. Log Tour Report (Complex B - Comparison)
    input_text_2 = "판교 푸르지오 그랑블. 20억이라 너무 비쌈. 평지이고 판교역 바로 앞이라 교통은 최고임."
    print(f"\n📝 Logging Tour 2: {input_text_2[:30]}...")
    response_2 = agent.log_tour(input_text_2)
    print(f"📤 Response:\n{response_2}")

    # Wait for indexing (ChromaDB is fast, but just in case)
    time.sleep(1)

    # 3. Search (Filter Test)
    query = "10억 이하이면서 초등학교가 있는 곳은 어디야?"
    print(f"\n🔍 Searching: '{query}'")
    search_response = agent.search_tours(query)
    print(f"📤 Search Result:\n{search_response}")
    
    # Validation
    if "단대오거리" in search_response and "판교" not in search_response:
        print("\n✅ Test Passed: Successfully filtered by Price and School.")
    else:
        print("\n❌ Test Failed: Search result logic is incorrect.")

if __name__ == "__main__":
    test_real_estate_flow()
