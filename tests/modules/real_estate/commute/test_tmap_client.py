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
