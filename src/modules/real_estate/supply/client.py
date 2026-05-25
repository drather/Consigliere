import os
import requests
from typing import List
from core.logger import get_logger
from .models import SupplySchedule

logger = get_logger(__name__)

_BASE_URL = "https://api.odcloud.kr/api/ApplyhomeInfoDetailSvc/v1/getAPTLttotPblancDetail"

# 시군구명 → sigungu_code 매핑 (주요 수도권)
_SIGUNGU_MAP = {
    "서초구": "11650", "강남구": "11680", "송파구": "11710", "강동구": "11740",
    "성동구": "11200", "광진구": "11215", "용산구": "11170", "종로구": "11110",
    "강서구": "11500", "마포구": "11440", "성북구": "11290", "노원구": "11350",
    "분당구": "41135", "수정구": "41131", "중원구": "41133",
}

_CENTROIDS = {
    "11650": (37.4837, 127.0324), "11680": (37.5172, 127.0473),
    "11710": (37.5145, 127.1059), "11740": (37.5301, 127.1238),
    "11200": (37.5633, 127.0371), "11215": (37.5384, 127.0822),
    "11170": (37.5384, 126.9654), "11110": (37.5730, 126.9794),
    "11500": (37.5509, 126.8495), "11440": (37.5663, 126.9010),
    "11290": (37.5894, 127.0167), "11350": (37.6541, 127.0568),
    "41135": (37.3825, 127.1195), "41131": (37.4474, 127.1370),
    "41133": (37.4200, 127.1264),
}


class SupplyClient:
    def __init__(self):
        self._key = os.getenv("APPLYHOME_API_KEY", "")

    def fetch(self, page: int = 1, per_page: int = 100) -> List[SupplySchedule]:
        params = {
            "serviceKey": self._key,
            "page": page,
            "perPage": per_page,
        }
        try:
            resp = requests.get(_BASE_URL, params=params, timeout=15)
            resp.raise_for_status()
            data = resp.json()
        except Exception as e:
            logger.error("[SupplyClient] fetch 실패: %s", e)
            return []

        results = []
        for item in data.get("data", []):
            name = item.get("HOUSE_NM", "")
            area_nm = item.get("SUBSCRPT_AREA_CODE_NM", "")
            count_raw = item.get("TOT_SUPLY_HSHLDCO", 0)
            mvin_ym = item.get("MVIN_PREARNGE_YM", "")
            sigungu_code = _SIGUNGU_MAP.get(area_nm, "")

            try:
                count = int(count_raw) if count_raw else 0
                expected = f"{str(mvin_ym)[:4]}-{str(mvin_ym)[4:6]}" if len(str(mvin_ym)) >= 6 else ""
            except (ValueError, TypeError):
                continue

            if not name or count == 0 or not expected or not sigungu_code:
                continue

            lat, lng = _CENTROIDS.get(sigungu_code, (37.5665, 126.9780))
            results.append(SupplySchedule(
                project_name=name, sigungu_code=sigungu_code,
                lat=lat, lng=lng,
                household_count=count, expected_date=expected,
                supply_type="move_in"
            ))
        logger.info("[SupplyClient] %d건 파싱", len(results))
        return results
