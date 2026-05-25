from typing import Any, List, Optional
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
    composite_score: float   # 0.0 ~ 1.0 (aggregator 원본 값; 화면 표시 시 * 100)
    verdict: str
    key_points: List[str]
    trend: TrendData
    commute: CommuteData
    residential_results: List[Any]   # List[DimensionResult]
    investment_results: List[Any]    # List[DimensionResult]


class SubwayStation(TypedDict):
    name: str           # "강남"
    line: str           # "2호선"
    walk_minutes: int   # 도보 분


class LocationSummaryData(TypedDict, total=False):
    # 역세권
    subway_stations: List[SubwayStation]
    # 생활편의
    mart_count: int
    convenience_count: int
    cafe_count: int
    restaurant_count: int
    pharmacy_count: int
    medical_count: int
    # 자연
    park_nearest_m: int     # 0 = 반경 내 없음
    # 학군
    school_nearby_count: int
    school_transfer_rate: float   # 0.0~1.0
    school_avg_per_teacher: float
    school_score: int             # 0~100
    school_label: str             # "학군 우수" / "학군 양호" / "학군 평이"
    # 혐오시설
    nuisance_high_count: int
    nuisance_mid_count: int


class SimilarUnitData(TypedDict):
    name: str
    price_per_sqm: float


class CompData(TypedDict, total=False):
    district_avg_per_sqm: float
    pct_vs_avg: float
    similar_units: List[SimilarUnitData]


class YieldData(TypedDict, total=False):
    jeonse_rate: float
    jeonse_avg: int
    gap_cost: int
    monthly_cost: int
    jeonse_sample: int


class SupplyData(TypedDict, total=False):
    nearby_units: int
    supply_period: str
    news_catalysts: List[dict]
