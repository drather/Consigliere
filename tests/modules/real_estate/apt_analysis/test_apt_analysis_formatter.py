import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../../../src"))

from modules.real_estate.apt_analysis.models import AptAnalysisReport
from modules.real_estate.apt_analysis.formatter import format_slack, format_markdown


def _make_report() -> AptAnalysisReport:
    return AptAnalysisReport(
        complex_code="CC001",
        apt_name="래미안블레스티지",
        generated_at="2026-05-30T12:00:00",
        price_history=[{"date": "2026-05-01", "price": 1_500_000_000, "area": 84.0}],
        jeonse_ratio=60.5,
        supply_risk_summary="반경 3km 공급 3,500세대 — 위험",
        location_score={"residential_total": 72, "investment_total": 68, "results": {}},
        commute_summary={"transit": 32, "car": 25},
        macro_snapshot={"base_rate": {"value": 3.0}},
        llm_insight="이 단지는 강남 핵심 입지입니다.",
        slack_text="",
        markdown_text="",
    )


class TestFormatSlack:
    def test_slack_text_contains_apt_name(self):
        report = _make_report()
        text = format_slack(report)
        assert "래미안블레스티지" in text

    def test_slack_text_contains_jeonse_ratio(self):
        report = _make_report()
        text = format_slack(report)
        assert "60.5" in text

    def test_slack_text_contains_location_scores(self):
        report = _make_report()
        text = format_slack(report)
        assert "72" in text  # residential_total
        assert "68" in text  # investment_total

    def test_slack_text_contains_llm_insight(self):
        report = _make_report()
        text = format_slack(report)
        assert "강남 핵심 입지" in text

    def test_slack_text_handles_none_jeonse_ratio(self):
        report = _make_report()
        report.jeonse_ratio = None
        text = format_slack(report)
        assert "래미안블레스티지" in text
        assert "전세가율" not in text  # must be omitted when None


class TestFormatMarkdown:
    def test_markdown_contains_header(self):
        report = _make_report()
        text = format_markdown(report)
        assert "# 래미안블레스티지" in text

    def test_markdown_contains_price_history(self):
        report = _make_report()
        text = format_markdown(report)
        assert "실거래가" in text

    def test_markdown_contains_llm_insight(self):
        report = _make_report()
        text = format_markdown(report)
        assert "강남 핵심 입지" in text
