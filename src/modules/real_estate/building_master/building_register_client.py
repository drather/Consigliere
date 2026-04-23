import os
import logging
import requests
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

_BASE_URL = "https://apis.data.go.kr/1613000/BldRgstHubService/getBrBasisOulnInfo"


class BuildingRegisterClient:
    def __init__(self, api_key: Optional[str] = None):
        self._api_key = api_key or os.getenv("HUB_API_KEY", "")

    def fetch_page(self, sigungu_cd: str, page_no: int = 1, num_of_rows: int = 100) -> dict:
        params = {
            "serviceKey": self._api_key,
            "sigunguCd": sigungu_cd,
            "numOfRows": num_of_rows,
            "pageNo": page_no,
            "_type": "json",
        }
        resp = requests.get(_BASE_URL, params=params, timeout=30)
        resp.raise_for_status()
        return resp.json()

    def fetch_apartments_by_sigungu(self, sigungu_cd: str) -> List[dict]:
        """시군구 전체 아파트 수집 (페이지네이션). 아파트 용도만 반환."""
        page_no = 1
        results: List[dict] = []
        while True:
            data = self.fetch_page(sigungu_cd, page_no=page_no)
            items = self._extract_items(data)
            if not items:
                break
            results.extend(i for i in items if "아파트" in str(i.get("mainPurpsCdNm", "")))
            total = _safe_int(
                data.get("response", {}).get("body", {}).get("totalCount", 0)
            )
            if page_no * 100 >= total:
                break
            page_no += 1
        return results

    @staticmethod
    def _extract_items(data: dict) -> List[dict]:
        try:
            items = data["response"]["body"]["items"]["item"]
            if items is None:
                return []
            if isinstance(items, dict):
                return [items]
            return list(items)
        except (KeyError, TypeError):
            return []

    @staticmethod
    def parse_item(item: dict) -> dict:
        use_apr = str(item.get("useAprDay", "") or "")
        sigungu = str(item.get("sigunguCd", "") or "")
        bjdong = str(item.get("bjdongCd", "") or "")
        return {
            "mgm_pk": str(item.get("mgmBldrgstPk", "") or ""),
            "building_name": str(item.get("bldNm", "") or ""),
            "sigungu_code": sigungu,
            "bjdong_code": bjdong,
            "parcel_pnu": sigungu + bjdong,
            "road_address": str(item.get("newPlatPlc", "") or "") or None,
            "jibun_address": str(item.get("platPlc", "") or "") or None,
            "completion_year": int(use_apr[:4]) if len(use_apr) >= 4 and use_apr[:4].isdigit() else None,
            "total_units": _to_int(item.get("hhldCnt")),
            "total_buildings": _to_int(item.get("dongCnt")),
            "floor_area_ratio": _to_float(item.get("vlRat")),
            "building_coverage_ratio": _to_float(item.get("bcRat")),
        }


def _safe_int(val) -> int:
    try:
        return int(val)
    except (ValueError, TypeError):
        return 0


def _to_int(val) -> Optional[int]:
    try:
        v = str(val).strip()
        return int(v) if v and v != "None" else None
    except (ValueError, TypeError):
        return None


def _to_float(val) -> Optional[float]:
    try:
        v = str(val).strip()
        return float(v) if v and v != "None" else None
    except (ValueError, TypeError):
        return None
