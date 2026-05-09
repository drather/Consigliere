from abc import ABC, abstractmethod


class BaseDimension(ABC):
    def __init__(self, config: dict):
        self._config = config

    @abstractmethod
    def score(self, candidate: dict) -> int:
        """Return 0-100. Return data_absent_neutral when data unavailable."""

    @property
    @abstractmethod
    def dimension_id(self) -> str:
        """Unique identifier matching config.yaml dimension id."""
