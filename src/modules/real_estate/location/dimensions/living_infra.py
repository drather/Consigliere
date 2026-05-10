from typing import List
from modules.real_estate.location.dimensions.base import BaseDimension


class LivingInfraDimension(BaseDimension):
    @property
    def dimension_id(self) -> str:
        return "living_infra"

    @property
    def label(self) -> str:
        return "🛒 생활인프라"

    def score(self, candidate: dict) -> int:
        total = (
            (candidate.get("poi_convenience_count") or 0)
            + (candidate.get("poi_pharmacy_count") or 0)
            + (candidate.get("poi_marts_count") or 0)
        )
        high = self._config.get("high_count", 5)
        medium = self._config.get("medium_count", 2)
        if total >= high:
            return 100
        if total >= medium:
            return 60
        return 20

    def evidence(self, candidate: dict) -> List[str]:
        poi = candidate.get("_poi")
        if not poi:
            return []
        return [
            f"편의점: {poi.convenience_count}개",
            f"약국: {poi.pharmacy_count}개",
            f"마트/백화점: {poi.marts_count}개",
        ]
