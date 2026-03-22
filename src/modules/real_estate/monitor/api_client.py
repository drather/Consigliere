import os
import time
import requests
import xml.etree.ElementTree as ET
from datetime import date
from typing import List, Dict, Any, Optional
from dotenv import load_dotenv
from core.logger import get_logger

logger = get_logger(__name__)


load_dotenv()

class MOLITClient:
    """
    Client for Ministry of Land, Infrastructure and Transport (MOLIT) Open API.
    Fetches Apartment Transaction data from data.go.kr.
    """
    
    # Updated Endpoint based on latest public data portal spec
    BASE_URL = "http://apis.data.go.kr/1613000/RTMSDataSvcAptTradeDev/getRTMSDataSvcAptTradeDev"

    def __init__(self, service_key: Optional[str] = None):
        self.service_key = service_key or os.getenv("MOLIT_API_KEY")
        if not self.service_key:
            logger.warning("⚠️ WARNING: MOLIT_API_KEY not found. API calls will fail.")

    def fetch_raw_transactions(self, district_code: str, year_month: str) -> Optional[str]:
        """
        Fetches raw XML data from the API.
        
        Args:
            district_code: 5-digit district code (e.g., '11110' for Jongno-gu)
            year_month: 6-digit year and month (e.g., '202601')
        """
        if not self.service_key:
            return None

        # Since the user has a Hex format key (87c0...), we should try using it directly.
        # requests will URL-encode it automatically if needed, but for Hex it shouldn't change much.
        params = {
            "serviceKey": self.service_key, # Use RAW key from .env
            "pageNo": "1",
            "numOfRows": "100", 
            "LAWD_CD": district_code,
            "DEAL_YMD": year_month,
        }

        logger.info(f"📡 [MOLIT] Fetching data from: {self.BASE_URL} (LAWD: {district_code}, YMD: {year_month})")
        for attempt in range(3):
            try:
                response = requests.get(self.BASE_URL, params=params, timeout=15)

                if response.status_code == 429:
                    wait = 2 ** attempt  # 1s, 2s, 4s
                    logger.warning(f"⏳ [MOLIT] 429 Rate Limited ({district_code}), {wait}s 후 재시도 ({attempt+1}/3)")
                    time.sleep(wait)
                    continue

                # MOLIT API success codes: "0", "00", "000" depending on endpoint version
                if "<resultCode>" in response.text:
                    success_codes = ["<resultCode>0</resultCode>", "<resultCode>00</resultCode>", "<resultCode>000</resultCode>"]
                    if not any(code in response.text for code in success_codes):
                        logger.error(f"❌ [MOLIT] API Logic Error: {response.text[:300]}")
                        return None

                response.raise_for_status()
                return response.text
            except Exception as e:
                logger.error(f"❌ [MOLIT] API Connection Error: {e}")
                return None
        logger.error(f"❌ [MOLIT] 3회 재시도 실패 ({district_code})")
        return None

    def parse_xml_to_dict_list(self, xml_data: str) -> List[Dict[str, Any]]:
        """
        Parses the raw XML response into a list of dictionaries.
        """
        if not xml_data:
            return []

        try:
            root = ET.fromstring(xml_data)
            items = []
            
            # Navigate to <items>/<item>
            for item in root.findall(".//item"):
                data = {}
                for element in item:
                    data[element.tag] = element.text.strip() if element.text else None
                items.append(data)
            
            return items
        except Exception as e:
            logger.error(f"❌ [MOLIT] XML Parsing Error: {e}")
            return []
