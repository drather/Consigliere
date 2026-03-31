"""
TDD tests for render_map_view (folium map component)
"""
import pandas as pd
import folium
import pytest
from unittest.mock import MagicMock, patch

try:
    from dashboard.components.map_view import render_map_view
except ImportError:
    from src.dashboard.components.map_view import render_map_view


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
