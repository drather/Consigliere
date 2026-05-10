from typing import List
from modules.real_estate.location.dimensions.base import BaseDimension


class NuisanceDimension(BaseDimension):
    @property
    def dimension_id(self) -> str:
        return "nuisance"

    @property
    def label(self) -> str:
        return "⚠️ 혐오시설"

    def score(self, candidate: dict) -> int:
        if "poi_nuisance_high_count" not in candidate:
            return self._config.get("data_absent_neutral", 50)

        high = candidate.get("poi_nuisance_high_count") or 0
        mid = candidate.get("poi_nuisance_mid_count") or 0

        cfg = self._config
        if high > 0:
            return cfg.get("high_score", 20)
        if mid > 0:
            return cfg.get("mid_score", 60)
        return cfg.get("clean_score", 100)

    def evidence(self, candidate: dict) -> List[str]:
        high = candidate.get("poi_nuisance_high_count") or 0
        mid = candidate.get("poi_nuisance_mid_count") or 0
        if high == 0 and mid == 0:
            return ["혐오시설 없음 (9개 키워드 조사)"]
        lines = []
        if high > 0:
            lines.append(f"고강도 혐오시설 {high}종 탐지 (화장장·교도소·하수처리장 등)")
        if mid > 0:
            lines.append(f"중강도 혐오시설 {mid}종 탐지 (장례식장·변전소)")
        return lines
