from dataclasses import dataclass
from typing import List, Optional


@dataclass
class AggregatedTransaction:
    apt_master_id: int
    apt_name: str
    district_code: str
    sigungu: str
    complex_code: Optional[str]
    recent_tx_count: int
    avg_recent_price: float        # 원 단위
    price_change_pct: float        # 직전 30일 대비 변동률 (%)
    exclusive_area: float          # 가장 많이 거래된 면적 (㎡)
    household_count: int
    composite_score: float         # 0.0 ~ 1.0
    road_address: Optional[str] = None   # geocode/commute용
    pnu: Optional[str] = None            # 건물대장 조회용


@dataclass
class DailyReport:
    date: str                      # YYYY-MM-DD
    analysis_period: str           # "2026-05-01 ~ 2026-05-03"
    total_transactions: int
    top_k: int
    macro_summary: str
    market_summary: str            # LLM 생성 시장 총평
    candidates: List[dict]         # enrich 완료 단지 목록 (직렬화 가능)
    markdown: str                  # 최종 렌더링 MD
    generated_at: str
