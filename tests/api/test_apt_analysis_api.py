import dataclasses
import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient

from main import app
from api.dependencies import get_apt_analysis_repo, get_apt_orchestrator

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
        mock_orch = MagicMock()
        mock_orch.analyze.return_value = mock_report
        mock_repo = MagicMock()

        app.dependency_overrides[get_apt_orchestrator] = lambda: mock_orch
        app.dependency_overrides[get_apt_analysis_repo] = lambda: mock_repo
        try:
            with patch("api.routers.real_estate._send_slack_if_needed"):
                resp = client.post("/jobs/apt/analyze", json={"complex_code": "CC001", "send_slack": False})
        finally:
            app.dependency_overrides.pop(get_apt_orchestrator, None)
            app.dependency_overrides.pop(get_apt_analysis_repo, None)

        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "success"
        assert data["report"]["complex_code"] == "CC001"

    def test_analyze_returns_404_when_complex_not_found(self):
        mock_orch = MagicMock()
        mock_orch.analyze.side_effect = ValueError("단지 코드 없음: NOTFOUND")
        mock_repo = MagicMock()

        app.dependency_overrides[get_apt_orchestrator] = lambda: mock_orch
        app.dependency_overrides[get_apt_analysis_repo] = lambda: mock_repo
        try:
            resp = client.post("/jobs/apt/analyze", json={"complex_code": "NOTFOUND"})
        finally:
            app.dependency_overrides.pop(get_apt_orchestrator, None)
            app.dependency_overrides.pop(get_apt_analysis_repo, None)

        assert resp.status_code == 404

    def test_analyze_saves_to_repository(self):
        mock_report = _make_mock_report()
        mock_orch = MagicMock()
        mock_orch.analyze.return_value = mock_report
        mock_repo = MagicMock()

        app.dependency_overrides[get_apt_orchestrator] = lambda: mock_orch
        app.dependency_overrides[get_apt_analysis_repo] = lambda: mock_repo
        try:
            with patch("api.routers.real_estate._send_slack_if_needed"):
                client.post("/jobs/apt/analyze", json={"complex_code": "CC001", "send_slack": False})
        finally:
            app.dependency_overrides.pop(get_apt_orchestrator, None)
            app.dependency_overrides.pop(get_apt_analysis_repo, None)

        mock_repo.save.assert_called_once_with(mock_report)


class TestAptAnalysisGetEndpoints:
    def test_get_latest_returns_200_with_report(self):
        mock_report = _make_mock_report()
        mock_repo = MagicMock()
        mock_repo.get_latest.return_value = mock_report

        app.dependency_overrides[get_apt_analysis_repo] = lambda: mock_repo
        try:
            resp = client.get("/dashboard/apt/analysis/CC001/latest")
        finally:
            app.dependency_overrides.pop(get_apt_analysis_repo, None)

        assert resp.status_code == 200
        assert resp.json()["complex_code"] == "CC001"

    def test_get_latest_returns_404_when_no_report(self):
        mock_repo = MagicMock()
        mock_repo.get_latest.return_value = None

        app.dependency_overrides[get_apt_analysis_repo] = lambda: mock_repo
        try:
            resp = client.get("/dashboard/apt/analysis/NOTFOUND/latest")
        finally:
            app.dependency_overrides.pop(get_apt_analysis_repo, None)

        assert resp.status_code == 404

    def test_get_history_returns_list(self):
        mock_report = _make_mock_report()
        mock_repo = MagicMock()
        mock_repo.get_history.return_value = [mock_report]

        app.dependency_overrides[get_apt_analysis_repo] = lambda: mock_repo
        try:
            resp = client.get("/dashboard/apt/analysis/CC001")
        finally:
            app.dependency_overrides.pop(get_apt_analysis_repo, None)

        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        assert len(data) == 1
