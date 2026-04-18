from typing import Dict, Any
from pydantic import BaseModel
from core.logger import get_logger

logger = get_logger(__name__)

class BudgetPlan(BaseModel):
    available_cash: int
    max_price_ltv: int
    max_price_dsr: int
    final_max_price: int
    estimated_loan: int
    estimated_taxes: int
    reasoning: str

class FinancialCalculator:
    def __init__(self):
        from .config import RealEstateConfig
        self.config = RealEstateConfig()
        defaults = self.config.get_financial_defaults()
        
        # Base assumptions from dynamic config
        self.tax_rate_multiplier = defaults.get("tax_rate_multiplier", 0.03)
        self.default_interest_rate = defaults.get("interest_rate", 0.045)
        self.default_loan_term = defaults.get("loan_term_years", 30)

    def _parse_numeric(self, value: Any) -> float:
        """Extracts float from strings like '최대 80%', '40%'"""
        if isinstance(value, (int, float)):
            return float(value)
        if isinstance(value, str):
            import re
            match = re.search(r'(\d+(\.\d+)?)', value)
            if match:
                return float(match.group(1)) / 100.0 if '%' in value else float(match.group(1))
        return 0.0

    def calculate_budget(
        self,
        persona: Dict[str, Any],
        policy: Dict[str, Any],
        mortgage_rate: float = None,
    ) -> BudgetPlan:
        try:
            data = persona.get("user", persona)

            capital = data.get("assets", {}).get("total", 0)
            income = data.get("income", {}).get("total", 0)
            is_first_time = data.get("plans", {}).get("is_first_time_buyer", False)

            ltv_dict = policy.get("ltv", {})
            if is_first_time:
                ltv_str = ltv_dict.get("first_time_buyer", "80%")
            else:
                ltv_str = ltv_dict.get("non_regulated_area", "70%")

            ltv_rate = self._parse_numeric(ltv_str) or 0.7
            if not (0.3 <= ltv_rate <= 0.9):
                logger.warning(f"⚠️ [Calculator] Abnormal LTV rate {ltv_rate:.2f}, falling back to 0.7")
                ltv_rate = 0.7

            dsr_str = policy.get("dsr", {}).get("limit", "40%")
            dsr_rate = self._parse_numeric(dsr_str) or 0.4
            if not (0.3 <= dsr_rate <= 0.6):
                logger.warning(f"⚠️ [Calculator] Abnormal DSR rate {dsr_rate:.4f}, falling back to 0.4")
                dsr_rate = 0.4

            first_time_loan_cap = 600_000_000

            max_p_ltv = int(capital / (1 - ltv_rate + self.tax_rate_multiplier))
            loan_ltv = int(max_p_ltv * ltv_rate)

            if is_first_time and loan_ltv > first_time_loan_cap:
                loan_ltv = first_time_loan_cap
                max_p_ltv = int((capital + loan_ltv) / (1 + self.tax_rate_multiplier))

            interest_rate = mortgage_rate if mortgage_rate is not None else self.default_interest_rate
            years = self.default_loan_term
            annual_payment = income * dsr_rate
            monthly_payment = annual_payment / 12
            monthly_rate = interest_rate / 12
            n_payments = years * 12

            max_loan_dsr = int((monthly_payment * (1 - (1 + monthly_rate)**(-n_payments))) / monthly_rate)
            max_p_dsr = int((capital + max_loan_dsr) / (1 + self.tax_rate_multiplier))

            final_max_price = min(max_p_ltv, max_p_dsr)
            estimated_loan = min(loan_ltv, max_loan_dsr)
            estimated_taxes = int(final_max_price * self.tax_rate_multiplier)

            _억 = 100_000_000
            rate_pct = round(interest_rate * 100, 2)
            reasoning = (
                f"총 자산 {capital/_억:.1f}억원, 연소득 {income/_억:.1f}억원 기준 (주담대금리 {rate_pct}%).\n"
                f"- LTV ({ltv_rate*100:.0f}%) 한도: {max_p_ltv/_억:.2f}억원 (대출 {loan_ltv/_억:.2f}억원)\n"
                f"- DSR ({dsr_rate*100:.0f}%) 한도: {max_p_dsr/_억:.2f}억원 (대출 {max_loan_dsr/_억:.2f}억원)\n"
                f"☞ 최종 보수적 매수 한도: {final_max_price/_억:.2f}억원 (예상 부대비용: {estimated_taxes/_억:.2f}억원)"
            )

            logger.info(f"🧮 [FinancialCalculator] Max Price: {final_max_price:,} KRW (rate={rate_pct}%)")

            return BudgetPlan(
                available_cash=capital - estimated_taxes,
                max_price_ltv=max_p_ltv,
                max_price_dsr=max_p_dsr,
                final_max_price=final_max_price,
                estimated_loan=estimated_loan,
                estimated_taxes=estimated_taxes,
                reasoning=reasoning,
            )

        except Exception as e:
            logger.error(f"❌ [FinancialCalculator] Failed to calculate budget: {e}")
            raise
