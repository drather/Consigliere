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

    def test_response_includes_legs_and_summary(self):
        """응답에 transit_legs, transit_summary 포함돼야 한다."""
        from modules.real_estate.commute.models import CommuteResult

        legs = [{"mode": "BUS", "route": "302", "from_name": "가락시장",
                 "to_name": "잠실역", "duration_minutes": 12, "stop_count": 4}]
        mock_svc = MagicMock()
        mock_svc.get_all_modes.return_value = {
            "transit": CommuteResult("k", "삼성역", "transit", 59, 1200,
                                     legs=legs, route_summary="도보 5분 → 302번 버스 → 잠실역"),
            "car": CommuteResult("k", "삼성역", "car", 35, 15000,
                                  legs=[{"mode": "ROAD", "road_name": "올림픽대로", "distance_meters": 8000}],
                                  route_summary="올림픽대로 → 테헤란로 (15.0km)"),
            "walking": CommuteResult("k", "삼성역", "walking", 90, 5000,
                                      legs=[], route_summary="가락로 (5.0km)"),
        }
        client = TestClient(_make_app(mock_svc))
        resp = client.get("/dashboard/real-estate/commute", params={
            "address": "서울 송파구 가락동 124",
            "apt_name": "송파파크데일1단지",
            "district_code": "11710",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["transit_legs"][0]["route"] == "302"
        assert data["transit_summary"] == "도보 5분 → 302번 버스 → 잠실역"
        assert data["car_summary"] == "올림픽대로 → 테헤란로 (15.0km)"
        assert data["walking_legs"] == []
