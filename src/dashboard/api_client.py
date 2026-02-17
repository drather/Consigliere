import requests
import pandas as pd
from typing import Optional, List, Dict
import os

# Use environment variable for API URL, default to localhost
API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")

class DashboardClient:
    """
    Client for interacting with the Consigliere Backend API.
    Decouples UI from Backend implementation details.
    """
    
    @staticmethod
    def get_finance_ledger(year: int, month: int) -> pd.DataFrame:
        """
        Fetches finance ledger data from the backend and returns a DataFrame.
        """
        try:
            response = requests.get(
                f"{API_BASE_URL}/dashboard/finance/ledger",
                params={"year": year, "month": month}
            )
            response.raise_for_status()
            data = response.json()
            
            if not data:
                return pd.DataFrame()
                
            return pd.DataFrame(data)
        except requests.exceptions.RequestException as e:
            print(f"Error fetching ledger: {e}")
            return pd.DataFrame()

    @staticmethod
    def get_real_estate_transactions(district_code: Optional[str] = None, limit: int = 50) -> pd.DataFrame:
        """Fetches transactions for the monitor tab."""
        try:
            params = {"limit": limit}
            if district_code:
                params["district_code"] = district_code
                
            response = requests.get(f"{API_BASE_URL}/dashboard/real-estate/monitor", params=params)
            response.raise_for_status()
            data = response.json()
            return pd.DataFrame(data) if data else pd.DataFrame()
        except requests.exceptions.RequestException as e:
            print(f"Error fetching real estate data: {e}")
            return pd.DataFrame()

    @staticmethod
    def list_news_reports() -> List[str]:
        """Fetches list of available news reports."""
        try:
            response = requests.get(f"{API_BASE_URL}/dashboard/real-estate/news")
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"Error fetching news list: {e}")
            return []

    @staticmethod
    def get_news_content(filename: str) -> str:
        """Fetches content of a specific news report."""
        try:
            response = requests.get(f"{API_BASE_URL}/dashboard/real-estate/news/{filename}")
            response.raise_for_status()
            return response.json().get("content", "")
        except requests.exceptions.RequestException as e:
            print(f"Error fetching news content: {e}")
            return "❌ Error loading report."
