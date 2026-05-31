"""
대시보드 서비스 진입점.

규칙: 대시보드 뷰(views/)는 이 모듈만 import한다.
      sqlite3, Repository, requests 직접 사용 금지.
"""
import dataclasses
from typing import Optional

from api.dependencies import (
    get_location_service,
    get_apt_analysis_repo,
    get_apt_master_repo,
    get_apt_repo,
    get_bm_repo,
    get_apt_search_tx_limit,
    get_apt_search_map_limit,
)


def get_location_score(complex_code: str):
    """단지 입지점수(LocationScore 객체) 반환. 없으면 None."""
    return get_location_service().get_score(complex_code)


def get_location_score_as_dict(complex_code: str) -> Optional[dict]:
    """입지점수를 렌더링용 dict로 반환. 없으면 None."""
    score = get_location_service().get_score(complex_code)
    if score is None:
        return None
    return {
        "residential_total": score.residential_total,
        "investment_total": score.investment_total,
        "results": {
            "residential": [
                {"label": dr.label, "score": dr.score, "evidence": dr.evidence}
                for dr in score.residential_results
            ],
            "investment": [
                {"label": dr.label, "score": dr.score, "evidence": dr.evidence}
                for dr in score.investment_results
            ],
        },
    }


def get_poi_cached(complex_code: str) -> Optional[dict]:
    """POI 캐시 조회 (API 호출 없음). 없으면 None."""
    poi = get_location_service().get_poi_cached(complex_code)
    if poi is None:
        return None
    return {
        "subway_stations": poi.subway_stations,
        "schools_count": poi.schools_count,
        "academies_count": poi.academies_count,
        "marts_count": poi.marts_count,
        "convenience_count": poi.convenience_count,
        "pharmacy_count": poi.pharmacy_count,
        "medical_count": poi.medical_count,
        "park_nearest_m": poi.park_nearest_m,
        "restaurant_count": poi.restaurant_count,
        "cafe_count": poi.cafe_count,
        "nuisance_high_count": poi.nuisance_high_count,
        "nuisance_mid_count": poi.nuisance_mid_count,
    }


def get_latest_apt_analysis(complex_code: str) -> Optional[dict]:
    """최근 심층분석 결과 dict 반환. 없으면 None."""
    report = get_apt_analysis_repo().get_latest(complex_code)
    if report is None:
        return None
    return dataclasses.asdict(report)


# ── Tab1 AptMaster 래퍼 ───────────────────────────────────────────────────────


def count_apt_masters() -> int:
    """apt_master 테이블 전체 행 수. 0이면 마이그레이션 미실행."""
    return get_apt_master_repo().count()


def get_distinct_sidos() -> list:
    """검색 필터용 시도 목록."""
    return get_apt_master_repo().get_distinct_sidos()


def get_distinct_sigungus(sido_filter: str) -> list:
    """sido_filter 기준 시군구 목록. 빈 문자열이면 전체."""
    return get_apt_master_repo().get_distinct_sigungus(sido_filter)


def search_apt_masters(apt_name: str = "", sido: str = "", sigungu: str = "") -> list:
    """AptMasterEntry 목록 반환. 빈 문자열 파라미터는 필터 무시."""
    return get_apt_master_repo().search(apt_name=apt_name, sido=sido, sigungu=sigungu)


def get_apt_search_limits() -> tuple:
    """(tx_limit, map_limit) 반환. config apt_search_tx_limit / apt_search_map_limit."""
    return get_apt_search_tx_limit(), get_apt_search_map_limit()


def get_apt_details(complex_code: str):
    """complex_code 기준 ApartmentRepository.get(). 없으면 None."""
    return get_apt_repo().get(complex_code)


def get_building_master_by_pnu(pnu: str):
    """pnu(mgm_pk) 기준 BuildingMasterRepository.get_by_mgm_pk(). 없으면 None."""
    return get_bm_repo().get_by_mgm_pk(pnu)
