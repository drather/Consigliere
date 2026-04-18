import pytest
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../../src"))

from modules.real_estate.calculator import FinancialCalculator

PERSONA = {
    "user": {
        "assets": {"total": 300_000_000},
        "income": {"total": 160_000_000},
        "plans": {"is_first_time_buyer": True},
    }
}
POLICY = {"ltv": {"first_time_buyer": "80%"}, "dsr": {"limit": "40%"}}


def test_calculate_budget_accepts_mortgage_rate():
    calc = FinancialCalculator()
    plan_high = calc.calculate_budget(PERSONA, POLICY, mortgage_rate=0.06)
    plan_low  = calc.calculate_budget(PERSONA, POLICY, mortgage_rate=0.03)
    assert plan_low.max_price_dsr > plan_high.max_price_dsr


def test_calculate_budget_default_rate_unchanged():
    calc = FinancialCalculator()
    plan_default = calc.calculate_budget(PERSONA, POLICY)
    plan_explicit = calc.calculate_budget(PERSONA, POLICY, mortgage_rate=calc.default_interest_rate)
    assert plan_default.final_max_price == plan_explicit.final_max_price


def test_calculate_budget_reasoning_includes_rate():
    calc = FinancialCalculator()
    plan = calc.calculate_budget(PERSONA, POLICY, mortgage_rate=0.042)
    assert "4.2%" in plan.reasoning
