from dataclasses import dataclass, field
from typing import List


@dataclass
class SimilarUnit:
    name: str
    price_per_sqm: float    # 원/㎡


@dataclass
class ComparativeResult:
    district_avg_per_sqm: float     # 원/㎡
    pct_vs_avg: float               # %, 양수=비쌈 음수=저렴
    similar_units: List[SimilarUnit] = field(default_factory=list)
