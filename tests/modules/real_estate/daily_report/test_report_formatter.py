import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../../../src"))

from modules.real_estate.daily_report.report_formatter import (
    format_macro_summary,
    format_stat_block,
    format_dimension_scores,
    build_markdown,
)
from modules.real_estate.location.dimension_result import DimensionResult
from modules.real_estate.location.location_scorer import LocationScore
from modules.real_estate.daily_report.report_types import TrendData, CommuteData


def _make_location_score(r_results=None, i_results=None):
    return LocationScore(
        complex_code="CC001",
        residential_total=75,
        residential_results=r_results or [
            DimensionResult(id="transportation", label="🚇 교통", score=80,
                            evidence=["대중교통 22분", "경로: 2호선 18분 → 도보 4분"]),
            DimensionResult(id="education", label="🏫 교육환경", score=70, evidence=["초중학교: 3개"]),
        ],
        investment_total=65,
        investment_results=i_results or [
            DimensionResult(id="commercial", label="🛍️ 상업활성도", score=60,
                            evidence=["음식점: 15개, 카페: 8개", "업종 다양성: 4/6 카테고리"]),
        ],
        scored_at="2026-05-10T00:00:00+00:00",
    )


# ── format_macro_summary ────────────────────────────────────────
def test_format_macro_summary_splits_pipes():
    result = format_macro_summary("기준금리: 3.5%|주담대: 4.2%|M2: 증가")
    assert len(result) == 3
    assert result[0] == "- 기준금리: 3.5%"

def test_format_macro_summary_empty():
    result = format_macro_summary("")
    assert result == ["데이터 없음"]


# ── format_stat_block ───────────────────────────────────────────
def test_format_stat_block_basic():
    c = {
        "recent_tx_count": 3, "sigungu": "강남구",
        "exclusive_area": 84.0, "household_count": 1200,
    }
    lines = format_stat_block(c, price_eok=28.0, change=2.5, trend=None, trend_area=84)
    joined = "\n".join(lines)
    assert "28.0억" in joined
    assert "▲" in joined
    assert "강남구" in joined

def test_format_stat_block_negative_change():
    c = {"recent_tx_count": 2, "sigungu": "서초구", "exclusive_area": 59.0, "household_count": 500}
    lines = format_stat_block(c, price_eok=20.0, change=-1.5, trend=None, trend_area=59)
    joined = "\n".join(lines)
    assert "▼" in joined


# ── format_dimension_scores ─────────────────────────────────────
def test_format_dimension_scores_renders_all_dims():
    c = {"_location_score": _make_location_score()}
    lines = format_dimension_scores(c)
    joined = "\n".join(lines)
    assert "🚇 교통" in joined
    assert "80점" in joined
    assert "대중교통 22분" in joined
    assert "🏫 교육환경" in joined
    assert "🛍️ 상업활성도" in joined
    assert "업종 다양성: 4/6 카테고리" in joined

def test_format_dimension_scores_empty_when_no_score():
    assert format_dimension_scores({}) == []

def test_format_dimension_scores_evidence_indented():
    c = {"_location_score": _make_location_score()}
    lines = format_dimension_scores(c)
    evidence_lines = [l for l in lines if l.startswith("  - ")]
    assert len(evidence_lines) >= 3

def test_format_dimension_scores_no_hardcoded_dimension_ids():
    """포매터가 차원 ID를 전혀 모른다 — 미지의 차원도 렌더링된다."""
    c = {"_location_score": LocationScore(
        complex_code="T001",
        residential_total=50,
        residential_results=[
            DimensionResult(id="mystery_dim", label="🔮 미지의차원", score=99,
                            evidence=["비밀 근거 데이터"]),
        ],
        investment_total=50,
        investment_results=[],
        scored_at="2026-05-10T00:00:00+00:00",
    )}
    lines = format_dimension_scores(c)
    joined = "\n".join(lines)
    assert "🔮 미지의차원" in joined
    assert "99점" in joined
    assert "비밀 근거 데이터" in joined


# ── build_markdown ──────────────────────────────────────────────
def test_build_markdown_contains_sections():
    candidates = [{
        "apt_name": "래미안", "sigungu": "강남구",
        "recent_tx_count": 3, "avg_recent_price": 280_000_000,
        "price_change_pct": 2.5, "exclusive_area": 84.0,
        "household_count": 1200, "composite_score": 0.8,
        "_location_score": _make_location_score(),
    }]
    insights_map = {
        "래미안": {
            "trading_bullets": ["3건 거래"],
            "characteristics_bullets": ["1200세대"],
            "strategy_bullets": ["매수 적기"],
        }
    }
    md = build_markdown(
        date_str="2026-05-10",
        date_range="2026-05-07 ~ 2026-05-10",
        macro_summary="기준금리: 3.5%",
        market_summary="강남권 거래 활발",
        candidates=candidates,
        insights_map=insights_map,
    )
    assert "데일리 부동산 브리핑" in md
    assert "래미안" in md
    assert "🚇 교통" in md
    assert "거래 동향" in md
    assert "전략 제안" in md


class TestRenderTrend:
    def _make_trend(self, prices_eok, dates=None) -> TrendData:
        n = len(prices_eok)
        if dates is None:
            dates = [f"2026-05-{i+1:02d}" for i in range(n)]
        return TrendData(
            points=[{"price_eok": p, "deal_date": d} for p, d in zip(prices_eok, dates)],
            avg_eok=sum(prices_eok) / n,
            change_pct=-5.0,
            area_sqm=84.0,
        )

    def test_render_trend_returns_svg(self):
        from modules.real_estate.daily_report.report_formatter import render_trend
        trend = self._make_trend([8.5, 8.8, 8.3])
        result = render_trend(trend)
        assert "<svg" in result

    def test_render_trend_falling_uses_red(self):
        from modules.real_estate.daily_report.report_formatter import render_trend
        trend = self._make_trend([9.5, 9.0, 8.8])  # 하락
        result = render_trend(trend)
        assert "#f38ba8" in result

    def test_render_trend_rising_uses_green(self):
        from modules.real_estate.daily_report.report_formatter import render_trend
        trend = self._make_trend([8.0, 8.5, 9.0])  # 상승
        result = render_trend(trend)
        assert "#a6e3a1" in result

    def test_render_trend_last_point_has_star(self):
        from modules.real_estate.daily_report.report_formatter import render_trend
        trend = self._make_trend([8.5, 8.8])
        result = render_trend(trend)
        assert "★" in result

    def test_render_trend_empty_points_fallback(self):
        from modules.real_estate.daily_report.report_formatter import render_trend
        trend = TrendData(points=[], avg_eok=0.0, change_pct=0.0, area_sqm=84.0)
        result = render_trend(trend)
        assert "<svg" not in result
        assert "데이터 없음" in result

    def test_render_trend_single_point(self):
        from modules.real_estate.daily_report.report_formatter import render_trend
        trend = self._make_trend([8.8])
        result = render_trend(trend)
        assert "<svg" in result
        assert "★" in result


class TestRenderCommute:
    def _make_commute(self, transit=None, car=None, walk=None, route=""):
        from modules.real_estate.daily_report.report_types import CommuteData
        return CommuteData(
            transit_minutes=transit, car_minutes=car,
            walk_minutes=walk, route_summary=route,
        )

    def test_all_modes_present(self):
        from modules.real_estate.daily_report.report_formatter import render_commute
        result = render_commute(self._make_commute(transit=35, car=20, walk=90))
        assert "35분" in result
        assert "20분" in result
        assert "90분" in result

    def test_none_mode_shows_unavailable(self):
        from modules.real_estate.daily_report.report_formatter import render_commute
        result = render_commute(self._make_commute(transit=35, car=None, walk=None))
        assert "35분" in result
        assert result.count("조회 불가") == 2

    def test_all_none_shows_three_unavailable(self):
        from modules.real_estate.daily_report.report_formatter import render_commute
        result = render_commute(self._make_commute())
        assert result.count("조회 불가") == 3

    def test_route_summary_shown_when_present(self):
        from modules.real_estate.daily_report.report_formatter import render_commute
        result = render_commute(self._make_commute(transit=35, route="2호선 30분"))
        assert "2호선 30분" in result


class TestRenderScores:
    def test_renders_residential_and_investment(self):
        from modules.real_estate.daily_report.report_formatter import render_scores
        from modules.real_estate.location.dimension_result import DimensionResult
        res = [DimensionResult(id="transportation", label="🚇 교통", score=80, evidence=["22분"])]
        inv = [DimensionResult(id="commercial", label="🛍️ 상업", score=60, evidence=["음식점 15개"])]
        result = render_scores(res, inv)
        assert "🚇 교통" in result
        assert "80점" in result
        assert "🛍️ 상업" in result
        assert "음식점 15개" in result

    def test_empty_lists_returns_empty(self):
        from modules.real_estate.daily_report.report_formatter import render_scores
        assert render_scores([], []) == ""

    def test_unknown_dimension_id_still_renders(self):
        from modules.real_estate.daily_report.report_formatter import render_scores
        from modules.real_estate.location.dimension_result import DimensionResult
        res = [DimensionResult(id="mystery", label="🔮 미지의차원", score=99, evidence=["비밀"])]
        result = render_scores(res, [])
        assert "🔮 미지의차원" in result
        assert "99점" in result


class TestRenderVerdictKeypoints:
    def test_render_verdict_with_text(self):
        from modules.real_estate.daily_report.report_formatter import render_verdict
        result = render_verdict("관망 — 하락 추세 중")
        assert "관망" in result
        assert "🔍" in result

    def test_render_verdict_empty_returns_empty(self):
        from modules.real_estate.daily_report.report_formatter import render_verdict
        assert render_verdict("") == ""

    def test_render_keypoints_with_items(self):
        from modules.real_estate.daily_report.report_formatter import render_keypoints
        result = render_keypoints(["✅ 역세권", "📉 하락 추세"])
        assert "✅ 역세권" in result
        assert "📉 하락 추세" in result

    def test_render_keypoints_empty_returns_empty(self):
        from modules.real_estate.daily_report.report_formatter import render_keypoints
        assert render_keypoints([]) == ""
