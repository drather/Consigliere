import os
import requests
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from core.logger import get_logger
from .models import MacroData, MacroIndicator

logger = get_logger(__name__)

class BOKClient:
    """
    Client for Bank of Korea (BOK) ECOS Open API.
    """
    BASE_URL = "https://ecos.bok.or.kr/api/StatisticSearch"

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("BOK_API_KEY", "sample")

    def get_statistic(
        self, 
        stat_code: str, 
        period: str = "M", 
        start_date: Optional[str] = None, 
        end_date: Optional[str] = None,
        item_code1: str = "?",
        item_code2: str = "?",
        item_code3: str = "?"
    ) -> Optional[Dict[str, Any]]:
        """
        Generic method to fetch statistics from ECOS.
        URL Format: /api/StatisticSearch/KEY/json/kr/1/10/CODE/PERIOD/START/END/ITEM1/ITEM2/ITEM3
        """
        if not end_date:
            end_date = datetime.now().strftime("%Y%m%d") if period == "D" else datetime.now().strftime("%Y%m")
        if not start_date:
            # Default to last 3 months
            dt_start = datetime.now() - timedelta(days=90)
            start_date = dt_start.strftime("%Y%m%d") if period == "D" else dt_start.strftime("%Y%m")

        url = f"{self.BASE_URL}/{self.api_key}/json/kr/1/1/{stat_code}/{period}/{start_date}/{end_date}/{item_code1}/{item_code2}/{item_code3}"
        
        try:
            logger.info(f"🌐 [BOKClient] Fetching: {stat_code} ({period})")
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            if "StatisticSearch" in data and "row" in data["StatisticSearch"]:
                return data["StatisticSearch"]["row"][0]
            
            logger.warning(f"⚠️ [BOKClient] No data found for {stat_code}. Response: {data}")
            return None
        except Exception as e:
            logger.error(f"❌ [BOKClient] Error fetching {stat_code}: {e}")
            return None

class MacroService:
    def __init__(self, api_key: Optional[str] = None):
        self.client = BOKClient(api_key)
        from ..config import RealEstateConfig
        self.config = RealEstateConfig()

    def fetch_latest_macro_data(self) -> MacroData:
        logger.info("📈 [MacroService] Fetching latest macro-economic data...")
        codes = self.config.get_bok_codes()
        
        # 1. Base Rate
        base_rate_row = self.client.get_statistic(codes["base_rate"], period="M", item_code1="0101000")
        base_rate = None
        if base_rate_row:
            base_rate = MacroIndicator(
                name="한국은행 기준금리",
                code="0101000",
                value=float(base_rate_row["DATA_VALUE"]),
                unit="%",
                date=base_rate_row["TIME"]
            )

        # 2. M2
        m2_row = self.client.get_statistic(codes["m2"], period="M", item_code1="BBGS00")
        m2_growth = None
        if m2_row:
            m2_growth = MacroIndicator(
                name="M2 통화량(기말, 계절조정)",
                code="BBGS00",
                value=float(m2_row["DATA_VALUE"]),
                unit="십억원",
                date=m2_row["TIME"]
            )

        # 3. Household Loan Rate
        loan_rate_row = self.client.get_statistic(codes["loan_rate"], period="M", item_code1="BEABAA2")
        loan_rate = None
        if loan_rate_row:
            loan_rate = MacroIndicator(
                name="예금은행 주택담보대출 금리",
                code="BEABAA2",
                value=float(loan_rate_row["DATA_VALUE"]),
                unit="%",
                date=loan_rate_row["TIME"]
            )

        return MacroData(
            base_rate=base_rate,
            m2_growth=m2_growth,
            loan_rate=loan_rate,
            updated_at=datetime.now().isoformat()
        )
