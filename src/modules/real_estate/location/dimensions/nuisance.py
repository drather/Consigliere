from modules.real_estate.location.dimensions.base import BaseDimension


class NuisanceDimension(BaseDimension):
    @property
    def dimension_id(self) -> str:
        return "nuisance"

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
