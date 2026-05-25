import os
import requests
from typing import List, Tuple
from core.logger import get_logger
from .models import SupplySchedule

logger = get_logger(__name__)

_BASE_URL = "https://api.odcloud.kr/api/ApplyhomeInfoDetailSvc/v1/getAPTLttotPblancDetail"

# HSSPLY_ADRES에서 키워드 매칭으로 대략적 좌표 추출
_ADDR_CENTROIDS: dict[str, Tuple[float, float]] = {
    # 서울 자치구
    "종로구": (37.5730, 126.9794), "용산구": (37.5384, 126.9654),
    "성동구": (37.5633, 127.0371), "광진구": (37.5384, 127.0822), "동대문구": (37.5744, 127.0398),
    "중랑구": (37.6063, 127.0927), "성북구": (37.5894, 127.0167), "강북구": (37.6396, 127.0256),
    "도봉구": (37.6688, 127.0472), "노원구": (37.6541, 127.0568), "은평구": (37.6176, 126.9227),
    "서대문구": (37.5791, 126.9368), "마포구": (37.5663, 126.9010), "양천구": (37.5170, 126.8664),
    "강서구": (37.5509, 126.8495), "구로구": (37.4954, 126.8874), "금천구": (37.4569, 126.8955),
    "영등포구": (37.5264, 126.8962), "동작구": (37.5124, 126.9393), "관악구": (37.4784, 126.9516),
    "서초구": (37.4837, 127.0324), "강남구": (37.5172, 127.0473), "송파구": (37.5145, 127.1059),
    "강동구": (37.5301, 127.1238), "중구": (37.5641, 126.9977),
    # 인천
    "미추홀구": (37.4638, 126.6503), "연수구": (37.4101, 126.6800), "남동구": (37.4469, 126.7314),
    "부평구": (37.5074, 126.7220), "계양구": (37.5376, 126.7374),
    # 경기 자치구
    "권선구": (37.2548, 126.9975), "영통구": (37.2459, 127.0554), "팔달구": (37.2812, 127.0170),
    "장안구": (37.3047, 127.0192), "분당구": (37.3825, 127.1195), "수정구": (37.4474, 127.1370),
    "중원구": (37.4200, 127.1264), "덕양구": (37.6340, 126.8357), "일산동구": (37.6561, 126.7842),
    "일산서구": (37.6745, 126.7485), "기흥구": (37.2711, 127.1146), "수지구": (37.3218, 127.0967),
    "처인구": (37.2339, 127.2004), "오정구": (37.5034, 126.7660),
    # 경기 시
    "수원시": (37.2636, 127.0286), "성남시": (37.4196, 127.1267), "고양시": (37.6584, 126.8320),
    "용인시": (37.2411, 127.1775), "부천시": (37.5034, 126.7660), "안산시": (37.3219, 126.8309),
    "화성시": (37.2000, 126.8319), "남양주시": (37.6360, 127.2166), "안양시": (37.3943, 126.9568),
    "의정부시": (37.7382, 127.0428), "시흥시": (37.3800, 126.8029), "파주시": (37.7601, 126.7799),
    "광주시": (37.4296, 127.2558), "김포시": (37.6150, 126.7162), "광명시": (37.4784, 126.8665),
    "군포시": (37.3617, 126.9350), "하남시": (37.5398, 127.2149), "오산시": (37.1498, 127.0774),
    "이천시": (37.2722, 127.4348), "안성시": (37.0079, 127.2836), "의왕시": (37.3447, 126.9684),
    "양주시": (37.7852, 127.0459), "평택시": (36.9921, 127.1122), "과천시": (37.4291, 126.9878),
    "구리시": (37.5946, 127.1296), "포천시": (37.8948, 127.2003), "여주시": (37.2982, 127.6367),
}

_DEFAULT_LAT_LNG: Tuple[float, float] = (37.5665, 126.9780)


def _extract_lat_lng(addr: str) -> Tuple[float, float]:
    for keyword, coords in _ADDR_CENTROIDS.items():
        if keyword in addr:
            return coords
    return _DEFAULT_LAT_LNG


class SupplyClient:
    def __init__(self):
        self._key = os.getenv("APPLYHOME_API_KEY", "")

    def fetch(self, page: int = 1, per_page: int = 500) -> List[SupplySchedule]:
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
            addr = item.get("HSSPLY_ADRES", "")
            count_raw = item.get("TOT_SUPLY_HSHLDCO", 0)
            mvin_ym = item.get("MVN_PREARNGE_YM", "")
            sigungu_code = item.get("SUBSCRPT_AREA_CODE", "")

            try:
                count = int(count_raw) if count_raw else 0
                mvin_str = str(mvin_ym)
                expected = f"{mvin_str[:4]}-{mvin_str[4:6]}" if len(mvin_str) >= 6 else ""
            except (ValueError, TypeError):
                continue

            if not name or count == 0 or not expected:
                continue

            lat, lng = _extract_lat_lng(addr)
            results.append(SupplySchedule(
                project_name=name, sigungu_code=sigungu_code,
                lat=lat, lng=lng,
                household_count=count, expected_date=expected,
                supply_type="move_in"
            ))

        logger.info("[SupplyClient] %d건 파싱", len(results))
        return results
