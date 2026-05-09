from modules.real_estate.location.dimensions.base import BaseDimension


class CommercialDimension(BaseDimension):
    @property
    def dimension_id(self) -> str:
        return "commercial"

    def score(self, candidate: dict) -> int:
        total = (
            (candidate.get("poi_restaurant_count") or 0)
            + (candidate.get("poi_cafe_count") or 0)
        )
        if total >= self._config.get("high_count", 30):
            return 100
        if total >= self._config.get("medium_count", 10):
            return 60
        return 20
