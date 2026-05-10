from modules.real_estate.location.dimensions.base import BaseDimension


class LivingInfraDimension(BaseDimension):
    @property
    def dimension_id(self) -> str:
        return "living_infra"

    @property
    def label(self) -> str:
        return "living_infra"  # TODO(task2): replace with emoji label

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
