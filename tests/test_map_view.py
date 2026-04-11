"""
TDD tests for render_map_view and render_master_map_view (folium map components)
"""
import pandas as pd
import folium
import pytest
from unittest.mock import MagicMock, patch

try:
    from dashboard.components.map_view import (
        render_map_view,
        render_master_map_view,
        _build_master_popup_html,
    )
    from modules.real_estate.models import ApartmentMaster
except ImportError:
    from src.dashboard.components.map_view import (
        render_map_view,
        render_master_map_view,
        _build_master_popup_html,
    )
    from src.modules.real_estate.models import ApartmentMaster


def _make_df():
    return pd.DataFrame([
        {
            "apt_name": "래미안퍼스티지",
            "district_code": "1168010700",
            "deal_date": "2026-03-15",
            "price": 2_550_000_000,
            "exclusive_area": 84.97,
            "floor": 10,
        },
        {
            "apt_name": "래미안퍼스티지",
            "district_code": "1168010700",
            "deal_date": "2026-02-20",
            "price": 1_820_000_000,
            "exclusive_area": 59.91,
            "floor": 5,
        },
        {
            "apt_name": "아크로리버파크",
            "district_code": "1156010500",
            "deal_date": "2026-03-10",
            "price": 3_000_000_000,
            "exclusive_area": 112.0,
            "floor": 15,
        },
    ])


def _make_geocoder(lat=37.5172, lng=127.0473):
    geocoder = MagicMock()
    geocoder.batch_geocode.return_value = {
        "1168010700__래미안퍼스티지": (lat, lng),
        "1156010500__아크로리버파크": (37.5082, 126.9974),
    }
    return geocoder


# ── Test 1: return type is folium.Map ────────────────────────────────────────
def test_render_map_returns_folium_map():
    df = _make_df()
    geocoder = _make_geocoder()
    result = render_map_view(df, geocoder)
    assert isinstance(result, folium.Map)


# ── Test 2: empty df — no error, returns folium.Map ──────────────────────────
def test_render_map_empty_df():
    df = pd.DataFrame(columns=["apt_name", "district_code", "deal_date", "price", "exclusive_area", "floor"])
    geocoder = MagicMock()
    geocoder.batch_geocode.return_value = {}
    result = render_map_view(df, geocoder)
    assert isinstance(result, folium.Map)


# ── Test 3: marker count matches unique apts ─────────────────────────────────
def test_marker_count_matches_unique_apts():
    df = _make_df()
    geocoder = _make_geocoder()
    result = render_map_view(df, geocoder)

    # Count markers in the map's children
    markers = [
        child for child in result._children.values()
        if isinstance(child, folium.Marker)
    ]
    # 2 unique apts, both have coordinates → 2 markers
    assert len(markers) == 2


# ── Test 4: popup contains apt name ──────────────────────────────────────────
def test_popup_contains_apt_name():
    df = _make_df()
    geocoder = _make_geocoder()
    result = render_map_view(df, geocoder)

    markers = [
        child for child in result._children.values()
        if isinstance(child, folium.Marker)
    ]
    assert len(markers) > 0

    # At least one marker popup should contain the apt name
    popup_texts = []
    for marker in markers:
        for child in marker._children.values():
            if isinstance(child, folium.Popup):
                popup_texts.append(child.html.render())

    combined = " ".join(popup_texts)
    assert "래미안퍼스티지" in combined or "아크로리버파크" in combined


# ═══════════════════════════════════════════════════════════════════════════════
# render_master_map_view & _build_master_popup_html 테스트
# ═══════════════════════════════════════════════════════════════════════════════

def _make_master(apt_name="래미안퍼스티지", district_code="11680") -> ApartmentMaster:
    return ApartmentMaster(
        apt_name=apt_name,
        district_code=district_code,
        complex_code="A12345",
        household_count=2678,
        building_count=15,
        parking_count=0,
        constructor="삼성물산",
        approved_date="20091030",
        road_address="서울특별시 서초구 반포대로 201",
        legal_address="서울특별시 서초구 반포동 1-1",
        top_floor=35,
        sido="서울특별시",
        sigungu="서초구",
    )


def _make_master_geocoder():
    geocoder = MagicMock()
    geocoder.batch_geocode.return_value = {
        "11680__래미안퍼스티지": (37.5082, 126.9974),
        "11650__아크로리버파크": (37.5080, 126.9970),
    }
    return geocoder


def _make_tx_df(apt_name="래미안퍼스티지", district_code="11680") -> pd.DataFrame:
    return pd.DataFrame([
        {"apt_name": apt_name, "district_code": district_code,
         "deal_date": "2026-03-15", "price": 2_550_000_000, "exclusive_area": 84.97, "floor": 10},
        {"apt_name": apt_name, "district_code": district_code,
         "deal_date": "2026-01-10", "price": 2_480_000_000, "exclusive_area": 84.97, "floor": 5},
    ])


# ── render_master_map_view ────────────────────────────────────────────────────

def test_render_master_map_returns_folium_map():
    masters = [_make_master()]
    fmap = render_master_map_view(masters, _make_tx_df(), _make_master_geocoder())
    assert isinstance(fmap, folium.Map)


def test_render_master_map_empty_masters():
    fmap = render_master_map_view([], pd.DataFrame(), MagicMock())
    assert isinstance(fmap, folium.Map)


def test_render_master_map_marker_count():
    """마스터 2개 단지 → 2개 마커 (좌표 있는 것만)."""
    masters = [
        _make_master("래미안퍼스티지", "11680"),
        _make_master("아크로리버파크", "11650"),
    ]
    fmap = render_master_map_view(masters, pd.DataFrame(), _make_master_geocoder())
    markers = [c for c in fmap._children.values() if isinstance(c, folium.Marker)]
    assert len(markers) == 2


def test_render_master_map_no_marker_if_no_coords():
    """좌표를 반환하지 않는 단지는 마커가 생성되지 않는다."""
    masters = [_make_master()]
    geocoder = MagicMock()
    geocoder.batch_geocode.return_value = {}  # 좌표 없음
    fmap = render_master_map_view(masters, pd.DataFrame(), geocoder)
    markers = [c for c in fmap._children.values() if isinstance(c, folium.Marker)]
    assert len(markers) == 0


def test_render_master_map_blue_marker_when_has_transactions():
    """거래 있는 단지 → 파란색 마커."""
    masters = [_make_master()]
    fmap = render_master_map_view(masters, _make_tx_df(), _make_master_geocoder())
    markers = [c for c in fmap._children.values() if isinstance(c, folium.Marker)]
    assert len(markers) == 1
    icon = list(markers[0]._children.values())[0]
    assert isinstance(icon, folium.Icon)
    # folium.Icon은 color를 options["marker_color"]로 저장
    assert icon.options.get("marker_color") == "blue"


def test_render_master_map_gray_marker_when_no_transactions():
    """거래 없는 단지 → 회색 마커."""
    masters = [_make_master()]
    fmap = render_master_map_view(masters, pd.DataFrame(), _make_master_geocoder())
    markers = [c for c in fmap._children.values() if isinstance(c, folium.Marker)]
    assert len(markers) == 1
    icon = list(markers[0]._children.values())[0]
    assert isinstance(icon, folium.Icon)
    assert icon.options.get("marker_color") == "gray"


# ── _build_master_popup_html ──────────────────────────────────────────────────

def test_build_master_popup_contains_apt_name():
    master = _make_master()
    html = _build_master_popup_html(master, pd.DataFrame())
    assert "래미안퍼스티지" in html


def test_build_master_popup_contains_basic_info():
    master = _make_master()
    html = _build_master_popup_html(master, pd.DataFrame())
    assert "2,678" in html or "2678" in html   # 세대수
    assert "2009" in html                       # 준공연도
    assert "삼성물산" in html                   # 건설사


def test_build_master_popup_no_transactions():
    master = _make_master()
    html = _build_master_popup_html(master, pd.DataFrame())
    assert "거래 이력이 없습니다" in html


def test_build_master_popup_with_transactions():
    master = _make_master()
    html = _build_master_popup_html(master, _make_tx_df())
    assert "2026-03-15" in html
    assert "84.97" in html


def test_build_master_popup_max_10_transactions():
    """11건 거래가 있어도 팝업에는 최대 10건만 표시된다."""
    master = _make_master()
    rows = [
        {"apt_name": "래미안퍼스티지", "district_code": "11680",
         "deal_date": f"2026-0{i % 9 + 1}-01", "price": 2_000_000_000,
         "exclusive_area": 84.0, "floor": i}
        for i in range(1, 12)
    ]
    tx_df = pd.DataFrame(rows)
    html = _build_master_popup_html(master, tx_df)
    # 날짜 형식 "2026-0X-01" 이 최대 10개
    count = html.count("2026-0")
    assert count <= 10


def test_build_master_popup_address_displayed():
    master = _make_master()
    html = _build_master_popup_html(master, pd.DataFrame())
    assert "반포대로" in html
