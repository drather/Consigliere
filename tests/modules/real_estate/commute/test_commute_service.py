import os
import sys
import pytest
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../../../src"))

from modules.real_estate.commute.models import CommuteResult
from modules.real_estate.commute.commute_repository import CommuteRepository


def make_service(repo=None, tmap_client=None, geocoder=None, config=None):
    from modules.real_estate.commute.commute_service import CommuteService
    repo = repo or CommuteRepository(db_path=":memory:", ttl_days=90)
    config = config or {
        "destination": "삼성역",
        "destination_lat": 37.5088,
        "destination_lng": 127.0633,
    }
    return CommuteService(
        repo=repo,
        tmap_client=tmap_client or MagicMock(),
        geocoder=geocoder or MagicMock(),
        config=config,
    )


class TestCommuteServiceCacheHit:
    def test_cache_hit_returns_without_api_call(self):
        """캐시에 유효한 값이 있으면 tmap_client를 호출하지 않는다."""
        repo = CommuteRepository(db_path=":memory:", ttl_days=90)
        repo.upsert(CommuteResult(
            origin_key="11680__래미안",
            destination="삼성역",
            mode="transit",
            duration_minutes=20,
            distance_meters=1000,
        ))
        mock_client = MagicMock()
        svc = make_service(repo=repo, tmap_client=mock_client)

        result = svc.get(
            origin_key="11680__래미안",
            road_address="서울 강남구 역삼동 123",
            apt_name="래미안",
            district_code="11680",
            mode="transit",
        )

        assert result.duration_minutes == 20
        assert result.cached is True
        mock_client.route_with_legs.assert_not_called()


class TestCommuteServiceCacheMiss:
    def test_cache_miss_calls_tmap_and_stores(self):
        """캐시가 없으면 geocoder → tmap_client 순서로 호출하고 결과를 저장한다."""
        mock_geocoder = MagicMock()
        mock_geocoder.geocode.return_value = (37.4942, 127.0611)

        mock_client = MagicMock()
        mock_client.route_with_legs.return_value = (59, 1200, [], "")

        repo = CommuteRepository(db_path=":memory:", ttl_days=90)
        svc = make_service(repo=repo, tmap_client=mock_client, geocoder=mock_geocoder)

        result = svc.get(
            origin_key="11710__파크데일",
            road_address="서울 송파구 가락동 124",
            apt_name="파크데일",
            district_code="11710",
            mode="transit",
        )

        assert result.duration_minutes == 59
        assert result.cached is False
        mock_geocoder.geocode.assert_called_once()
        mock_client.route_with_legs.assert_called_once()

        # 저장 확인
        stored = repo.get("11710__파크데일", "삼성역", "transit")
        assert stored is not None
        assert stored.duration_minutes == 59

    def test_geocode_failure_returns_none(self):
        """지오코딩 실패 시 None 반환 (예외 전파 안 함)."""
        mock_geocoder = MagicMock()
        mock_geocoder.geocode.return_value = None

        svc = make_service(geocoder=mock_geocoder)
        result = svc.get("k", "주소없음", "단지", "11680", mode="transit")
        assert result is None

    def test_tmap_failure_returns_none(self):
        """T-map API 오류 시 None 반환."""
        mock_geocoder = MagicMock()
        mock_geocoder.geocode.return_value = (37.49, 127.06)

        mock_client = MagicMock()
        mock_client.route_with_legs.side_effect = Exception("T-map 오류")

        svc = make_service(geocoder=mock_geocoder, tmap_client=mock_client)
        result = svc.get("k", "주소", "단지", "11680", mode="transit")
        assert result is None

    def test_cache_miss_stores_legs_in_result(self):
        """캐시 미스 시 route_with_legs()가 호출되어 legs가 CommuteResult에 포함된다."""
        mock_geocoder = MagicMock()
        mock_geocoder.geocode.return_value = (37.49, 127.06)

        mock_client = MagicMock()
        mock_client.route_with_legs.return_value = (
            59, 1200,
            [{"mode": "BUS", "route": "302", "from_name": "가락시장", "to_name": "잠실역",
              "duration_minutes": 12, "stop_count": 4}],
            "도보 5분 → 302번 버스 → 잠실역",
        )

        repo = CommuteRepository(db_path=":memory:", ttl_days=90)
        svc = make_service(repo=repo, tmap_client=mock_client, geocoder=mock_geocoder)

        result = svc.get(
            origin_key="11710__파크데일",
            road_address="서울 송파구 가락동 124",
            apt_name="파크데일",
            district_code="11710",
            mode="transit",
        )

        assert result is not None
        assert result.duration_minutes == 59
        assert len(result.legs) == 1
        assert result.legs[0]["route"] == "302"
        assert result.route_summary == "도보 5분 → 302번 버스 → 잠실역"
        mock_client.route_with_legs.assert_called_once()


class TestCommuteServiceGetAllModes:
    def test_get_all_modes_returns_three_results(self):
        """get_all_modes는 transit/car/walking 모두 반환한다."""
        mock_geocoder = MagicMock()
        mock_geocoder.geocode.return_value = (37.49, 127.06)

        mock_client = MagicMock()
        mock_client.route_with_legs.side_effect = [(59, 1200, [], ""), (30, 15000, [], ""), (90, 5000, [], "")]

        svc = make_service(geocoder=mock_geocoder, tmap_client=mock_client)
        results = svc.get_all_modes("k", "서울 송파구 가락동 124", "파크데일", "11710")

        assert results["transit"].duration_minutes == 59
        assert results["car"].duration_minutes == 30
        assert results["walking"].duration_minutes == 90
        assert mock_client.route_with_legs.call_count == 3

    def test_get_all_modes_partial_failure_skips_failed_mode(self):
        """일부 모드 실패 시 나머지만 반환한다."""
        mock_geocoder = MagicMock()
        mock_geocoder.geocode.return_value = (37.49, 127.06)

        mock_client = MagicMock()
        mock_client.route_with_legs.side_effect = [(59, 1200, [], ""), Exception("car 오류"), (90, 5000, [], "")]

        svc = make_service(geocoder=mock_geocoder, tmap_client=mock_client)
        results = svc.get_all_modes("k", "주소", "단지", "11710")

        assert "transit" in results
        assert "car" not in results
        assert "walking" in results
