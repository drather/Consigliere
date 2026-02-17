import os
import sys
import unittest
from fastapi.testclient import TestClient
from dotenv import load_dotenv

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), "../src"))

from main import app

class TestN8nNews(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)
        load_dotenv()
        
    def test_news_api_endpoint(self):
        """
        Verify that the news analyze endpoint exists and triggers the service.
        """
        if not os.getenv("NAVER_CLIENT_ID"):
            print("⚠️ Skipping News API Test (No API Key)")
            return

        print("\n🚀 Starting News API Test...")
        # Note: This will actually call the LLM, so it might take 10s+ 
        response = self.client.post(
            "/agent/real_estate/news/analyze",
            json={"keywords": "test"}
        )
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        
        self.assertEqual(data["status"], "success")
        self.assertIn("report_content", data)
        print(f"✅ API Response received. Report Date: {data['report_date']}")

if __name__ == "__main__":
    unittest.main()

