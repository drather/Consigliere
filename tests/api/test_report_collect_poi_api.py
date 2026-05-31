import pytest
from unittest.mock import MagicMock
from fastapi.testclient import TestClient

from main import app
from api.dependencies import get_report_repo

client = TestClient(app)


def _make_mock_report():
    from modules.real_estate.report_repository import ProfessionalReport
    return ProfessionalReport(
        date="2026-05-30",
        budget_available=500_000_000,
        macro_summary="금리 안정",
        candidates_summary=[],
        location_analyses=[],
        school_analyses=[],
        strategy={"recommendation": "관망"},
        markdown="# 전문 리포트",
    )


class TestProfessionalReportEndpoints:
    def test_list_reports_returns_200(self):
        mock_repo = MagicMock()
        mock_repo.list_dates.return_value = ["2026-05-30", "2026-05-29"]

        app.dependency_overrides[get_report_repo] = lambda: mock_repo
        try:
            resp = client.get("/dashboard/real-estate/professional-reports")
        finally:
            app.dependency_overrides.pop(get_report_repo, None)

        assert resp.status_code == 200
        assert resp.json() == {"dates": ["2026-05-30", "2026-05-29"]}

    def test_get_report_returns_200(self):
        mock_repo = MagicMock()
        mock_repo.load.return_value = _make_mock_report()

        app.dependency_overrides[get_report_repo] = lambda: mock_repo
        try:
            resp = client.get("/dashboard/real-estate/professional-reports/2026-05-30")
        finally:
            app.dependency_overrides.pop(get_report_repo, None)

        assert resp.status_code == 200
        data = resp.json()
        assert data["date"] == "2026-05-30"
        assert data["macro_summary"] == "금리 안정"

    def test_get_report_returns_404_when_missing(self):
        mock_repo = MagicMock()
        mock_repo.load.return_value = None

        app.dependency_overrides[get_report_repo] = lambda: mock_repo
        try:
            resp = client.get("/dashboard/real-estate/professional-reports/1999-01-01")
        finally:
            app.dependency_overrides.pop(get_report_repo, None)

        assert resp.status_code == 404
