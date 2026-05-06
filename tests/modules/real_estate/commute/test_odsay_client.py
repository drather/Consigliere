import os
import sys
import math
import pytest
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../../../src"))

# ODsay 정상 응답 — 지하철+버스+도보 혼합 경로
ODSAY_RESPONSE = {
    "result": {
        "path": [{
            "info": {
                "totalTime": 45,   # 분 단위
                "totalWalk": 800,  # 도보 거리(m)
            },
            "subPath": [
                {
                    "trafficType": 3,     # 도보
                    "sectionTime": 300,   # 초
                    "startName": "출발지",
                    "endName": "강남역",
                },
                {
                    "trafficType": 1,     # 지하철
                    "sectionTime": 900,   # 초
                    "startName": "강남역",
                    "endName": "서울역",
                    "lane": [{"name": "2호선"}],
                    "passStopList": {
                        "stations": [
                            {"stationName": "강남역"},
                            {"stationName": "역삼역"},
                            {"stationName": "서울역"},
                        ]
                    },
                },
                {
                    "trafficType": 2,     # 버스
                    "sectionTime": 600,   # 초
                    "startName": "서울역",
                    "endName": "종로3가역",
                    "lane": [{"busNo": "150"}],
                    "passStopList": {
                        "stations": [
                            {"stationName": "서울역"},
                            {"stationName": "종로3가역"},
                        ]
                    },
                },
                {
                    "trafficType": 3,     # 도보
                    "sectionTime": 180,   # 초
                    "startName": "종로3가역",
                    "endName": "목적지",
                },
            ]
        }]
    }
}

ODSAY_EMPTY_PATH = {"result": {"path": []}}


def _mock_get(response_json):
    mock_resp = MagicMock()
    mock_resp.json.return_value = response_json
    mock_resp.raise_for_status.return_value = None
    return mock_resp


class TestOdsayClientRouteDuration:
    def test_total_time_is_already_minutes(self):
        """ODsay totalTime은 분 단위 — 변환 없이 그대로 반환."""
        from modules.real_estate.commute.odsay_client import OdsayClient
        client = OdsayClient(api_key="test-key")

        with patch("modules.real_estate.commute.odsay_client.requests.get",
                   return_value=_mock_get(ODSAY_RESPONSE)):
            duration, distance = client.route(37.4942, 127.0611, 37.5088, 127.0633)

        assert duration == 45
        assert distance == 800

    def test_non_transit_mode_raises(self):
        """transit 이외 모드는 ValueError를 발생시킨다."""
        from modules.real_estate.commute.odsay_client import OdsayClient
        client = OdsayClient(api_key="test-key")
        with pytest.raises(ValueError, match="transit"):
            client.route(37.49, 127.06, 37.51, 127.07, mode="car")

    def test_empty_path_raises_value_error(self):
        """path가 비어 있으면 ValueError를 발생시킨다."""
        from modules.real_estate.commute.odsay_client import OdsayClient
        client = OdsayClient(api_key="test-key")

        with patch("modules.real_estate.commute.odsay_client.requests.get",
                   return_value=_mock_get(ODSAY_EMPTY_PATH)):
            with pytest.raises(ValueError, match="empty path"):
                client.route(37.4942, 127.0611, 37.5088, 127.0633)


class TestOdsayClientLegs:
    def test_legs_count_matches_subpath(self):
        """subPath 4개 → legs 4개."""
        from modules.real_estate.commute.odsay_client import OdsayClient
        client = OdsayClient(api_key="test-key")

        with patch("modules.real_estate.commute.odsay_client.requests.get",
                   return_value=_mock_get(ODSAY_RESPONSE)):
            _, _, legs, _ = client.route_with_legs(37.4942, 127.0611, 37.5088, 127.0633)

        assert len(legs) == 4

    def test_traffic_type_1_maps_to_subway(self):
        """trafficType=1 → mode='SUBWAY', lane[0].name → route."""
        from modules.real_estate.commute.odsay_client import OdsayClient
        client = OdsayClient(api_key="test-key")

        with patch("modules.real_estate.commute.odsay_client.requests.get",
                   return_value=_mock_get(ODSAY_RESPONSE)):
            _, _, legs, _ = client.route_with_legs(37.4942, 127.0611, 37.5088, 127.0633)

        subway = next(l for l in legs if l["mode"] == "SUBWAY")
        assert subway["route"] == "2호선"
        assert subway["stop_count"] == 3
        assert subway["from_name"] == "강남역"
        assert subway["to_name"] == "서울역"

    def test_traffic_type_2_maps_to_bus(self):
        """trafficType=2 → mode='BUS', lane[0].busNo → route."""
        from modules.real_estate.commute.odsay_client import OdsayClient
        client = OdsayClient(api_key="test-key")

        with patch("modules.real_estate.commute.odsay_client.requests.get",
                   return_value=_mock_get(ODSAY_RESPONSE)):
            _, _, legs, _ = client.route_with_legs(37.4942, 127.0611, 37.5088, 127.0633)

        bus = next(l for l in legs if l["mode"] == "BUS")
        assert bus["route"] == "150"
        assert bus["stop_count"] == 2

    def test_traffic_type_3_maps_to_walk(self):
        """trafficType=3 → mode='WALK', duration_minutes = ceil(sectionTime/60)."""
        from modules.real_estate.commute.odsay_client import OdsayClient
        client = OdsayClient(api_key="test-key")

        with patch("modules.real_estate.commute.odsay_client.requests.get",
                   return_value=_mock_get(ODSAY_RESPONSE)):
            _, _, legs, _ = client.route_with_legs(37.4942, 127.0611, 37.5088, 127.0633)

        walk_legs = [l for l in legs if l["mode"] == "WALK"]
        assert len(walk_legs) == 2
        # 첫 번째 도보: 300초 = 5분
        assert walk_legs[0]["duration_minutes"] == 5

    def test_section_time_seconds_converted_to_minutes(self):
        """sectionTime(초) → duration_minutes(분, ceil)."""
        from modules.real_estate.commute.odsay_client import OdsayClient
        client = OdsayClient(api_key="test-key")

        with patch("modules.real_estate.commute.odsay_client.requests.get",
                   return_value=_mock_get(ODSAY_RESPONSE)):
            _, _, legs, _ = client.route_with_legs(37.4942, 127.0611, 37.5088, 127.0633)

        subway = next(l for l in legs if l["mode"] == "SUBWAY")
        # 900초 = 15분
        assert subway["duration_minutes"] == 15


class TestOdsayClientSummary:
    def test_summary_contains_subway_route(self):
        """route_summary에 지하철 노선명 포함."""
        from modules.real_estate.commute.odsay_client import OdsayClient
        client = OdsayClient(api_key="test-key")

        with patch("modules.real_estate.commute.odsay_client.requests.get",
                   return_value=_mock_get(ODSAY_RESPONSE)):
            _, _, _, summary = client.route_with_legs(37.4942, 127.0611, 37.5088, 127.0633)

        assert "2호선" in summary

    def test_summary_contains_bus_number(self):
        """route_summary에 버스 번호 포함."""
        from modules.real_estate.commute.odsay_client import OdsayClient
        client = OdsayClient(api_key="test-key")

        with patch("modules.real_estate.commute.odsay_client.requests.get",
                   return_value=_mock_get(ODSAY_RESPONSE)):
            _, _, _, summary = client.route_with_legs(37.4942, 127.0611, 37.5088, 127.0633)

        assert "150" in summary

    def test_summary_contains_walk_minutes(self):
        """route_summary에 도보 시간 포함."""
        from modules.real_estate.commute.odsay_client import OdsayClient
        client = OdsayClient(api_key="test-key")

        with patch("modules.real_estate.commute.odsay_client.requests.get",
                   return_value=_mock_get(ODSAY_RESPONSE)):
            _, _, _, summary = client.route_with_legs(37.4942, 127.0611, 37.5088, 127.0633)

        assert "도보" in summary

    def test_request_passes_correct_params(self):
        """GET 요청에 SX=경도, SY=위도 파라미터가 포함된다."""
        from modules.real_estate.commute.odsay_client import OdsayClient
        client = OdsayClient(api_key="test-key")

        with patch("modules.real_estate.commute.odsay_client.requests.get",
                   return_value=_mock_get(ODSAY_RESPONSE)) as mock_get:
            client.route(37.4942, 127.0611, 37.5088, 127.0633)

        call_kwargs = mock_get.call_args[1]
        params = call_kwargs["params"]
        assert params["SX"] == "127.0611"  # 경도
        assert params["SY"] == "37.4942"   # 위도
        assert params["EX"] == "127.0633"
        assert params["EY"] == "37.5088"
        assert params["apiKey"] == "test-key"
