"""
TrendAnalyzer — transactions 테이블에서 단지별 실거래가 추세를 집계한다.
"""
import sqlite3
from dataclasses import dataclass
from datetime import date, timedelta
from typing import Optional

from core.logger import get_logger

logger = get_logger(__name__)

_AREA_TOLERANCE = 5.0  # 전용면적 ±5㎡ 허용


@dataclass
class TrendData:
    apt_master_id: int
    area_sqm: float
    avg_price: int
    price_change_pct: float
    monthly_volume: float
    price_min: int
    price_max: int
    sample_count: int

    def avg_price_eok(self) -> str:
        eok = self.avg_price / 1_00_000_000
        return f"{eok:.1f}억"

    def price_change_str(self) -> str:
        sign = "+" if self.price_change_pct >= 0 else ""
        return f"{sign}{self.price_change_pct:.1f}%"


class TrendAnalyzer:
    def __init__(self, db_path: str):
        self._db_path = db_path

    def get_trend(
        self,
        apt_master_id: int,
        area_sqm: float,
        months: int = 6,
    ) -> Optional[TrendData]:
        since = (date.today() - timedelta(days=30 * months)).strftime("%Y-%m-%d")
        mid = (date.today() - timedelta(days=30 * (months // 2))).strftime("%Y-%m-%d")
        area_min = area_sqm - _AREA_TOLERANCE
        area_max = area_sqm + _AREA_TOLERANCE

        with sqlite3.connect(self._db_path) as conn:
            rows = conn.execute(
                "SELECT price, deal_date FROM transactions "
                "WHERE apt_master_id = ? "
                "  AND exclusive_area BETWEEN ? AND ? "
                "  AND deal_date >= ? "
                "ORDER BY deal_date",
                (apt_master_id, area_min, area_max, since),
            ).fetchall()

        if not rows:
            return None

        prices = [r[0] for r in rows]
        avg_price = sum(prices) // len(prices)

        recent = [r[0] for r in rows if r[1] >= mid]
        older = [r[0] for r in rows if r[1] < mid]
        if recent and older:
            recent_avg = sum(recent) / len(recent)
            older_avg = sum(older) / len(older)
            change_pct = round((recent_avg - older_avg) / older_avg * 100, 1)
        else:
            change_pct = 0.0

        monthly_volume = round(len(rows) / months, 1)

        return TrendData(
            apt_master_id=apt_master_id,
            area_sqm=area_sqm,
            avg_price=avg_price,
            price_change_pct=change_pct,
            monthly_volume=monthly_volume,
            price_min=min(prices),
            price_max=max(prices),
            sample_count=len(rows),
        )
