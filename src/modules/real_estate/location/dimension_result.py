from dataclasses import dataclass, field
from typing import List


@dataclass
class DimensionResult:
    id: str
    label: str
    score: int
    evidence: List[str] = field(default_factory=list)
