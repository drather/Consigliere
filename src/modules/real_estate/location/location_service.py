from typing import Optional

from modules.real_estate.location.location_repository import LocationRepository
from modules.real_estate.location.location_scorer import LocationScore, LocationScorer
from modules.real_estate.poi_collector import PoiCollector, PoiData


class LocationService:
    """POI 수집 + 입지점수 계산 + 저장을 통합하는 서비스."""

    def __init__(
        self,
        loc_repo: LocationRepository,
        poi_collector: PoiCollector,
        scorer: LocationScorer,
    ):
        self._loc_repo = loc_repo
        self._poi_collector = poi_collector
        self._scorer = scorer

    def get_score(self, complex_code: str) -> Optional[LocationScore]:
        """저장된 입지점수 반환. 없으면 None."""
        return self._loc_repo.get_score(complex_code)

    def get_poi_cached(self, complex_code: str) -> Optional[PoiData]:
        """POI 캐시 조회 (API 호출 없음). 캐시 없거나 만료되면 None."""
        return self._poi_collector.get_cached(complex_code)

    def enrich_and_save(self, complex_code: str, candidate: dict) -> LocationScore:
        """candidate dict 기반 스코어링 → 저장 → 반환."""
        score = self._scorer.score(candidate)
        self._loc_repo.upsert_score(score)
        return score
