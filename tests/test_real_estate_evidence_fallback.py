"""입지점수 카드 "근거 보기" — evidence가 빈 리스트일 때 fallback 표시 검증.

배경: POI 캐시가 없던 시점에 location_score가 계산된 단지는 일부 dimension의
evidence가 영구히 []로 저장되어, "근거 보기"를 펼쳐도 아무것도 보이지 않는 문제.
(docs/features/apt-detail-card-evidence-fallback/spec.md)
"""
from streamlit.testing.v1 import AppTest


def _render_grid_with_empty_evidence():
    from dashboard.views.real_estate import _render_score_dimension_grid
    from modules.real_estate.location.dimension_result import DimensionResult

    results = [
        DimensionResult(id="medical", label="🏥 의료", score=100, evidence=[]),
        DimensionResult(id="nature", label="🌳 자연환경", score=50, evidence=["최근접 공원: 120m"]),
    ]
    _render_score_dimension_grid(results)


def test_empty_evidence_shows_fallback_caption():
    at = AppTest.from_function(_render_grid_with_empty_evidence).run()

    captions = [c.value for c in at.caption]
    assert any("데이터 없음" in c for c in captions), captions


def test_non_empty_evidence_still_renders_normally():
    at = AppTest.from_function(_render_grid_with_empty_evidence).run()

    captions = [c.value for c in at.caption]
    assert any("최근접 공원: 120m" in c for c in captions), captions
