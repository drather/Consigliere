from modules.real_estate.location.dimensions.base import BaseDimension


class EducationDimension(BaseDimension):
    @property
    def dimension_id(self) -> str:
        return "education"

    def score(self, candidate: dict) -> int:
        school_score = candidate.get("school_score")
        if school_score is not None:
            return int(school_score)
        return self._config.get("data_absent_neutral", 50)
