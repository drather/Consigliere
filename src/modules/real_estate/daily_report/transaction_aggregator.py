import sqlite3
from datetime import date, timedelta
from typing import Dict, List, Optional

from core.logger import get_logger

logger = get_logger(__name__)

_AGGREGATE_SQL = """
WITH recent AS (
    SELECT
        t.apt_master_id,
        COUNT(*) AS recent_tx_count,
        AVG(t.price) AS avg_recent_price
    FROM transactions t
    WHERE t.deal_date >= :date_from
      AND t.apt_master_id IS NOT NULL
    GROUP BY t.apt_master_id
),
prior AS (
    SELECT
        apt_master_id,
        AVG(price) AS prior_avg_price
    FROM transactions
    WHERE deal_date >= :date_prior AND deal_date < :date_from
      AND apt_master_id IS NOT NULL
    GROUP BY apt_master_id
),
top_area AS (
    SELECT apt_master_id, exclusive_area
    FROM (
        SELECT apt_master_id, exclusive_area,
               ROW_NUMBER() OVER (PARTITION BY apt_master_id ORDER BY COUNT(*) DESC) AS rn
        FROM transactions
        WHERE deal_date >= :date_from AND apt_master_id IS NOT NULL
        GROUP BY apt_master_id, exclusive_area
    ) WHERE rn = 1
)
SELECT
    am.id                          AS apt_master_id,
    am.apt_name,
    am.district_code,
    am.sigungu,
    am.complex_code,
    r.recent_tx_count,
    r.avg_recent_price,
    COALESCE(
        CASE WHEN p.prior_avg_price > 0
             THEN (r.avg_recent_price - p.prior_avg_price) / p.prior_avg_price * 100.0
             ELSE 0.0 END,
        0.0
    )                              AS price_change_pct,
    COALESCE(ta.exclusive_area, 84.0) AS exclusive_area,
    COALESCE(a.household_count, 0) AS household_count,
    a.road_address,
    am.pnu
FROM recent r
JOIN apt_master am ON r.apt_master_id = am.id
LEFT JOIN prior p ON r.apt_master_id = p.apt_master_id
LEFT JOIN top_area ta ON r.apt_master_id = ta.apt_master_id
LEFT JOIN apartments a ON am.complex_code = a.complex_code
ORDER BY r.recent_tx_count DESC
LIMIT :limit
"""

_RECENT_TX_SQL = """
SELECT price, deal_date
FROM transactions
WHERE apt_master_id = :apt_master_id
  AND deal_date >= :date_from
ORDER BY deal_date ASC
LIMIT 10
"""


class TransactionAggregator:
    """최근 N일 실거래를 집계해 composite_score 상위 K개 단지를 반환한다."""

    def __init__(self, db_path: str = "data/real_estate.db"):
        self._db_path = db_path

    def aggregate(
        self,
        days: int = 3,
        top_k: int = 10,
        persona: Optional[Dict] = None,
        budget_available: int = 0,
    ) -> List[Dict]:
        """반환: List[dict] — 집계 필드 + _recent_tx_points."""
        today = date.today()
        date_from = (today - timedelta(days=days)).isoformat()
        date_prior = (today - timedelta(days=days + 30)).isoformat()

        try:
            conn = sqlite3.connect(self._db_path)
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                _AGGREGATE_SQL,
                {"date_from": date_from, "date_prior": date_prior, "limit": top_k * 3},
            ).fetchall()
        except sqlite3.Error as e:
            logger.error("[Aggregator] DB 조회 실패: %s", e)
            return []

        if not rows:
            conn.close()
            return []

        raw = [dict(r) for r in rows]

        for item in raw:
            tx_rows = conn.execute(
                _RECENT_TX_SQL,
                {"apt_master_id": item["apt_master_id"], "date_from": date_from},
            ).fetchall()
            item["_recent_tx_points"] = [
                {
                    "price_eok": round(r["price"] / 100_000_000, 2),
                    "deal_date": r["deal_date"],
                }
                for r in tx_rows
            ]
        conn.close()

        max_tx = max(r["recent_tx_count"] for r in raw) or 1
        persona = persona or {}

        for item in raw:
            item["composite_score"] = self._composite_score(
                recent_tx_count=item["recent_tx_count"],
                max_tx_count=max_tx,
                price_change_pct=item["price_change_pct"],
                sigungu=item["sigungu"],
                avg_recent_price=item["avg_recent_price"],
                household_count=item["household_count"],
                persona=persona,
                budget_available=budget_available,
            )

        raw.sort(key=lambda x: x["composite_score"], reverse=True)
        logger.info(
            "[Aggregator] 최근 %d일 거래 집계 완료 — 단지 %d개 → 상위 %d개 선택",
            days, len(raw), top_k,
        )
        return raw[:top_k]

    @staticmethod
    def _composite_score(
        recent_tx_count: int,
        max_tx_count: int,
        price_change_pct: float,
        sigungu: str,
        avg_recent_price: float,
        household_count: int,
        persona: Dict,
        budget_available: int,
        weights: Optional[Dict] = None,
    ) -> float:
        w = weights or {"tx": 0.4, "price": 0.3, "persona": 0.3}
        tx_score = recent_tx_count / max_tx_count if max_tx_count > 0 else 0.0
        price_signal = min(abs(price_change_pct) / 10.0, 1.0)
        interest_areas = persona.get("user", {}).get("interest_areas", [])
        min_hh = persona.get("apartment_preferences", {}).get("min_household_count", 0)
        budget_fit = 1.0
        if budget_available > 0:
            if avg_recent_price <= budget_available:
                budget_fit = 1.0
            else:
                budget_fit = max(0.0, 1.0 - (avg_recent_price - budget_available) / budget_available)
        area_fit = 1.0 if sigungu in interest_areas else 0.5
        household_fit = 1.0 if (min_hh == 0 or household_count >= min_hh) else 0.0
        persona_affinity = (budget_fit + area_fit + household_fit) / 3
        return (
            tx_score * w["tx"]
            + price_signal * w["price"]
            + persona_affinity * w["persona"]
        )
