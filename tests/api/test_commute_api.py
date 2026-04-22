import pytest
from unittest.mock import MagicMock
from fastapi.testclient import TestClient


def _make_app(commute_service):
    """의존성 오버라이드를 사용한 테스트용 앱 생성."""
    from main import app
    from api.dependencies import get_commute_service
    app.dependency_overrides[get_commute_service] = lambda: commute_service
    return app


class TestCommuteAPI:
    def test_get_all_commute_times_returns_three_modes(self):
        from modules.real_estate.commute.models import CommuteResult

        mock_svc = MagicMock()
        mock_svc.get_all_modes.return_value = {
            "transit": CommuteResult("k", "삼성역", "transit", 59, 1200),
            "car": CommuteResult("k", "삼성역", "car", 35, 15000),
            "walking": CommuteResult("k", "삼성역", "walking", 90, 5000),
        }
        client = TestClient(_make_app(mock_svc))
        resp = client.get("/dashboard/real-estate/commute", params={
            "address": "서울 송파구 가락동 124",
            "apt_name": "송파파크데일1단지",
            "district_code": "11710",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["transit"] == 59
        assert data["car"] == 35
        assert data["walking"] == 90
        assert data["destination"] == "삼성역"

    def test_partial_failure_returns_null_for_failed_mode(self):
        from modules.real_estate.commute.models import CommuteResult

        mock_svc = MagicMock()
        mock_svc.get_all_modes.return_value = {
            "transit": CommuteResult("k", "삼성역", "transit", 59, 0),
        }
        client = TestClient(_make_app(mock_svc))
        resp = client.get("/dashboard/real-estate/commute", params={
            "address": "서울 송파구 가락동 124",
            "apt_name": "테스트아파트",
            "district_code": "11710",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["transit"] == 59
        assert data["car"] is None
        assert data["walking"] is None

    def test_missing_required_params_returns_422(self):
        mock_svc = MagicMock()
        client = TestClient(_make_app(mock_svc))
        resp = client.get("/dashboard/real-estate/commute")
        assert resp.status_code == 422
