from modules.real_estate.location.dimensions.base import BaseDimension


class MedicalDimension(BaseDimension):
    @property
    def dimension_id(self) -> str:
        return "medical"

    @property
    def label(self) -> str:
        return "medical"  # TODO(task2): replace with emoji label

    def score(self, candidate: dict) -> int:
        count = candidate.get("poi_medical_count")
        if count is None:
            return self._config.get("data_absent_neutral", 50)
        if count >= self._config.get("high_count", 3):
            return 100
        if count >= self._config.get("medium_count", 1):
            return 60
        return 20
