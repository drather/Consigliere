from dataclasses import dataclass, field
from typing import List


@dataclass
class CommuteResult:
    origin_key: str          # 캐시 식별자: "{district_code}__{apt_name}"
    destination: str         # 예: "삼성역"
    mode: str                # "transit" | "car" | "walking"
    duration_minutes: int
    distance_meters: int
    cached: bool = field(default=False)
    legs: List[dict] = field(default_factory=list)   # 구조화 단계 목록
    route_summary: str = ""                           # LLM용 한 줄 요약
