"""
ApartmentMasterClient — 국토교통부 공동주택 공공 API 클라이언트.

API 1: 공동주택 단지 목록 (getSigunguAptList3)
  - sigunguCd(5자리) → kaptCode, kaptName 목록

API 2: 공동주택 기본정보 (getAphusBassInfoV4)
  - kaptCode → hhldCnt, bdNum, kaptBcompany, useAprDay 등
"""
import os
import logging
import requests
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

_BASE_LIST_URL = os.getenv(
    "APT_MASTER_LIST_URL",
    "https://apis.data.go.kr/1613000/AptListService3/getSigunguAptList3",
)
_BASE_INFO_URL = os.getenv(
    "APT_MASTER_INFO_URL",
    "https://apis.data.go.kr/1613000/AtclService/getAphusBassInfoV4",
)


class ApartmentMasterClient:
    def __init__(self, api_key: Optional[str] = None):
        self._api_key = api_key or os.getenv("MOLIT_APT_LIST_API_KEY") or os.getenv("MOLIT_API_KEY", "")

    def fetch_complex_list(self, sigungu_cd: str) -> List[Dict]:
        """시군구코드(5자리) → 단지 목록 [{kaptCode, kaptName, bjdCode}, ...]."""
        params = {
            "serviceKey": self._api_key,
            "sigunguCd": sigungu_cd,
            "numOfRows": "1000",
            "pageNo": "1",
            "_type": "json",
        }
        try:
            resp = requests.get(_BASE_LIST_URL, params=params, timeout=10)
            resp.raise_for_status()
            data = resp.json()
            items = (
                data.get("response", {})
                .get("body", {})
                .get("items", {})
                .get("item", [])
            )
            # API가 1건일 때 list 대신 dict 반환하는 케이스 처리
            if isinstance(items, dict):
                items = [items]
            return items if items else []
        except Exception as e:
            logger.warning(f"[AptMasterClient] fetch_complex_list({sigungu_cd}) 실패: {e}")
            return []

    def fetch_complex_info(self, kapt_code: str) -> Optional[Dict]:
        """단지코드 → 기본정보 dict (hhldCnt, bdNum, kaptBcompany, useAprDay 등)."""
        params = {
            "serviceKey": self._api_key,
            "kaptCode": kapt_code,
            "_type": "json",
        }
        try:
            resp = requests.get(_BASE_INFO_URL, params=params, timeout=10)
            resp.raise_for_status()
            data = resp.json()
            item = (
                data.get("response", {})
                .get("body", {})
                .get("item")
            )
            if not item:
                return None
            return item
        except Exception as e:
            logger.warning(f"[AptMasterClient] fetch_complex_info({kapt_code}) 실패: {e}")
            return None
