from typing import Optional, TYPE_CHECKING
from core.logger import get_logger
from .models import YieldResult

if TYPE_CHECKING:
    from modules.real_estate.jeonse.repository import JeonseRepository

logger = get_logger(__name__)

_LTV = 0.70
_LOAN_MONTHS = 360
_MAINTENANCE_FEE = 15  # 만원


class YieldCalculator:
    def __init__(self, jeonse_repo: "JeonseRepository", mortgage_rate: float = 0.0283):
        self._repo = jeonse_repo
        self._rate = mortgage_rate

    def calculate(
        self,
        complex_code: Optional[str],
        apt_name: str,
        district_code: str,
        exclusive_area: float,
        avg_sale_price: int,    # 만원 단위
    ) -> Optional[YieldResult]:
        txs = self._repo.get_recent(
            complex_code=complex_code,
            area=exclusive_area,
            months=6,
            apt_name=apt_name,
            district_code=district_code,
            jeonse_only=True,
        )
        if not txs:
            return None

        avg_deposit = sum(t.deposit for t in txs) // len(txs)
        jeonse_rate = avg_deposit / avg_sale_price if avg_sale_price > 0 else 0.0
        gap_cost = avg_sale_price - avg_deposit
        monthly_cost = self._calc_monthly_cost(avg_sale_price) + _MAINTENANCE_FEE

        return YieldResult(
            jeonse_rate=round(jeonse_rate, 4),
            jeonse_avg=avg_deposit,
            gap_cost=gap_cost,
            monthly_cost=monthly_cost,
            jeonse_sample=len(txs),
        )

    def _calc_monthly_cost(self, sale_price_man: int) -> int:
        """LTV 70% 대출 기준 월 원리금(만원). sale_price_man: 만원 단위."""
        principal = sale_price_man * _LTV
        r = self._rate / 12
        if r == 0:
            return int(principal / _LOAN_MONTHS)
        pmt = principal * r / (1 - (1 + r) ** (-_LOAN_MONTHS))
        return int(pmt)
