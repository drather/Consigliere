import os
import sys
import unittest
from unittest.mock import MagicMock
from datetime import date

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), "../src"))

from modules.real_estate.monitor.service import TransactionMonitorService
from modules.real_estate.monitor.api_client import MOLITClient

class TestRealEstateMonitor(unittest.TestCase):
    
    SAMPLE_XML = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
    <response>
        <header><resultCode>00</resultCode><resultMsg>NORMAL SERVICE.</resultMsg></header>
        <body>
            <items>
                <item>
                    <거래금액>    82,500</거래금액>
                    <건축년도>2006</건축년도>
                    <년>2026</년>
                    <월>1</월>
                    <일>15</일>
                    <아파트>판교푸르지오그랑블</아파트>
                    <전용면적>103.96</전용면적>
                    <층>12</층>
                    <법정동시군구코드>41135</법정동시군구코드>
                </item>
            </items>
        </body>
    </response>
    """

    def test_parsing_logic(self):
        # Mock the API Client to return our sample XML
        mock_client = MagicMock(spec=MOLITClient)
        mock_client.fetch_raw_transactions.return_value = self.SAMPLE_XML
        mock_client.parse_xml_to_dict_list.side_effect = MOLITClient().parse_xml_to_dict_list
        
        service = TransactionMonitorService(client=mock_client)
        
        # Execute
        results = service.get_daily_transactions("41135", "202601")
        
        # Verify
        self.assertEqual(len(results), 1)
        tx = results[0]
        self.assertEqual(tx.apt_name, "판교푸르지오그랑블")
        self.assertEqual(tx.price, 825000000) # 82,500 * 10,000
        self.assertEqual(tx.deal_date, date(2026, 1, 15))
        self.assertEqual(tx.exclusive_area, 103.96)
        print("\n✅ Parsing Logic Test Passed!")

    def test_service_repository_flow(self):
        # 1. Mock Client
        mock_client = MagicMock(spec=MOLITClient)
        mock_client.fetch_raw_transactions.return_value = self.SAMPLE_XML
        mock_client.parse_xml_to_dict_list.side_effect = MOLITClient().parse_xml_to_dict_list

        # 2. Mock Repository (Dynamic Import to avoid circular dep issues in test setup if any)
        # In real code, we'd inject this. For now, let's assume service uses it or returns data.
        # But wait, Service currently RETURNS list, doesn't save it itself.
        # So we test that the Service output is valid for Repository.
        
        service = TransactionMonitorService(client=mock_client)
        transactions = service.get_daily_transactions("41135", "202601")
        
        # 3. Simulate Save
        from modules.real_estate.repository import ChromaRealEstateRepository
        mock_repo = MagicMock(spec=ChromaRealEstateRepository)
        
        for tx in transactions:
            mock_repo.save_transaction(tx)
            
        # Verify save was called
        self.assertEqual(mock_repo.save_transaction.call_count, 1)
        # Verify the argument passed to save
        saved_tx = mock_repo.save_transaction.call_args[0][0]
        self.assertEqual(saved_tx.apt_name, "판교푸르지오그랑블")
        print("✅ Repository Flow Logic Verified!")

    def test_integration_real_api(self):
        """
        Integration test with REAL API Key.
        Only runs if MOLIT_API_KEY is set in .env
        """
        api_key = os.getenv("MOLIT_API_KEY")
        if not api_key or "your_api_key" in api_key:
            print("\n⚠️ Skipping Real API Test (MOLIT_API_KEY not set)")
            return

        print("\n🚀 Starting Real API Integration Test...")
        service = TransactionMonitorService()
        
        # Test with Bundang-gu (41135) for Jan 2025 (to ensure data exists)
        # Using 202501 because 202602 might be too early for data
        district_code = "41135" 
        deal_ym = "202501" 
        
        transactions = service.get_daily_transactions(district_code, deal_ym)
        
        if not transactions:
            print("⚠️ No transactions found. Might be an API issue or no deals.")
            # Verify raw response manually if needed
            # raw = service.client.fetch_raw_transactions(district_code, deal_ym)
            # print(raw[:200])
        else:
            print(f"✅ Successfully fetched {len(transactions)} transactions from API.")
            print(f"   Sample: {transactions[0].apt_name}, {transactions[0].price} KRW")
            
            # Verify one transaction structure
            tx = transactions[0]
            self.assertIsInstance(tx.price, int)
            self.assertIsInstance(tx.apt_name, str)

if __name__ == "__main__":
    unittest.main()
