import os
import requests
from typing import List, Dict, Any, Optional
from dotenv import load_dotenv

load_dotenv()

class NaverNewsClient:
    """
    Client for Naver Open API (News Search).
    """
    
    BASE_URL = "https://openapi.naver.com/v1/search/news.json"

    def __init__(self, client_id: Optional[str] = None, client_secret: Optional[str] = None):
        self.client_id = client_id or os.getenv("NAVER_CLIENT_ID")
        self.client_secret = client_secret or os.getenv("NAVER_CLIENT_SECRET")
        
        if not self.client_id or not self.client_secret:
            print("⚠️ WARNING: Naver API credentials not found.")

    def search_news(self, query: str, display: int = 20, sort: str = "date") -> List[Dict[str, Any]]:
        """
        Search news by keyword.
        
        Args:
            query: Search keyword (e.g., "부동산 정책")
            display: Number of results (10~100)
            sort: 'date' (latest) or 'sim' (relevance)
        """
        if not self.client_id or not self.client_secret:
            return []

        headers = {
            "X-Naver-Client-Id": self.client_id,
            "X-Naver-Client-Secret": self.client_secret
        }
        
        params = {
            "query": query,
            "display": display,
            "start": 1,
            "sort": sort
        }

        try:
            response = requests.get(self.BASE_URL, headers=headers, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            return data.get("items", [])
        except Exception as e:
            print(f"❌ [Naver] API Error: {e}")
            return []
