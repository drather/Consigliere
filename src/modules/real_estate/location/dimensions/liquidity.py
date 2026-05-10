from modules.real_estate.location.dimensions.base import BaseDimension


class LiquidityDimension(BaseDimension):
    @property
    def dimension_id(self) -> str:
        return "liquidity"

    @property
    def label(self) -> str:
        return "liquidity"  # TODO(task2): replace with emoji label

    def score(self, candidate: dict) -> int:
        households = candidate.get("household_count")
        if households is None:
            return self._config.get("data_absent_neutral", 50)
        if households >= self._config.get("high_households", 500):
            return 100
        if households >= self._config.get("medium_households", 300):
            return 60
        return 20
