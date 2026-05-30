import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient

from main import app

client = TestClient(app)


def _make_mock_report():
    from modules.real_estate.apt_analysis.models import AptAnalysisReport
    return AptAnalysisReport(
        complex_code="CC001",
        apt_name="래미안블레스티지",
        generated_at="2026-05-30T12:00:00",
        price_history=[{"date": "2026-05-01", "price": 1_500_000_000, "area": 84.0}],
        jeonse_ratio=60.5,
        supply_risk_summary="반경 3km — 안전",
        location_score={"residential_total": 72, "investment_total": 68, "results": {}},
        commute_summary={"transit": 32},
        macro_snapshot={"base_rate": {"value": 3.0}},
        llm_insight="강남 핵심 입지 추천.",
        slack_text="*래미안블레스티지* 분석 완료",
        markdown_text="# 래미안블레스티지",
    )


class TestAptAnalyzeEndpoint:
    def test_analyze_returns_200_with_report(self):
        mock_report = _make_mock_report()
        with patch("api.routers.real_estate._build_apt_analysis_orchestrator") as mock_build, \
             patch("api.routers.real_estate._get_apt_analysis_repo") as mock_repo_fn, \
             patch("api.routers.real_estate._send_slack_if_needed"):
            mock_orch = MagicMock()
            mock_orch.analyze.return_value = mock_report
            mock_build.return_value = mock_orch
            mock_repo = MagicMock()
            mock_repo_fn.return_value = mock_repo

            resp = client.post("/jobs/apt/analyze", json={"complex_code": "CC001", "send_slack": False})

        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "success"
        assert data["report"]["complex_code"] == "CC001"

    def test_analyze_returns_404_when_complex_not_found(self):
        with patch("api.routers.real_estate._build_apt_analysis_orchestrator") as mock_build, \
             patch("api.routers.real_estate._get_apt_analysis_repo"):
            mock_orch = MagicMock()
            mock_orch.analyze.side_effect = ValueError("단지 코드 없음: NOTFOUND")
            mock_build.return_value = mock_orch

            resp = client.post("/jobs/apt/analyze", json={"complex_code": "NOTFOUND"})

        assert resp.status_code == 404

    def test_analyze_saves_to_repository(self):
        mock_report = _make_mock_report()
        with patch("api.routers.real_estate._build_apt_analysis_orchestrator") as mock_build, \
             patch("api.routers.real_estate._get_apt_analysis_repo") as mock_repo_fn, \
             patch("api.routers.real_estate._send_slack_if_needed"):
            mock_orch = MagicMock()
            mock_orch.analyze.return_value = mock_report
            mock_build.return_value = mock_orch
            mock_repo = MagicMock()
            mock_repo_fn.return_value = mock_repo

            client.post("/jobs/apt/analyze", json={"complex_code": "CC001", "send_slack": False})
            mock_repo.save.assert_called_once_with(mock_report)


class TestAptAnalysisGetEndpoints:
    def test_get_latest_returns_200_with_report(self):
        mock_report = _make_mock_report()
        with patch("api.routers.real_estate._get_apt_analysis_repo") as mock_repo_fn:
            mock_repo = MagicMock()
            mock_repo.get_latest.return_value = mock_report
            mock_repo_fn.return_value = mock_repo

            resp = client.get("/dashboard/apt/analysis/CC001/latest")

        assert resp.status_code == 200
        assert resp.json()["complex_code"] == "CC001"

    def test_get_latest_returns_404_when_no_report(self):
        with patch("api.routers.real_estate._get_apt_analysis_repo") as mock_repo_fn:
            mock_repo = MagicMock()
            mock_repo.get_latest.return_value = None
            mock_repo_fn.return_value = mock_repo

            resp = client.get("/dashboard/apt/analysis/NOTFOUND/latest")

        assert resp.status_code == 404

    def test_get_history_returns_list(self):
        mock_report = _make_mock_report()
        with patch("api.routers.real_estate._get_apt_analysis_repo") as mock_repo_fn:
            mock_repo = MagicMock()
            mock_repo.get_history.return_value = [mock_report]
            mock_repo_fn.return_value = mock_repo

            resp = client.get("/dashboard/apt/analysis/CC001")

        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        assert len(data) == 1
