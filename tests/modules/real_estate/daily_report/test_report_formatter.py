import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../../../src"))

from modules.real_estate.daily_report.report_formatter import (
    format_macro_summary,
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


class TestBuildCandidateCard:
    def _make_candidate(self) -> dict:
        from modules.real_estate.location.dimension_result import DimensionResult
        from modules.real_estate.location.location_scorer import LocationScore
        return {
            "apt_name": "래미안",
            "sigungu": "강남구",
            "exclusive_area": 84.0,
            "household_count": 1200,
            "composite_score": 0.85,
            "avg_recent_price": 280_000_000,
            "price_change_pct": 2.5,
            "_recent_tx_points": [
                {"price_eok": 2.7, "deal_date": "2026-05-07"},
                {"price_eok": 2.8, "deal_date": "2026-05-10"},
            ],
            "commute_transit_minutes": 35,
            "commute_car_minutes": 20,
            "commute_walk_minutes": None,
            "_commute_route_summary": "2호선 30분",
            "_location_score": LocationScore(
                complex_code="CC001",
                residential_total=75,
                residential_results=[
                    DimensionResult(id="transportation", label="🚇 교통", score=80,
                                    evidence=["대중교통 22분"]),
                ],
                investment_total=65,
                investment_results=[
                    DimensionResult(id="commercial", label="🛍️ 상업", score=60,
                                    evidence=["음식점 15개"]),
                ],
                scored_at="2026-05-10T00:00:00+00:00",
            ),
            "_verdict": "매수 검토 — 역세권 우수",
            "_key_points": ["✅ 역세권", "📈 상승 추세"],
        }

    def test_build_candidate_card_contains_name(self):
        from modules.real_estate.daily_report.report_formatter import build_candidate_card
        result = build_candidate_card(self._make_candidate())
        assert "래미안" in result

    def test_build_candidate_card_contains_svg(self):
        from modules.real_estate.daily_report.report_formatter import build_candidate_card
        result = build_candidate_card(self._make_candidate())
        assert "<svg" in result

    def test_build_candidate_card_contains_commute(self):
        from modules.real_estate.daily_report.report_formatter import build_candidate_card
        result = build_candidate_card(self._make_candidate())
        assert "35분" in result  # transit
        assert "20분" in result  # car
        assert "조회 불가" in result  # walk is None

    def test_build_candidate_card_contains_verdict(self):
        from modules.real_estate.daily_report.report_formatter import build_candidate_card
        result = build_candidate_card(self._make_candidate())
        assert "매수 검토" in result

    def test_build_candidate_card_contains_keypoints(self):
        from modules.real_estate.daily_report.report_formatter import build_candidate_card
        result = build_candidate_card(self._make_candidate())
        assert "✅ 역세권" in result

    def test_build_candidate_card_no_stats_tag(self):
        from modules.real_estate.daily_report.report_formatter import build_candidate_card
        result = build_candidate_card(self._make_candidate())
        assert "<!-- stats -->" not in result


class TestBuildMarkdown:
    def test_build_markdown_structure(self):
        from modules.real_estate.daily_report.report_formatter import build_markdown
        candidates = [{
            "apt_name": "래미안", "sigungu": "강남구",
            "exclusive_area": 84.0, "household_count": 1200,
            "composite_score": 0.85, "avg_recent_price": 280_000_000,
            "price_change_pct": 2.5, "_recent_tx_points": [],
            "commute_transit_minutes": None, "commute_car_minutes": None,
            "commute_walk_minutes": None, "_commute_route_summary": "",
            "_location_score": None, "_verdict": "관망", "_key_points": [],
        }]
        md = build_markdown(
            date_str="2026-05-10",
            date_range="2026-05-07 ~ 2026-05-10",
            macro_summary="기준금리: 3.5%",
            market_summary="강남권 거래 활발",
            candidates=candidates,
            insights_map={},
        )
        assert "데일리 부동산 브리핑" in md
        assert "래미안" in md
        assert "<!-- stats -->" not in md


class TestBuildSlack:
    def _make_candidate(self, transit=35, car=20):
        return {
            "apt_name": "래미안", "sigungu": "강남구",
            "composite_score": 0.85,
            "_recent_tx_points": [
                {"price_eok": 8.5, "deal_date": "2026-05-07"},
                {"price_eok": 8.8, "deal_date": "2026-05-10"},
            ],
            "avg_recent_price": 880_000_000,
            "price_change_pct": 3.5,
            "exclusive_area": 84.0,
            "commute_transit_minutes": transit,
            "commute_car_minutes": car,
            "commute_walk_minutes": None,
            "_commute_route_summary": "",
            "_verdict": "매수 검토",
            "_key_points": ["✅ 역세권"],
            "_location_score": None,
        }

    def test_build_slack_contains_apt_name(self):
        from modules.real_estate.daily_report.report_formatter import build_slack
        result = build_slack([self._make_candidate()])
        assert "래미안" in result

    def test_build_slack_no_svg(self):
        from modules.real_estate.daily_report.report_formatter import build_slack
        result = build_slack([self._make_candidate()])
        assert "<svg" not in result

    def test_build_slack_has_text_sparkline(self):
        from modules.real_estate.daily_report.report_formatter import build_slack
        result = build_slack([self._make_candidate()])
        spark_chars = set("▁▂▃▄▅▆▇█")
        assert any(ch in result for ch in spark_chars)

    def test_build_slack_transit_shown(self):
        from modules.real_estate.daily_report.report_formatter import build_slack
        result = build_slack([self._make_candidate(transit=35)])
        assert "35분" in result

    def test_build_slack_none_transit_shows_unavailable(self):
        from modules.real_estate.daily_report.report_formatter import build_slack
        result = build_slack([self._make_candidate(transit=None)])
        assert "조회불가" in result or "조회 불가" in result

    def test_build_slack_multiple_candidates_separated(self):
        from modules.real_estate.daily_report.report_formatter import build_slack
        c1 = self._make_candidate()
        c2 = {**self._make_candidate(), "apt_name": "힐스테이트"}
        result = build_slack([c1, c2])
        assert "래미안" in result
        assert "힐스테이트" in result
