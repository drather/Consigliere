import os
import sys
import pytest
from unittest.mock import MagicMock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../../../src"))


def _make_hybrid(odsay=None, tmap=None):
    from modules.real_estate.commute.hybrid_commute_client import HybridCommuteClient
    return HybridCommuteClient(
        odsay=odsay or MagicMock(),
        tmap=tmap or MagicMock(),
    )


class TestHybridRouteWithLegs:
    def test_transit_delegates_to_odsay(self):
        """transit 모드 → OdsayClient.route_with_legs 호출."""
        mock_odsay = MagicMock()
        mock_odsay.route_with_legs.return_value = (45, 800, [], "2호선 → 서울역")
        mock_tmap = MagicMock()

        client = _make_hybrid(odsay=mock_odsay, tmap=mock_tmap)
        result = client.route_with_legs(37.49, 127.06, 37.51, 127.07, mode="transit")

        mock_odsay.route_with_legs.assert_called_once_with(37.49, 127.06, 37.51, 127.07)
        mock_tmap.route_with_legs.assert_not_called()
        assert result == (45, 800, [], "2호선 → 서울역")

    def test_car_delegates_to_tmap(self):
        """car 모드 → TmapClient.route_with_legs 호출."""
        mock_odsay = MagicMock()
        mock_tmap = MagicMock()
        mock_tmap.route_with_legs.return_value = (30, 15000, [], "올림픽대로 (15.0km)")

        client = _make_hybrid(odsay=mock_odsay, tmap=mock_tmap)
        result = client.route_with_legs(37.49, 127.06, 37.51, 127.07, mode="car")

        mock_tmap.route_with_legs.assert_called_once_with(37.49, 127.06, 37.51, 127.07, mode="car")
        mock_odsay.route_with_legs.assert_not_called()
        assert result == (30, 15000, [], "올림픽대로 (15.0km)")

    def test_walking_delegates_to_tmap(self):
        """walking 모드 → TmapClient.route_with_legs 호출."""
        mock_odsay = MagicMock()
        mock_tmap = MagicMock()
        mock_tmap.route_with_legs.return_value = (90, 5000, [], "도보 (5.0km)")

        client = _make_hybrid(odsay=mock_odsay, tmap=mock_tmap)
        result = client.route_with_legs(37.49, 127.06, 37.51, 127.07, mode="walking")

        mock_tmap.route_with_legs.assert_called_once_with(37.49, 127.06, 37.51, 127.07, mode="walking")
        mock_odsay.route_with_legs.assert_not_called()


class TestHybridRoute:
    def test_transit_route_delegates_to_odsay(self):
        """route() transit → OdsayClient.route 호출."""
        mock_odsay = MagicMock()
        mock_odsay.route.return_value = (45, 800)
        mock_tmap = MagicMock()

        client = _make_hybrid(odsay=mock_odsay, tmap=mock_tmap)
        duration, distance = client.route(37.49, 127.06, 37.51, 127.07, mode="transit")

        mock_odsay.route.assert_called_once_with(37.49, 127.06, 37.51, 127.07)
        mock_tmap.route.assert_not_called()
        assert duration == 45

    def test_car_route_delegates_to_tmap(self):
        """route() car → TmapClient.route 호출."""
        mock_odsay = MagicMock()
        mock_tmap = MagicMock()
        mock_tmap.route.return_value = (30, 15000)

        client = _make_hybrid(odsay=mock_odsay, tmap=mock_tmap)
        duration, distance = client.route(37.49, 127.06, 37.51, 127.07, mode="car")

        mock_tmap.route.assert_called_once_with(37.49, 127.06, 37.51, 127.07, mode="car")
        mock_odsay.route.assert_not_called()
        assert duration == 30
