import os
import sys
import unittest
from fastapi.testclient import TestClient

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), "../src"))

from main import app

class TestN8nIntegration(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)
        
    def test_monitor_fetch_endpoint(self):
        """
        Verify that the monitor fetch endpoint exists and accepts requests.
        """
        # If API key is missing, it might return 0 fetched, but status should be success.
        response = self.client.post(
            "/agent/real_estate/monitor/fetch",
            json={"district_code": "41135", "year_month": "202601"}
        )
        
        # We expect 200 OK regardless of whether data was found (business logic handles it)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        
        self.assertEqual(data["status"], "success")
        self.assertIn("fetched_count", data)
        print(f"\n✅ Monitor API Test: Fetched {data['fetched_count']} items.")

if __name__ == "__main__":
    unittest.main()

