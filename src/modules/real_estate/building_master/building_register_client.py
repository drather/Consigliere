import os
import logging
import requests
from typing import List, Optional

logger = logging.getLogger(__name__)

_BASE_URL = "https://apis.data.go.kr/1613000/BldRgstHubService/getBrRecapTitleInfo"
_BJDONG_PROBE_RANGE = range(10100, 20000, 100)


def _is_apartment(item: dict) -> bool:
    return "아파트" in str(item.get("etcPurps", ""))


class BuildingRegisterClient:
    def __init__(self, api_key: Optional[str] = None):
        self._api_key = api_key or os.getenv("HUB_API_KEY", "")

    def fetch_page(
        self,
        sigungu_cd: str,
        bjdong_cd: str = "",
        page_no: int = 1,
        num_of_rows: int = 100,
    ) -> dict:
        params = {
            "serviceKey": self._api_key,
            "sigunguCd": sigungu_cd,
            "numOfRows": num_of_rows,
            "pageNo": page_no,
            "_type": "json",
        }
        if bjdong_cd:
            params["bjdongCd"] = bjdong_cd
        resp = requests.get(_BASE_URL, params=params, timeout=30)
        resp.raise_for_status()
        return resp.json()

    def discover_bjdong_codes(self, sigungu_cd: str) -> List[str]:
        """시군구 내 데이터가 존재하는 법정동 코드를 탐색해 반환한다."""
        found: List[str] = []
        for bj in _BJDONG_PROBE_RANGE:
            bjdong_cd = str(bj)
            try:
                data = self.fetch_page(sigungu_cd, bjdong_cd=bjdong_cd, num_of_rows=1)
                total = _safe_int(
                    data.get("response", {}).get("body", {}).get("totalCount", 0)
                )
                if total > 0:
                    found.append(bjdong_cd)
            except Exception:
                pass
        return found

    def fetch_apartments_by_sigungu(self, sigungu_cd: str) -> List[dict]:
        """시군구 전체 아파트 단지 수집 (총괄표제부 기준).

        법정동 코드를 자동 탐색 후 법정동별로 페이지네이션하여 아파트만 반환.
        """
        bjdong_codes = self.discover_bjdong_codes(sigungu_cd)
        results: List[dict] = []
        for bjdong_cd in bjdong_codes:
            results.extend(self._fetch_by_bjdong(sigungu_cd, bjdong_cd))
        return results

    def _fetch_by_bjdong(self, sigungu_cd: str, bjdong_cd: str) -> List[dict]:
        page_no = 1
        num_of_rows = 100
        results: List[dict] = []
        while True:
            data = self.fetch_page(
                sigungu_cd, bjdong_cd=bjdong_cd, page_no=page_no, num_of_rows=num_of_rows
            )
            items = self._extract_items(data)
            if not items:
                break
            results.extend(i for i in items if _is_apartment(i))
            total = _safe_int(
                data.get("response", {}).get("body", {}).get("totalCount", 0)
            )
            if page_no * num_of_rows >= total:
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
        # 총괄표제부: mainBldCnt(동수). 구버전 호환을 위해 dongCnt도 fallback.
        total_buildings = _to_int(item.get("mainBldCnt") or item.get("dongCnt"))
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
            "total_buildings": total_buildings,
            "floor_area_ratio": _to_float(item.get("vlRat")),
            "building_coverage_ratio": _to_float(item.get("bcRat")),
        }


def _safe_int(val) -> int:
    try:
        return int(val)
    except (ValueError, TypeError):
        return 0


def _to_int(val) -> Optional[int]:
    if val is None:
        return None
    try:
        v = str(val).strip()
        return int(v) if v else None
    except (ValueError, TypeError):
        return None


def _to_float(val) -> Optional[float]:
    if val is None:
        return None
    try:
        v = str(val).strip()
        return float(v) if v else None
    except (ValueError, TypeError):
        return None
