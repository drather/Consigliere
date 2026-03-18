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
    def get_real_estate_transactions(
        district_code: Optional[str] = None,
        apt_name: Optional[str] = None,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
        price_min: Optional[int] = None,
        price_max: Optional[int] = None,
        limit: int = 20,
    ) -> pd.DataFrame:
        """Fetches transactions for the monitor tab."""
        try:
            params: Dict = {"limit": min(limit, 500)}
            if district_code:
                params["district_code"] = district_code
            if apt_name:
                params["apt_name"] = apt_name
            if date_from:
                params["date_from"] = date_from
            if date_to:
                params["date_to"] = date_to
            if price_min is not None:
                params["price_min"] = price_min
            if price_max is not None:
                params["price_max"] = price_max

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

    @staticmethod
    def list_insight_reports() -> List[Dict]:
        """저장된 인사이트 리포트 목록을 반환한다."""
        try:
            response = requests.get(f"{API_BASE_URL}/dashboard/real-estate/reports")
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"Error fetching report list: {e}")
            return []

    @staticmethod
    def get_insight_report(filename: str) -> Dict:
        """저장된 인사이트 리포트 상세 내용을 반환한다."""
        try:
            response = requests.get(f"{API_BASE_URL}/dashboard/real-estate/reports/{filename}")
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"Error fetching report detail: {e}")
            return {}

    @staticmethod
    def get_districts() -> List[Dict]:
        """구/시 목록 반환 [{code, name}, ...]."""
        try:
            response = requests.get(f"{API_BASE_URL}/dashboard/real-estate/districts")
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"Error fetching districts: {e}")
            return []

    @staticmethod
    def get_macro_history() -> Dict:
        """거시경제 지표 시계열 데이터 반환."""
        try:
            response = requests.get(f"{API_BASE_URL}/dashboard/real-estate/macro-history")
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"Error fetching macro history: {e}")
            return {}

    @staticmethod
    def trigger_update_policy() -> Dict:
        """정책 팩트 수집: AdvancedScraper → ChromaDB policy_knowledge."""
        try:
            response = requests.post(f"{API_BASE_URL}/agent/real_estate/news/update_policy", timeout=120)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            return {"error": str(e)}

    @staticmethod
    def trigger_fetch_transactions(district_code: str = "11680", year_month: Optional[str] = None) -> Dict:
        """Job 1: 실거래가 수집 트리거."""
        try:
            payload = {"district_code": district_code}
            if year_month:
                payload["year_month"] = year_month
            response = requests.post(f"{API_BASE_URL}/jobs/real-estate/fetch-transactions", json=payload)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            return {"error": str(e)}

    @staticmethod
    def trigger_fetch_news() -> Dict:
        """Job 2: 뉴스 수집 트리거."""
        try:
            response = requests.post(f"{API_BASE_URL}/jobs/real-estate/fetch-news")
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            return {"error": str(e)}

    @staticmethod
    def trigger_fetch_macro() -> Dict:
        """Job 3: 거시경제 수집 트리거."""
        try:
            response = requests.post(f"{API_BASE_URL}/jobs/real-estate/fetch-macro")
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            return {"error": str(e)}

    @staticmethod
    def trigger_generate_report(district_code: str = "11680", target_date: Optional[str] = None) -> Dict:
        """Job 4: 리포트 생성 트리거."""
        try:
            payload = {"district_code": district_code}
            if target_date:
                payload["target_date"] = target_date
            response = requests.post(f"{API_BASE_URL}/jobs/real-estate/generate-report", json=payload)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            return {"error": str(e)}

    @staticmethod
    def trigger_run_pipeline(district_code: str = "11680", target_date: Optional[str] = None, send_slack: bool = True) -> Dict:
        """Pipeline: Job1~4 + Slack."""
        try:
            payload = {"district_code": district_code}
            if target_date:
                payload["target_date"] = target_date
            response = requests.post(
                f"{API_BASE_URL}/jobs/real-estate/run-pipeline",
                json=payload,
                params={"send_slack": str(send_slack).lower()},
                timeout=300
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            return {"error": str(e)}

    @staticmethod
    def search_policy_facts(query: str = "부동산 정책", n_results: int = 10) -> List[Dict]:
        """ChromaDB policy_knowledge 검색."""
        try:
            response = requests.get(
                f"{API_BASE_URL}/dashboard/real-estate/policy-facts",
                params={"query": query, "n_results": n_results}
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"Error fetching policy facts: {e}")
            return []

    @staticmethod
    def get_workflows() -> List[Dict]:
        """Fetches list of all n8n workflows."""
        try:
            response = requests.get(f"{API_BASE_URL}/agent/automation/workflows")
            response.raise_for_status()
            data = response.json()
            return data.get("workflows", [])
        except requests.exceptions.RequestException as e:
            print(f"Error fetching workflows: {e}")
            return []

    @staticmethod
    def run_workflow(workflow_id: str) -> Dict:
        """Manually triggers an n8n workflow."""
        try:
            response = requests.post(f"{API_BASE_URL}/agent/automation/workflow/{workflow_id}/run")
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"Error running workflow {workflow_id}: {e}")
            return {"error": str(e)}
