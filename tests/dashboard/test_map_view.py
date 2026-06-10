import folium
import pytest

try:
    from dashboard.components.map_view import render_detail_map
except ImportError:
    from src.dashboard.components.map_view import render_detail_map


class _FakeGeocoder:
    """apt_name/주소에 따라 좌표를 반환하는 테스트용 geocoder."""

    def geocode(self, apt_name: str, district_code: str, address: str | None = None):
        query = address or apt_name
        if "반포" in query or "래미안" in query:
            return (37.5010, 127.0260)  # 반포동 근처
        if "여의도" in query or "삼성역" in query:
            return (37.5210, 126.9240)  # 여의도/강남 근처
        return None


def test_render_detail_map_returns_folium_map():
    geocoder = _FakeGeocoder()
    result = render_detail_map(
        address="서울 서초구 반포동 1",
        apt_name="래미안원베일리",
        district_code="11650",
        geocoder=geocoder,
        workplace_address=None,
        poi_cached=None,
        commute_summary=None,
    )
    assert isinstance(result, folium.Map)


def test_render_detail_map_centers_on_apt():
    geocoder = _FakeGeocoder()
    result = render_detail_map(
        address="서울 서초구 반포동 1",
        apt_name="래미안원베일리",
        district_code="11650",
        geocoder=geocoder,
        workplace_address=None,
        poi_cached=None,
        commute_summary=None,
    )
    # folium.Map.location is [lat, lng]
    lat, lng = result.location
    assert abs(lat - 37.5010) < 0.01
    assert abs(lng - 127.0260) < 0.01


def test_render_detail_map_geocode_failure_returns_default_map():
    """geocode 실패 시 서울 기본 좌표로 fallback한다."""
    class _FailGeocoder:
        def geocode(self, apt_name, district_code, address=None):
            return None

    result = render_detail_map(
        address="존재하지않는주소",
        apt_name="테스트단지",
        district_code="00000",
        geocoder=_FailGeocoder(),
        workplace_address=None,
        poi_cached=None,
        commute_summary=None,
    )
    assert isinstance(result, folium.Map)
    assert result.location == [37.5665, 126.9780]


def test_render_detail_map_with_workplace():
    """직장 주소(또는 역명) 제공 시 지도가 정상 생성된다."""
    geocoder = _FakeGeocoder()
    result = render_detail_map(
        address="서울 서초구 반포동 1",
        apt_name="래미안원베일리",
        district_code="11650",
        geocoder=geocoder,
        workplace_address="삼성역",
        poi_cached=None,
        commute_summary={"transit": 38},
    )
    assert isinstance(result, folium.Map)


def test_render_detail_map_workplace_geocode_failure_skips_pin():
    """직장 좌표 조회 실패 시 직장 핀/경로 없이 정상 반환한다."""
    geocoder = _FakeGeocoder()
    result = render_detail_map(
        address="서울 서초구 반포동 1",
        apt_name="래미안원베일리",
        district_code="11650",
        geocoder=geocoder,
        workplace_address="존재하지않는직장주소",
        poi_cached=None,
        commute_summary=None,
    )
    assert isinstance(result, folium.Map)
