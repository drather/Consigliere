# tests/modules/real_estate/daily_report/test_report_formatter_new_blocks.py
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../../../src"))

from modules.real_estate.daily_report.report_formatter import (
    render_price_comparison, render_yield_analysis, render_supply_risk,
)
from modules.real_estate.daily_report.report_types import CompData, YieldData, SupplyData


def test_render_price_comparison_shows_pct():
    comp = CompData(
        district_avg_per_sqm=12000000.0, pct_vs_avg=-7.8,
        similar_units=[{"name": "잠실엘스", "price_per_sqm": 12310000.0}]
    )
    output = render_price_comparison(comp)
    assert "-7.8%" in output
    assert "잠실엘스" in output


def test_render_price_comparison_none_returns_empty():
    assert render_price_comparison(None) == ""


def test_render_yield_analysis_shows_rate():
    yield_r = YieldData(
        jeonse_rate=0.624, jeonse_avg=58000, gap_cost=35000,
        monthly_cost=187, jeonse_sample=3
    )
    output = render_yield_analysis(yield_r)
    assert "62.4%" in output
    assert "3.5억" in output  # gap_cost 35000만원 = 3.5억


def test_render_yield_analysis_none_returns_empty():
    assert render_yield_analysis(None) == ""


def test_render_supply_risk_shows_units():
    supply = SupplyData(
        nearby_units=2340, supply_period="2026H2",
        news_catalysts=[{"type": "positive", "title": "GTX-A 개통", "date": "2026-05-10"}]
    )
    output = render_supply_risk(supply)
    assert "2,340" in output
    assert "GTX-A" in output


def test_render_supply_risk_no_units():
    supply = SupplyData(nearby_units=0, supply_period="", news_catalysts=[])
    output = render_supply_risk(supply)
    assert "공급 없음" in output or output == "" or "0" in output
