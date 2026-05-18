import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../../../src"))

from modules.real_estate.daily_report.report_formatter import (
    render_location_summary,
    _school_label,
    _extract_location_summary,
)
from modules.real_estate.daily_report.report_types import LocationSummaryData


def _full_loc() -> LocationSummaryData:
    return {
        "subway_stations": [
            {"name": "강남", "line": "2호선", "walk_minutes": 8},
            {"name": "선릉", "line": "분당선", "walk_minutes": 12},
        ],
        "mart_count": 2,
        "convenience_count": 6,
        "cafe_count": 11,
        "restaurant_count": 38,
        "pharmacy_count": 4,
        "medical_count": 7,
        "park_nearest_m": 300,
        "school_nearby_count": 5,
        "school_transfer_rate": 0.072,
        "school_avg_per_teacher": 14.0,
        "school_score": 85,
        "school_label": "학군 우수",
        "nuisance_high_count": 0,
        "nuisance_mid_count": 0,
    }


# ── _school_label ────────────────────────────────────────────────
def test_school_label_high_transfer_rate():
    assert _school_label(0.08, 5) == "학군 우수"

def test_school_label_high_nearby():
    assert _school_label(0.01, 3) == "학군 우수"

def test_school_label_medium_transfer_rate():
    assert _school_label(0.04, 2) == "학군 양호"

def test_school_label_medium_nearby():
    assert _school_label(0.01, 1) == "학군 양호"

def test_school_label_low():
    assert _school_label(0.01, 0) == "학군 평이"

def test_school_label_boundary_high():
    assert _school_label(0.06, 0) == "학군 우수"

def test_school_label_boundary_medium():
    assert _school_label(0.03, 0) == "학군 양호"


# ── render_location_summary ──────────────────────────────────────
def test_render_location_summary_contains_header():
    result = render_location_summary(_full_loc())
    assert "📍 입지 현황" in result

def test_render_location_summary_subway_names():
    result = render_location_summary(_full_loc())
    assert "강남(2호선)" in result
    assert "도보 8분" in result
    assert "선릉(분당선)" in result
    assert "도보 12분" in result

def test_render_location_summary_amenities():
    result = render_location_summary(_full_loc())
    assert "마트 2" in result
    assert "카페 11" in result
    assert "식당 38" in result

def test_render_location_summary_medical():
    result = render_location_summary(_full_loc())
    assert "7곳" in result

def test_render_location_summary_park():
    result = render_location_summary(_full_loc())
    assert "300m" in result

def test_render_location_summary_school_label():
    result = render_location_summary(_full_loc())
    assert "학군 우수" in result

def test_render_location_summary_no_nuisance_row_when_zero():
    result = render_location_summary(_full_loc())
    assert "⚠️" not in result

def test_render_location_summary_nuisance_row_shown():
    loc = dict(_full_loc())
    loc["nuisance_high_count"] = 1
    loc["nuisance_mid_count"] = 0
    result = render_location_summary(loc)
    assert "⚠️" in result
    assert "고위험 1곳" in result

def test_render_location_summary_nuisance_mid_shown():
    loc = dict(_full_loc())
    loc["nuisance_high_count"] = 0
    loc["nuisance_mid_count"] = 2
    result = render_location_summary(loc)
    assert "⚠️" in result
    assert "중위험 2곳" in result

def test_render_location_summary_no_subway():
    loc = dict(_full_loc())
    loc["subway_stations"] = []
    result = render_location_summary(loc)
    assert "역 없음" in result

def test_render_location_summary_no_medical_row_when_zero():
    loc = dict(_full_loc())
    loc["medical_count"] = 0
    result = render_location_summary(loc)
    assert "병원" not in result

def test_render_location_summary_zero_amenity_hidden():
    loc = dict(_full_loc())
    loc["mart_count"] = 0
    result = render_location_summary(loc)
    assert "마트 0" not in result

def test_render_location_summary_no_school_data():
    loc: LocationSummaryData = {
        "subway_stations": [],
        "mart_count": 1,
        "convenience_count": 0,
        "cafe_count": 3,
        "restaurant_count": 10,
        "pharmacy_count": 1,
        "medical_count": 2,
        "park_nearest_m": 0,
        "nuisance_high_count": 0,
        "nuisance_mid_count": 0,
    }
    result = render_location_summary(loc)
    assert "학교 정보 수집 전" in result

def test_render_location_summary_no_park():
    loc = dict(_full_loc())
    loc["park_nearest_m"] = 0
    result = render_location_summary(loc)
    assert "없음" in result


# ── _extract_location_summary ────────────────────────────────────
def test_extract_location_summary_no_poi_returns_none():
    result = _extract_location_summary({"apt_name": "래미안"})
    assert result is None

def test_extract_location_summary_with_poi():
    from unittest.mock import MagicMock
    mock_poi = MagicMock()
    mock_poi.subway_stations = [
        {"name": "강남", "line": "2호선", "walk_minutes": 8}
    ]
    mock_poi.marts_count = 2
    mock_poi.convenience_count = 6
    mock_poi.cafe_count = 11
    mock_poi.restaurant_count = 38
    mock_poi.pharmacy_count = 4
    mock_poi.medical_count = 7
    mock_poi.park_nearest_m = 300
    mock_poi.nuisance_high_count = 0
    mock_poi.nuisance_mid_count = 0

    c = {
        "_poi": mock_poi,
        "school_score": 85,
        "school_nearby_count": 5,
        "school_transfer_rate": 0.072,
        "school_avg_per_teacher": 14.0,
    }
    result = _extract_location_summary(c)
    assert result is not None
    assert result["mart_count"] == 2
    assert result["school_score"] == 85
    assert result["school_label"] == "학군 우수"

def test_extract_location_summary_without_school_fields():
    from unittest.mock import MagicMock
    mock_poi = MagicMock()
    mock_poi.subway_stations = []
    mock_poi.marts_count = 1
    mock_poi.convenience_count = 0
    mock_poi.cafe_count = 3
    mock_poi.restaurant_count = 12
    mock_poi.pharmacy_count = 2
    mock_poi.medical_count = 1
    mock_poi.park_nearest_m = 0
    mock_poi.nuisance_high_count = 0
    mock_poi.nuisance_mid_count = 0

    c = {"_poi": mock_poi}
    result = _extract_location_summary(c)
    assert result is not None
    assert "school_score" not in result
    assert "school_label" not in result

def test_extract_location_summary_subway_sorted_by_walk():
    from unittest.mock import MagicMock
    mock_poi = MagicMock()
    mock_poi.subway_stations = [
        {"name": "선릉", "line": "분당선", "walk_minutes": 12},
        {"name": "강남", "line": "2호선", "walk_minutes": 8},
        {"name": "역삼", "line": "2호선", "walk_minutes": 15},
    ]
    mock_poi.marts_count = 0
    mock_poi.convenience_count = 0
    mock_poi.cafe_count = 0
    mock_poi.restaurant_count = 0
    mock_poi.pharmacy_count = 0
    mock_poi.medical_count = 0
    mock_poi.park_nearest_m = 0
    mock_poi.nuisance_high_count = 0
    mock_poi.nuisance_mid_count = 0

    c = {"_poi": mock_poi}
    result = _extract_location_summary(c)
    assert result is not None
    stations = result["subway_stations"]
    assert len(stations) == 2
    assert stations[0]["name"] == "강남"   # 8분이 먼저
    assert stations[1]["name"] == "선릉"   # 12분
