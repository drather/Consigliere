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

    loc_repo = MagicMock()
    loc_repo.get_score.return_value = None

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
        loc_repo=loc_repo,
        macro_svc=macro_svc,
        commute_repo=commute_repo,
        llm=llm,
    )
    return orch, apt_master_repo, apt_details_repo, tx_repo, jeonse_repo, loc_repo, macro_svc, commute_repo, llm


class TestAptAnalysisOrchestrator:
    def test_analyze_returns_report_with_correct_complex_code(self):
        orch, *_ = _build_orchestrator()
        report = orch.analyze("CC001")
        assert isinstance(report, AptAnalysisReport)
        assert report.complex_code == "CC001"
        assert report.apt_name == "래미안블레스티지"

    def test_analyze_calls_all_repositories(self):
        orch, apt_master_repo, apt_details_repo, tx_repo, jeonse_repo, loc_repo, macro_svc, commute_repo, llm = _build_orchestrator()
        orch.analyze("CC001")
        apt_master_repo.get_by_complex_code.assert_called_once_with("CC001")
        tx_repo.get_by_complex.assert_called_once_with("CC001")
        jeonse_repo.get_by_complex.assert_called_once_with("CC001")
        loc_repo.get_score.assert_called_once_with("CC001")
        macro_svc.fetch_latest_macro_data.assert_called_once()
        commute_repo.get_all_by_origin.assert_called_once()

    def test_analyze_calculates_jeonse_ratio(self):
        orch, *_ = _build_orchestrator()
        report = orch.analyze("CC001")
        # jeonse_deposit=900M, avg_sale=1500M → ratio=60.0%
        assert report.jeonse_ratio is not None
        assert abs(report.jeonse_ratio - 60.0) < 0.1

    def test_analyze_includes_llm_insight(self):
        orch, *_ = _build_orchestrator()
        report = orch.analyze("CC001")
        assert "강남" in report.llm_insight

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
