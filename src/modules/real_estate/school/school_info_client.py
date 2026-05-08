import os
from typing import Any, Dict, List, Optional

import requests

try:
    from core.logger import get_logger
    logger = get_logger(__name__)
except ImportError:
    import logging
    logger = logging.getLogger(__name__)

_BASE_URL = "https://www.schoolinfo.go.kr/openApi.do"

# apiType values — verified via smoke test against schoolinfo.go.kr (2026-05-09)
# apiType=0 : 학교기본정보 — no pbanYr required
# apiType=10: 학생현황 (STDNT_SUM, COL_2xx class counts) — pbanYr required
# apiType=17: 교원현황 (ML_TOI_FGR, FML_TOI_FGR, COL_1=total) — pbanYr required
# apiType=1~9, 11~16, 19, 23~26: 미공시 또는 다른 공시항목
_API_TYPE_SCHOOL_INFO = "0"    # 학교기본정보
_API_TYPE_STUDENT = "10"       # 학생 현황 (학급 수, 학생 수)
_API_TYPE_TEACHER = "17"       # 교원 현황 (교원 수)


class SchoolInfoClient:
    def __init__(self, api_key: Optional[str] = None):
        self._api_key = api_key or os.getenv("SCHOOLINFO_API_KEY", "")

    def _fetch(
        self,
        api_type: str,
        sido_code: str,
        sgg_code: str,
        school_kind: str,
        pban_yr: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        params: Dict[str, str] = {
            "apiKey": self._api_key,
            "apiType": api_type,
            "sidoCode": sido_code,
            "sggCode": sgg_code,
            "schulKndCode": school_kind,
        }
        if pban_yr:
            params["pbanYr"] = pban_yr
        if api_type in (_API_TYPE_STUDENT, _API_TYPE_TEACHER) and not pban_yr:
            logger.warning(f"[SchoolInfoClient] apiType={api_type} requires pbanYr — skipping request")
            return []
        try:
            logger.info(f"[SchoolInfoClient] apiType={api_type} sido={sido_code} sgg={sgg_code} kind={school_kind} pbanYr={pban_yr}")
            resp = requests.get(_BASE_URL, params=params, timeout=15)
            resp.raise_for_status()
            data = resp.json()
            if data.get("resultCode") != "success":
                logger.warning(f"[SchoolInfoClient] API 오류: {data.get('resultMsg')}")
                return []
            return data.get("list", [])
        except Exception as e:
            logger.error(f"[SchoolInfoClient] 요청 실패 apiType={api_type}: {e}")
            return []

    def get_school_list(
        self, sido_code: str, sgg_code: str, school_kind: str
    ) -> List[Dict[str, Any]]:
        """학교기본정보 조회 (apiType=0). pbanYr 불필요."""
        return self._fetch(_API_TYPE_SCHOOL_INFO, sido_code, sgg_code, school_kind)

    def get_student_counts(
        self, sido_code: str, sgg_code: str, school_kind: str, pban_yr: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """학생현황 조회 (apiType=10). STDNT_SUM, COL_2xx 필드 포함."""
        return self._fetch(_API_TYPE_STUDENT, sido_code, sgg_code, school_kind, pban_yr)

    def get_teacher_counts(
        self, sido_code: str, sgg_code: str, school_kind: str, pban_yr: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """교원현황 조회 (apiType=17). ML_TOI_FGR, FML_TOI_FGR, COL_1 필드 포함."""
        return self._fetch(_API_TYPE_TEACHER, sido_code, sgg_code, school_kind, pban_yr)
