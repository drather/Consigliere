"""
ApartmentMasterClient — 국토교통부 공동주택 공공 API 클라이언트.

API 1: 공동주택 전체 단지 목록 (getTotalAptList3)
  - 전체 목록 조회 후 bjdCode prefix로 시군구 필터링

API 2: 공동주택 기본정보 (getAphusBassInfoV4)
  - kaptCode → hoCnt, kaptDongCnt, kaptBcompany, kaptUsedate 등
"""
import os
import logging
import requests
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

_BASE_LIST_URL = os.getenv(
    "APT_MASTER_LIST_URL",
    "https://apis.data.go.kr/1613000/AptListService3/getTotalAptList3",
)
_BASE_INFO_URL = os.getenv(
    "APT_MASTER_INFO_URL",
    "https://apis.data.go.kr/1613000/AptBasisInfoServiceV4/getAphusBassInfoV4",
)

_PAGE_SIZE = 10000


class ApartmentMasterClient:
    def __init__(self, api_key: Optional[str] = None):
        self._api_key = api_key or os.getenv("MOLIT_APT_LIST_API_KEY") or os.getenv("MOLIT_API_KEY", "")
        self._complexes_cache: Optional[List[Dict]] = None  # build_initial 효율화용

    def fetch_complex_list(self, sigungu_cd: str) -> List[Dict]:
        """시군구코드(5자리) → 단지 목록 [{kaptCode, kaptName, bjdCode}, ...].

        전체 목록(getTotalAptList3)에서 bjdCode prefix로 필터링.
        """
        all_complexes = self._fetch_all_complexes()
        return [c for c in all_complexes if str(c.get("bjdCode", "")).startswith(sigungu_cd)]

    def _fetch_all_complexes(self) -> List[Dict]:
        """전체 공동주택 단지 목록 페이지네이션 수집 (in-memory 캐시).

        API 응답: items 필드가 list 직접 반환 (dict 래핑 없음).
        """
        if self._complexes_cache is not None:
            return self._complexes_cache

        results: List[Dict] = []
        page = 1

        while True:
            params = {
                "serviceKey": self._api_key,
                "numOfRows": str(_PAGE_SIZE),
                "pageNo": str(page),
                "_type": "json",
            }
            try:
                resp = requests.get(_BASE_LIST_URL, params=params, timeout=30)
                resp.raise_for_status()
                data = resp.json()
                body = data.get("response", {}).get("body", {})
                total = int(body.get("totalCount", 0))
                items = body.get("items", [])

                if not items:
                    break

                if isinstance(items, list):
                    results.extend(items)
                elif isinstance(items, dict):
                    # 하위 호환: 구버전 API가 {"item": [...]} 형태로 반환하는 경우
                    item_list = items.get("item", [])
                    if isinstance(item_list, dict):
                        item_list = [item_list]
                    results.extend(item_list)

                if len(results) >= total:
                    break
                page += 1

            except Exception as e:
                logger.warning(f"[AptMasterClient] _fetch_all_complexes page={page} 실패: {e}")
                break

        self._complexes_cache = results
        logger.info(f"[AptMasterClient] 전체 단지 목록 수집 완료: {len(results)}건")
        return results

    def fetch_complex_info(self, kapt_code: str) -> Optional[Dict]:
        """단지코드 → 기본정보 dict (hoCnt, kaptDongCnt, kaptBcompany, kaptUsedate 등)."""
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
