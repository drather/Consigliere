import os
import sys
import pytest
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../../../src"))


TRANSIT_RESPONSE = {
    "metaData": {
        "plan": {
            "itineraries": [
                {"totalTime": 3540, "totalWalkDistance": 456}
            ]
        }
    }
}

CAR_RESPONSE = {
    "features": [
        {"type": "Feature", "properties": {"totalTime": 2400, "totalDistance": 15000}}
    ]
}

WALKING_RESPONSE = {
    "features": [
        {"type": "Feature", "properties": {"totalTime": 3600, "totalDistance": 5000}}
    ]
}


class TestTmapClientTransit:
    def test_transit_duration_seconds_to_minutes(self):
        """3540초 = 59분으로 파싱되어야 한다."""
        from modules.real_estate.commute.tmap_client import TmapClient
        client = TmapClient(api_key="test-key")

        mock_resp = MagicMock()
        mock_resp.json.return_value = TRANSIT_RESPONSE
        mock_resp.raise_for_status.return_value = None

        with patch("modules.real_estate.commute.tmap_client.requests.post", return_value=mock_resp) as mock_post:
            duration, distance = client.route(
                origin_lat=37.4942, origin_lng=127.0611,
                dest_lat=37.5088, dest_lng=127.0633,
                mode="transit",
            )

        assert duration == 59
        assert distance == 456
        call_url = mock_post.call_args[0][0]
        assert "transit/routes" in call_url

    def test_transit_missing_itineraries_raises(self):
        from modules.real_estate.commute.tmap_client import TmapClient
        client = TmapClient(api_key="test-key")

        mock_resp = MagicMock()
        mock_resp.json.return_value = {"metaData": {"plan": {"itineraries": []}}}
        mock_resp.raise_for_status.return_value = None

        with patch("modules.real_estate.commute.tmap_client.requests.post", return_value=mock_resp):
            with pytest.raises(ValueError, match="itineraries"):
                client.route(37.4942, 127.0611, 37.5088, 127.0633, mode="transit")


class TestTmapClientCar:
    def test_car_duration_seconds_to_minutes(self):
        """2400초 = 40분으로 파싱되어야 한다."""
        from modules.real_estate.commute.tmap_client import TmapClient
        client = TmapClient(api_key="test-key")

        mock_resp = MagicMock()
        mock_resp.json.return_value = CAR_RESPONSE
        mock_resp.raise_for_status.return_value = None

        with patch("modules.real_estate.commute.tmap_client.requests.post", return_value=mock_resp) as mock_post:
            duration, distance = client.route(37.4942, 127.0611, 37.5088, 127.0633, mode="car")

        assert duration == 40
        assert distance == 15000
        call_url = mock_post.call_args[0][0]
        assert "tmap/routes" in call_url
        assert "pedestrian" not in call_url

    def test_car_missing_features_raises(self):
        from modules.real_estate.commute.tmap_client import TmapClient
        client = TmapClient(api_key="test-key")

        mock_resp = MagicMock()
        mock_resp.json.return_value = {"features": []}
        mock_resp.raise_for_status.return_value = None

        with patch("modules.real_estate.commute.tmap_client.requests.post", return_value=mock_resp):
            with pytest.raises(ValueError):
                client.route(37.4942, 127.0611, 37.5088, 127.0633, mode="car")


class TestTmapClientWalking:
    def test_walking_duration_seconds_to_minutes(self):
        """3600초 = 60분으로 파싱되어야 한다."""
        from modules.real_estate.commute.tmap_client import TmapClient
        client = TmapClient(api_key="test-key")

        mock_resp = MagicMock()
        mock_resp.json.return_value = WALKING_RESPONSE
        mock_resp.raise_for_status.return_value = None

        with patch("modules.real_estate.commute.tmap_client.requests.post", return_value=mock_resp) as mock_post:
            duration, distance = client.route(37.4942, 127.0611, 37.5088, 127.0633, mode="walking")

        assert duration == 60
        assert distance == 5000
        call_url = mock_post.call_args[0][0]
        assert "pedestrian" in call_url

    def test_invalid_mode_raises(self):
        from modules.real_estate.commute.tmap_client import TmapClient
        client = TmapClient(api_key="test-key")
        with pytest.raises(ValueError, match="mode"):
            client.route(0, 0, 0, 0, mode="bicycle")


TRANSIT_RESPONSE_WITH_LEGS = {
    "metaData": {
        "plan": {
            "itineraries": [{
                "totalTime": 3540,
                "totalWalkDistance": 456,
                "legs": [
                    {
                        "mode": "WALK",
                        "sectionTime": 300,
                        "distance": 400,
                        "start": {"name": "출발지"},
                        "end": {"name": "가락시장 정류장"},
                    },
                    {
                        "mode": "BUS",
                        "route": "302",
                        "sectionTime": 720,
                        "distance": 3200,
                        "start": {"name": "가락시장"},
                        "end": {"name": "잠실역"},
                        "passStopList": {
                            "stationList": [
                                {"stationName": "가락시장"},
                                {"stationName": "석촌"},
                                {"stationName": "잠실"},
                                {"stationName": "잠실역"},
                            ]
                        },
                    },
                    {
                        "mode": "SUBWAY",
                        "route": "2호선",
                        "sectionTime": 480,
                        "distance": 4100,
                        "start": {"name": "잠실역"},
                        "end": {"name": "삼성역"},
                        "passStopList": {
                            "stationList": [
                                {"stationName": "잠실역"},
                                {"stationName": "종합운동장"},
                                {"stationName": "삼성역"},
                            ]
                        },
                    },
                    {
                        "mode": "WALK",
                        "sectionTime": 180,
                        "distance": 200,
                        "start": {"name": "삼성역 5번 출구"},
                        "end": {"name": "목적지"},
                    },
                ],
            }]
        }
    }
}

CAR_RESPONSE_WITH_FEATURES = {
    "features": [
        {
            "type": "Feature",
            "geometry": {"type": "Point"},
            "properties": {"totalTime": 2100, "totalDistance": 15000},
        },
        {
            "type": "Feature",
            "geometry": {"type": "LineString"},
            "properties": {"index": 1, "name": "올림픽대로", "distance": 8000},
        },
        {
            "type": "Feature",
            "geometry": {"type": "LineString"},
            "properties": {"index": 2, "name": "잠실대교", "distance": 1500},
        },
        {
            "type": "Feature",
            "geometry": {"type": "LineString"},
            "properties": {"index": 3, "name": "테헤란로", "distance": 3000},
        },
    ]
}


class TestTmapClientRouteWithLegs:
    def test_transit_legs_parsed_correctly(self):
        """route_with_legs transit — legs 4개, 버스 302번, 2호선 포함."""
        from modules.real_estate.commute.tmap_client import TmapClient
        client = TmapClient(api_key="test-key")
        mock_resp = MagicMock()
        mock_resp.json.return_value = TRANSIT_RESPONSE_WITH_LEGS
        mock_resp.raise_for_status.return_value = None

        with patch("modules.real_estate.commute.tmap_client.requests.post", return_value=mock_resp):
            duration, distance, legs, summary = client.route_with_legs(
                37.4942, 127.0611, 37.5088, 127.0633, mode="transit"
            )

        assert duration == 59
        assert len(legs) == 4
        bus_leg = next(l for l in legs if l["mode"] == "BUS")
        assert bus_leg["route"] == "302"
        assert bus_leg["stop_count"] == 4
        subway_leg = next(l for l in legs if l["mode"] == "SUBWAY")
        assert subway_leg["route"] == "2호선"
        assert subway_leg["stop_count"] == 3

    def test_transit_summary_contains_bus_and_subway(self):
        """transit route_summary에 버스 번호와 지하철 노선 포함."""
        from modules.real_estate.commute.tmap_client import TmapClient
        client = TmapClient(api_key="test-key")
        mock_resp = MagicMock()
        mock_resp.json.return_value = TRANSIT_RESPONSE_WITH_LEGS
        mock_resp.raise_for_status.return_value = None

        with patch("modules.real_estate.commute.tmap_client.requests.post", return_value=mock_resp):
            _, _, _, summary = client.route_with_legs(
                37.4942, 127.0611, 37.5088, 127.0633, mode="transit"
            )

        assert "302" in summary
        assert "2호선" in summary or "삼성역" in summary

    def test_car_legs_contains_road_names(self):
        """route_with_legs car — 주요 도로명 포함."""
        from modules.real_estate.commute.tmap_client import TmapClient
        client = TmapClient(api_key="test-key")
        mock_resp = MagicMock()
        mock_resp.json.return_value = CAR_RESPONSE_WITH_FEATURES
        mock_resp.raise_for_status.return_value = None

        with patch("modules.real_estate.commute.tmap_client.requests.post", return_value=mock_resp):
            duration, distance, legs, summary = client.route_with_legs(
                37.4942, 127.0611, 37.5088, 127.0633, mode="car"
            )

        assert duration == 35
        assert any(l["road_name"] == "올림픽대로" for l in legs)
        assert "올림픽대로" in summary

    def test_car_summary_contains_distance(self):
        """car summary에 km 단위 거리 포함."""
        from modules.real_estate.commute.tmap_client import TmapClient
        client = TmapClient(api_key="test-key")
        mock_resp = MagicMock()
        mock_resp.json.return_value = CAR_RESPONSE_WITH_FEATURES
        mock_resp.raise_for_status.return_value = None

        with patch("modules.real_estate.commute.tmap_client.requests.post", return_value=mock_resp):
            _, _, _, summary = client.route_with_legs(
                37.4942, 127.0611, 37.5088, 127.0633, mode="car"
            )

        assert "km" in summary

    def test_existing_route_still_works(self):
        """기존 route() 메서드는 변경 없이 동작해야 한다."""
        from modules.real_estate.commute.tmap_client import TmapClient
        client = TmapClient(api_key="test-key")
        mock_resp = MagicMock()
        mock_resp.json.return_value = CAR_RESPONSE_WITH_FEATURES
        mock_resp.raise_for_status.return_value = None

        with patch("modules.real_estate.commute.tmap_client.requests.post", return_value=mock_resp):
            duration, distance = client.route(37.4942, 127.0611, 37.5088, 127.0633, mode="car")

        assert duration == 35
        assert distance == 15000
