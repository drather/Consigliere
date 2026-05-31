import pytest
from unittest.mock import MagicMock
from fastapi.testclient import TestClient

from main import app
from api.dependencies import get_report_repo, get_location_service, get_geocoder_service
from api.dependencies import get_apt_master_repo

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


class TestCollectPoiEndpoint:
    def test_collect_poi_returns_collected_count(self):
        mock_entry = MagicMock()
        mock_entry.complex_code = "CC001"
        mock_entry.apt_name = "테스트아파트"
        mock_entry.district_code = "11680"
        mock_entry.road_address = "서울시 강남구 테헤란로 1"

        mock_master_repo = MagicMock()
        mock_master_repo.search.return_value = [mock_entry]

        mock_location_svc = MagicMock()
        mock_location_svc.get_stale_complex_codes.return_value = {"CC001"}

        mock_geocoder = MagicMock()
        mock_geocoder.geocode.return_value = (37.5, 127.0)

        app.dependency_overrides[get_apt_master_repo] = lambda: mock_master_repo
        app.dependency_overrides[get_location_service] = lambda: mock_location_svc
        app.dependency_overrides[get_geocoder_service] = lambda: mock_geocoder
        try:
            resp = client.post("/jobs/poi/collect?limit=5")
        finally:
            app.dependency_overrides.pop(get_apt_master_repo, None)
            app.dependency_overrides.pop(get_location_service, None)
            app.dependency_overrides.pop(get_geocoder_service, None)

        assert resp.status_code == 200
        assert resp.json()["collected"] == 1
        mock_location_svc.collect_poi.assert_called_once_with("CC001", 37.5, 127.0)

    def test_collect_poi_skips_geocode_failure(self):
        mock_entry = MagicMock()
        mock_entry.complex_code = "CC001"
        mock_entry.apt_name = "테스트아파트"
        mock_entry.district_code = "11680"
        mock_entry.road_address = None

        mock_master_repo = MagicMock()
        mock_master_repo.search.return_value = [mock_entry]

        mock_location_svc = MagicMock()
        mock_location_svc.get_stale_complex_codes.return_value = {"CC001"}

        mock_geocoder = MagicMock()
        mock_geocoder.geocode.return_value = None  # geocode 실패

        app.dependency_overrides[get_apt_master_repo] = lambda: mock_master_repo
        app.dependency_overrides[get_location_service] = lambda: mock_location_svc
        app.dependency_overrides[get_geocoder_service] = lambda: mock_geocoder
        try:
            resp = client.post("/jobs/poi/collect?limit=5")
        finally:
            app.dependency_overrides.pop(get_apt_master_repo, None)
            app.dependency_overrides.pop(get_location_service, None)
            app.dependency_overrides.pop(get_geocoder_service, None)

        assert resp.status_code == 200
        assert resp.json()["collected"] == 0
        mock_location_svc.collect_poi.assert_not_called()
