from typing import List
from modules.real_estate.location.dimensions.base import BaseDimension


class SchoolPremiumDimension(BaseDimension):
    @property
    def dimension_id(self) -> str:
        return "school_premium"

    @property
    def label(self) -> str:
        return "🎒 학군프리미엄"

    def score(self, candidate: dict) -> int:
        school_score = candidate.get("school_score")
        if school_score is not None:
            return int(school_score)
        return self._config.get("data_absent_neutral", 50)

    def evidence(self, candidate: dict) -> List[str]:
        poi = candidate.get("_poi")
        if not poi:
            return []
        return [
            f"학교: {poi.schools_count}개",
            f"학원: {poi.academies_count}개",
        ]
