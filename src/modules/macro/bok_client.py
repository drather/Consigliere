import os
import requests
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any

try:
    from core.logger import get_logger
    logger = get_logger(__name__)
except ImportError:
    import logging
    logger = logging.getLogger(__name__)


class BOKClient:
    """Bank of Korea ECOS Open API 클라이언트."""

    BASE_URL = "https://ecos.bok.or.kr/api/StatisticSearch"

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("BOK_API_KEY", "sample")

    def get_statistic_series(
        self,
        stat_code: str,
        item_code: str,
        months: int = 24,
        frequency: str = "M",
        item_code2: str = "?",
        item_code3: str = "?",
    ) -> List[Dict[str, Any]]:
        end_dt = datetime.now()
        start_dt = end_dt - timedelta(days=30 * months)

        if frequency == "D":
            start_date = start_dt.strftime("%Y%m%d")
            end_date = end_dt.strftime("%Y%m%d")
        elif frequency == "Q":
            # BOK ECOS quarterly format: YYYYQ# (e.g. "2023Q1")
            start_date = f"{start_dt.year}Q{(start_dt.month - 1) // 3 + 1}"
            end_date = f"{end_dt.year}Q{(end_dt.month - 1) // 3 + 1}"
        else:
            start_date = start_dt.strftime("%Y%m")
            end_date = end_dt.strftime("%Y%m")

        url = (
            f"{self.BASE_URL}/{self.api_key}/json/kr/1/{months}/"
            f"{stat_code}/{frequency}/{start_date}/{end_date}/"
            f"{item_code}/{item_code2}/{item_code3}"
        )

        try:
            logger.info(f"[BOKClient] Fetching {stat_code} ({frequency}, {months}건)")
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            data = response.json()
            return data.get("StatisticSearch", {}).get("row", [])
        except Exception as e:
            logger.error(f"[BOKClient] {stat_code} 조회 실패: {e}")
            return []

    def list_items(self, stat_code: str) -> List[Dict[str, Any]]:
        """stat_code의 item_code 목록 조회. 신규 지표 추가 시 확인용."""
        return self.get_statistic_series(stat_code, item_code="?", months=1)
