from modules.real_estate.location.dimensions.base import BaseDimension


class NatureDimension(BaseDimension):
    @property
    def dimension_id(self) -> str:
        return "nature"

    def score(self, candidate: dict) -> int:
        dist_m = candidate.get("poi_park_nearest_m")
        if not dist_m:
            return self._config.get("data_absent_neutral", 50)
        if dist_m <= self._config.get("close_m", 300):
            return 100
        if dist_m <= self._config.get("medium_m", 800):
            return 60
        return 20
