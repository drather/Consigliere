from abc import ABC, abstractmethod
from typing import List


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

    @property
    @abstractmethod
    def label(self) -> str:
        """Human-readable display label with emoji prefix."""

    def evidence(self, candidate: dict) -> List[str]:
        """Return 0-3 bullet strings explaining the score. Override in subclasses."""
        return []
