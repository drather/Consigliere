from datetime import date, timedelta
from typing import TYPE_CHECKING
from core.logger import get_logger
from .models import ComparativeResult, SimilarUnit

if TYPE_CHECKING:
    from modules.real_estate.transaction_repository import TransactionRepository

logger = get_logger(__name__)


class ComparativeAnalyzer:
    def __init__(self, tx_repo: "TransactionRepository", lookback_days: int = 90):
        self._repo = tx_repo
        self._lookback_days = lookback_days

    def analyze(
        self,
        complex_code: str,
        district_code: str,
        exclusive_area: float,
        build_year: int,
        avg_sale_price: int,
    ) -> ComparativeResult:
        cutoff = (date.today() - timedelta(days=self._lookback_days)).isoformat()
        area_lo, area_hi = exclusive_area - 10, exclusive_area + 10
        year_lo, year_hi = build_year - 5, build_year + 5

        try:
            conn = self._get_conn()
            rows = conn.execute(
                """SELECT apt_name,
                          avg(CAST(price AS REAL) / exclusive_area) AS avg_per_sqm,
                          count(*) AS cnt
                   FROM transactions
                   WHERE district_code = ?
                     AND exclusive_area BETWEEN ? AND ?
                     AND build_year BETWEEN ? AND ?
                     AND deal_date >= ?
                   GROUP BY apt_name
                   ORDER BY cnt DESC""",
                (district_code, area_lo, area_hi, year_lo, year_hi, cutoff)
            ).fetchall()
        except Exception as e:
            logger.warning("[ComparativeAnalyzer] 쿼리 실패: %s", e)
            return ComparativeResult(district_avg_per_sqm=0.0, pct_vs_avg=0.0)

        if not rows:
            return ComparativeResult(district_avg_per_sqm=0.0, pct_vs_avg=0.0)

        all_avg = sum(r["avg_per_sqm"] for r in rows) / len(rows)
        my_per_sqm = avg_sale_price / exclusive_area if exclusive_area > 0 else 0
        pct = ((my_per_sqm - all_avg) / all_avg * 100) if all_avg > 0 else 0.0

        target_name = self._get_name_for_code(complex_code)
        similar = [
            SimilarUnit(name=r["apt_name"], price_per_sqm=r["avg_per_sqm"])
            for r in rows
            if r["apt_name"] != target_name
        ][:3]

        return ComparativeResult(
            district_avg_per_sqm=round(all_avg, 0),
            pct_vs_avg=round(pct, 1),
            similar_units=similar,
        )

    def _get_conn(self):
        # TransactionRepository._conn() is a callable factory:
        # - for :memory: DB it returns the shared connection
        # - for file-based DB it opens a new connection (with row_factory=sqlite3.Row)
        return self._repo._conn()

    def _get_name_for_code(self, complex_code: str) -> str:
        try:
            conn = self._get_conn()
            row = conn.execute(
                "SELECT apt_name FROM transactions WHERE complex_code = ? LIMIT 1",
                (complex_code,)
            ).fetchone()
            return row["apt_name"] if row else ""
        except Exception:
            return ""
