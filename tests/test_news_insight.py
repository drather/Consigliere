import os
import sys
import unittest
from dotenv import load_dotenv

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), "../src"))

from modules.real_estate.news.service import NewsService

class TestNewsInsight(unittest.TestCase):
    def test_daily_report_generation(self):
        """
        Integration test: Fetch -> Analyze -> Save
        """
        load_dotenv()
        if not os.getenv("NAVER_CLIENT_ID"):
            print("⚠️ Skipping News Test (No API Key)")
            return

        print("\n🚀 Starting News Insight Integration Test...")
        service = NewsService()
        
        # Execute
        report_md = service.generate_daily_report()
        
        print("\n--- Generated Report ---")
        print(report_md)
        print("------------------------")
        
        self.assertIn("# 📰 Real Estate News Report", report_md)
        self.assertIn("Trend Insight", report_md)

if __name__ == "__main__":
    unittest.main()

