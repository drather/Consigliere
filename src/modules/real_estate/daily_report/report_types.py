from typing import List, Optional
from typing_extensions import TypedDict


class TxPoint(TypedDict):
    price_eok: float    # 억 단위 (예: 8.8)
    deal_date: str      # "YYYY-MM-DD"


class TrendData(TypedDict):
    points: List[TxPoint]   # 날짜순 정렬
    avg_eok: float           # 평균가 (억)
    change_pct: float        # 전월비 변동률 (%)
    area_sqm: float          # 전용면적 (㎡)


class CommuteData(TypedDict):
    transit_minutes: Optional[int]
    car_minutes: Optional[int]
    walk_minutes: Optional[int]
    route_summary: str       # 빈 문자열이면 표시 안 함


class CandidateSummary(TypedDict):
    apt_name: str
    sigungu: str
    area_sqm: float
    household_count: int
    composite_score: int     # 0~100 정수
    verdict: str
    key_points: List[str]
    trend: TrendData
    commute: CommuteData
    residential_results: List    # List[DimensionResult]
    investment_results: List     # List[DimensionResult]
