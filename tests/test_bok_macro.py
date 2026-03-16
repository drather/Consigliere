import os
import sys
import pytest
from unittest.mock import MagicMock, patch

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), "../src"))

from modules.real_estate.macro.bok_service import BOKClient, MacroService

def test_bok_client_url_construction():
    client = BOKClient(api_key="TEST_KEY")
    # We'll use a mock to check the URL if possible, but let's just test the return for now
    with patch("requests.get") as mock_get:
        mock_get.return_value.json.return_value = {
            "StatisticSearch": {
                "row": [{"DATA_VALUE": "3.5", "TIME": "202403", "UNIT_NAME": "%"}]
            }
        }
        mock_get.return_value.status_code = 200
        
        result = client.get_statistic("060Y001", period="M")
        assert result["DATA_VALUE"] == "3.5"
        assert result["TIME"] == "202403"

def test_macro_service_synthesis():
    service = MacroService(api_key="sample")
    
    with patch.object(BOKClient, "get_statistic") as mock_get:
        # Mocking values for Base Rate, M2, and Loan Rate
        def side_effect(stat_code, **kwargs):
            if stat_code == "722Y001": # Base Rate
                return {"DATA_VALUE": "3.5", "TIME": "202403"}
            if stat_code == "101Y003": # M2
                return {"DATA_VALUE": "4000000", "TIME": "202402"}
            if stat_code == "121Y002": # Loan Rate
                return {"DATA_VALUE": "4.8", "TIME": "202402"}
            return None
        
        mock_get.side_effect = side_effect
        
        data = service.fetch_latest_macro_data()
        assert data.base_rate.value == 3.5
        assert data.m2_growth.value == 4000000.0
        assert data.loan_rate.value == 4.8
        assert data.updated_at is not None

if __name__ == "__main__":
    # Manual run
    service = MacroService(api_key="sample")
    data = service.fetch_latest_macro_data()
    print(f"📊 Latest Macro Data:\n{data.model_dump_json(indent=2)}")
