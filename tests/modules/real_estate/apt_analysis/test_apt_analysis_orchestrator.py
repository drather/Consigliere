import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../../../src"))

import pytest
from unittest.mock import MagicMock
from modules.real_estate.apt_analysis.models import AptAnalysisReport


def _make_mock_apt_master():
    m = MagicMock()
    m.apt_name = "래미안블레스티지"
    m.district_code = "11680"
    m.complex_code = "CC001"
    m.sigungu = "강남구"
    m.road_address = "서울특별시 강남구 도곡로 155"
    return m


def _make_mock_apt_details():
    m = MagicMock()
    m.apt_name = "래미안블레스티지"
    m.district_code = "11680"
    m.sigungu = "강남구"
    m.road_address = "서울특별시 강남구 도곡로 155"
    return m


def _make_mock_transaction():
    m = MagicMock()
    m.deal_date = "2026-05-01"
    m.price = 1_500_000_000
    m.exclusive_area = 84.0
    return m


def _make_mock_jeonse():
    m = MagicMock()
    m.deposit = 900_000_000
    m.contract_type = "jeonse"
    return m


def _build_orchestrator():
    from modules.real_estate.apt_analysis.orchestrator import AptAnalysisOrchestrator

    apt_master_repo = MagicMock()
    apt_master_repo.get_by_complex_code.return_value = _make_mock_apt_master()

    apt_details_repo = MagicMock()
    apt_details_repo.get.return_value = _make_mock_apt_details()

    tx_repo = MagicMock()
    tx_repo.get_by_complex.return_value = [_make_mock_transaction()]

    jeonse_repo = MagicMock()
    jeonse_repo.get_by_complex.return_value = [_make_mock_jeonse()]

    supply_repo = MagicMock()
    supply_repo.get_within_radius.return_value = []

    location_service = MagicMock()
    location_service.get_score.return_value = None
    location_service.get_poi_cached.return_value = None

    macro_svc = MagicMock()
    macro_svc.fetch_latest_macro_data.return_value = {"base_rate": {"value": 3.0}, "updated_at": "2026-05-30"}

    commute_repo = MagicMock()
    commute_repo.get_all_by_origin.return_value = []

    llm = MagicMock()
    llm.generate.return_value = "이 단지는 강남 핵심 입지로 실거주·투자 모두 우수합니다."

    orch = AptAnalysisOrchestrator(
        apt_master_repo=apt_master_repo,
        apt_details_repo=apt_details_repo,
        tx_repo=tx_repo,
        jeonse_repo=jeonse_repo,
        supply_repo=supply_repo,
        location_service=location_service,
        macro_svc=macro_svc,
        commute_repo=commute_repo,
        llm=llm,
    )
    return orch, apt_master_repo, apt_details_repo, tx_repo, jeonse_repo, location_service, macro_svc, commute_repo, llm


class TestAptAnalysisOrchestrator:
    def test_analyze_returns_report_with_correct_complex_code(self):
        orch, *_ = _build_orchestrator()
        report = orch.analyze("CC001")
        assert isinstance(report, AptAnalysisReport)
        assert report.complex_code == "CC001"
        assert report.apt_name == "래미안블레스티지"

    def test_analyze_calls_all_repositories(self):
        orch, apt_master_repo, apt_details_repo, tx_repo, jeonse_repo, location_service, macro_svc, commute_repo, llm = _build_orchestrator()
        orch.analyze("CC001")
        apt_master_repo.get_by_complex_code.assert_called_once_with("CC001")
        tx_repo.get_by_complex.assert_called_once_with("CC001")
        jeonse_repo.get_by_complex.assert_called_once_with("CC001")
        location_service.get_score.assert_called_once_with("CC001")
        macro_svc.fetch_latest_macro_data.assert_called_once()
        commute_repo.get_all_by_origin.assert_called_once_with("11680__래미안블레스티지")

    def test_analyze_calculates_jeonse_ratio(self):
        orch, *_ = _build_orchestrator()
        report = orch.analyze("CC001")
        # jeonse_deposit=900M, avg_sale=1500M → ratio=60.0%
        assert report.jeonse_ratio is not None
        assert abs(report.jeonse_ratio - 60.0) < 0.1

    def test_analyze_includes_llm_insight(self):
        orch, *_, llm = _build_orchestrator()
        report = orch.analyze("CC001")
        assert "강남" in report.llm_insight
        llm.generate.assert_called_once()

    def test_analyze_raises_value_error_when_complex_not_found(self):
        orch, apt_master_repo, *_ = _build_orchestrator()
        apt_master_repo.get_by_complex_code.return_value = None
        with pytest.raises(ValueError, match="단지 코드 없음"):
            orch.analyze("NONEXISTENT")

    def test_analyze_handles_missing_jeonse_gracefully(self):
        orch, _, _, _, jeonse_repo, *_ = _build_orchestrator()
        jeonse_repo.get_by_complex.return_value = []
        report = orch.analyze("CC001")
        assert report.jeonse_ratio is None

    def test_analyze_builds_commute_summary_from_cache(self):
        orch, _, _, _, _, _, _, commute_repo, _ = _build_orchestrator()
        mock_result = MagicMock()
        mock_result.mode = "transit"
        mock_result.duration_minutes = 32
        commute_repo.get_all_by_origin.return_value = [mock_result]
        report = orch.analyze("CC001")
        assert report.commute_summary is not None
        assert report.commute_summary.get("transit") == 32


def _make_fake_location_score(complex_code="CC001"):
    from modules.real_estate.location.location_scorer import LocationScore
    from modules.real_estate.location.dimension_result import DimensionResult

    return LocationScore(
        complex_code=complex_code,
        residential_total=78,
        residential_results=[DimensionResult(id="transportation", label="교통 접근성", score=80, evidence=[])],
        investment_total=66,
        investment_results=[DimensionResult(id="liquidity", label="거래 유동성", score=70, evidence=[])],
        scored_at="2026-06-08T00:00:00+00:00",
    )


class TestAptAnalysisOrchestratorLocationScoring:
    """enrich_and_save()를 리포트 생성 플로우에 연결 — 점수 미존재 시 계산·저장."""

    def test_computes_and_saves_score_when_missing(self):
        orch, *_, location_service, _, commute_repo, _ = _build_orchestrator()
        location_service.get_score.return_value = None
        location_service.enrich_and_save.return_value = _make_fake_location_score()

        report = orch.analyze("CC001")

        location_service.enrich_and_save.assert_called_once()
        called_code, called_candidate = location_service.enrich_and_save.call_args.args
        assert called_code == "CC001"
        assert called_candidate["complex_code"] == "CC001"
        assert report.location_score["residential_total"] == 78
        assert report.location_score["investment_total"] == 66

    def test_skips_enrich_when_score_already_exists(self):
        orch, *_, location_service, _, commute_repo, _ = _build_orchestrator()
        location_service.get_score.return_value = _make_fake_location_score()

        report = orch.analyze("CC001")

        location_service.enrich_and_save.assert_not_called()
        assert report.location_score["residential_total"] == 78

    def test_candidate_includes_poi_and_commute_fields(self):
        orch, *_, location_service, _, commute_repo, _ = _build_orchestrator()
        location_service.get_score.return_value = None
        location_service.enrich_and_save.return_value = _make_fake_location_score()

        mock_poi = MagicMock()
        mock_poi.subway_stations = [{"name": "강남역", "walk_minutes": 4}]
        mock_poi.schools_count = 3
        mock_poi.academies_count = 5
        mock_poi.marts_count = 1
        mock_poi.convenience_count = 4
        mock_poi.pharmacy_count = 2
        mock_poi.medical_count = 6
        mock_poi.park_nearest_m = 250
        mock_poi.restaurant_count = 40
        mock_poi.cafe_count = 12
        location_service.get_poi_cached.return_value = mock_poi

        mock_commute = MagicMock()
        mock_commute.mode = "transit"
        mock_commute.duration_minutes = 28
        commute_repo.get_all_by_origin.return_value = [mock_commute]

        orch.analyze("CC001")

        _, candidate = location_service.enrich_and_save.call_args.args
        assert candidate["poi_stations"] == [{"name": "강남역", "walk_minutes": 4}]
        assert candidate["poi_convenience_count"] == 4
        assert candidate["poi_park_nearest_m"] == 250
        assert candidate["commute_transit_minutes"] == 28

    def test_score_computation_failure_does_not_break_report(self):
        orch, *_, location_service, _, commute_repo, llm = _build_orchestrator()
        location_service.get_score.return_value = None
        location_service.enrich_and_save.side_effect = Exception("scoring 실패")

        report = orch.analyze("CC001")

        assert report.location_score is None
        llm.generate.assert_called_once()
