import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../../../src"))

from modules.real_estate.daily_report.report_types import (
    TxPoint, TrendData, CommuteData, CandidateSummary,
)


def test_txpoint_structure():
    p: TxPoint = {"price_eok": 8.8, "deal_date": "2026-05-10"}
    assert p["price_eok"] == 8.8
    assert p["deal_date"] == "2026-05-10"


def test_trenddata_structure():
    t: TrendData = {
        "points": [{"price_eok": 8.5, "deal_date": "2026-05-07"},
                   {"price_eok": 8.8, "deal_date": "2026-05-10"}],
        "avg_eok": 8.65,
        "change_pct": -3.2,
        "area_sqm": 84.0,
    }
    assert len(t["points"]) == 2
    assert t["avg_eok"] == 8.65


def test_commutedata_structure():
    c: CommuteData = {
        "transit_minutes": 35,
        "car_minutes": None,
        "walk_minutes": None,
        "route_summary": "2호선 30분 → 도보 5분",
    }
    assert c["transit_minutes"] == 35
    assert c["car_minutes"] is None


def test_candidatesummary_structure():
    cs: CandidateSummary = {
        "apt_name": "래미안",
        "sigungu": "강남구",
        "area_sqm": 84.0,
        "household_count": 1200,
        "composite_score": 85,
        "verdict": "매수 검토",
        "key_points": ["✅ 역세권", "📈 상승 추세"],
        "trend": {
            "points": [{"price_eok": 28.0, "deal_date": "2026-05-10"}],
            "avg_eok": 28.0, "change_pct": 2.5, "area_sqm": 84.0,
        },
        "commute": {
            "transit_minutes": 20, "car_minutes": 30,
            "walk_minutes": None, "route_summary": "",
        },
        "residential_results": [],
        "investment_results": [],
    }
    assert cs["apt_name"] == "래미안"
    assert cs["composite_score"] == 85


def test_subway_station_structure():
    from modules.real_estate.daily_report.report_types import SubwayStation
    s: SubwayStation = {"name": "강남", "line": "2호선", "walk_minutes": 8}
    assert s["name"] == "강남"
    assert s["walk_minutes"] == 8


def test_location_summary_data_full():
    from modules.real_estate.daily_report.report_types import LocationSummaryData
    loc: LocationSummaryData = {
        "subway_stations": [{"name": "강남", "line": "2호선", "walk_minutes": 8}],
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
    assert loc["mart_count"] == 2
    assert loc["school_label"] == "학군 우수"
    assert loc["school_transfer_rate"] == 0.072


def test_location_summary_data_partial():
    """total=False이므로 키 일부만 있어도 유효하다."""
    from modules.real_estate.daily_report.report_types import LocationSummaryData
    loc: LocationSummaryData = {
        "subway_stations": [],
        "mart_count": 0,
    }
    assert loc["mart_count"] == 0
    assert "school_score" not in loc
