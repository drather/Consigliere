from dataclasses import dataclass, field


@dataclass
class CommuteResult:
    origin_key: str          # 캐시 식별자: "{district_code}__{apt_name}"
    destination: str         # 예: "삼성역"
    mode: str                # "transit" | "car" | "walking"
    duration_minutes: int
    distance_meters: int
    cached: bool = field(default=False)
