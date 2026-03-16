import os
import sys
import pytest

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), "../src"))

from modules.real_estate.calculator import FinancialCalculator

def test_financial_calculator_first_time_buyer():
    calc = FinancialCalculator()
    
    # 3억 자본금, 1.6억 소득
    persona = {
        "assets": {"total": 300_000_000},
        "income": {"total": 160_000_000},
        "plans": {"is_first_time_buyer": True}
    }
    
    # Policy with 80% LTV, 40% DSR
    policy = {
        "ltv": {"first_time_buyer": "80%"},
        "dsr": {"limit": "40%"}
    }
    
    budget = calc.calculate_budget(persona, policy)
    
    # LTV Max: first_time_buyer capped at 6억 loan
    # max_p = (300M + 600M) / 1.03 = ~ 8.73억
    # DSR Max: 1.6억 * 40% = 6400만/년 -> 533만/월 -> 대출 한도 매우 높음 (약 10억 이상)
    # So LTV with 600M cap should be the bottleneck
    
    assert budget.final_max_price > 800_000_000
    assert budget.final_max_price < 900_000_000
    assert budget.estimated_loan <= 600_000_000
    assert "80%" in budget.reasoning

def test_financial_calculator_non_first_time_buyer():
    calc = FinancialCalculator()
    
    persona = {
        "assets": {"total": 300_000_000},
        "income": {"total": 80_000_000},
        "plans": {"is_first_time_buyer": False}
    }
    
    # Policy with 50% LTV (regulated area string test)
    policy = {
        "ltv": {"non_regulated_area": "50%"},
        "dsr": {"limit": "40%"}
    }
    
    budget = calc.calculate_budget(persona, policy)
    
    # LTV Max: 3억/ (1 - 0.5 + 0.03) = 3억 / 0.53 = ~ 5.66억
    # Loan = ~ 2.83억
    
    assert budget.final_max_price > 500_000_000
    assert budget.final_max_price < 600_000_000
    assert "50%" in budget.reasoning
