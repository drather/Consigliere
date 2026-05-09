import os
import sys
import sqlite3
import json
import tempfile
import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime, timedelta

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..', 'src')))

from modules.real_estate.poi_collector import PoiCollector, PoiData


def _make_kakao_response(places):
    return {"documents": places, "meta": {"total_count": len(places)}}


def _make_station(name, distance_m):
    return {"place_name": name, "distance": str(distance_m), "category_group_code": "SW8"}


def _make_school(name, distance_m):
    return {"place_name": name, "distance": str(distance_m), "category_group_code": "SC4"}


def _make_place(name, distance_m):
    return {"place_name": name, "distance": str(distance_m)}


@pytest.fixture
def db_path(tmp_path):
    return str(tmp_path / "test_re.db")


@pytest.fixture
def collector(db_path):
    return PoiCollector(api_key="test_key", db_path=db_path)


class TestPoiCollectorCollect:
    def test_collect_returns_poi_data(self, collector):
        mock_stations = [_make_station("강남역", 350), _make_station("역삼역", 620)]
        mock_elem = [_make_school("역삼초등학교", 450)]
        mock_middle = [_make_school("언주중학교", 820)]
        mock_academies = [_make_place(f"학원{i}", 500) for i in range(15)]
        mock_marts = [_make_place("이마트", 300), _make_place("홈플러스", 900)]
        mock_convenience = [_make_place("GS25", 200), _make_place("CU", 300)]
        mock_pharmacies = [_make_place("약국", 400)]
        mock_medical = [_make_place("내과", 500)]
        mock_parks = [{"place_name": "중앙공원", "distance": "350"}]
        mock_restaurants = [_make_place(f"음식점{i}", 300) for i in range(10)]
        mock_cafes = [_make_place(f"카페{i}", 200) for i in range(5)]

        # 11 API calls: 지하철역, 초등학교, 중학교, 학원(paged), 마트,
        #               편의점, 약국, 병원, 공원, 음식점(paged), 카페(paged)
        responses = [
            _make_kakao_response(mock_stations),
            _make_kakao_response(mock_elem),
            _make_kakao_response(mock_middle),
            {"documents": mock_academies, "meta": {"total_count": 15, "is_end": True}},
            _make_kakao_response(mock_marts),
            _make_kakao_response(mock_convenience),
            _make_kakao_response(mock_pharmacies),
            _make_kakao_response(mock_medical),
            _make_kakao_response(mock_parks),
            {"documents": mock_restaurants, "meta": {"total_count": 10, "is_end": True}},
            {"documents": mock_cafes, "meta": {"total_count": 5, "is_end": True}},
        ]

        with patch("requests.get") as mock_get:
            mock_get.side_effect = [MagicMock(status_code=200, json=lambda r=r: r) for r in responses]
            result = collector.collect(
                complex_code="1234567890",
                lat=37.4979,
                lng=127.0276,
            )

        assert isinstance(result, PoiData)
        assert len(result.subway_stations) == 2
        assert result.subway_stations[0]["name"] == "강남역"
        assert result.subway_stations[0]["walk_minutes"] == 5  # 350m / 67m/min ≈ 5분
        assert result.schools_count == 2
        assert result.academies_count == 15
        assert result.marts_count == 2
        assert result.convenience_count == 2
        assert result.pharmacy_count == 1
        assert result.medical_count == 1
        assert result.park_nearest_m == 350
        assert result.restaurant_count == 10
        assert result.cafe_count == 5

    def test_collect_caches_result(self, collector, db_path):
        mock_response = _make_kakao_response([])
        with patch("requests.get") as mock_get:
            mock_get.return_value = MagicMock(status_code=200, json=lambda: mock_response)
            collector.collect("CODE1", 37.0, 127.0)
            first_call_count = mock_get.call_count
            collector.collect("CODE1", 37.0, 127.0)
            assert mock_get.call_count == first_call_count  # 캐시 히트 → 추가 호출 없음

    def test_collect_refreshes_after_ttl(self, collector, db_path):
        # Insert an expired cache row directly via SQL (14-column schema)
        old_date = (datetime.now() - timedelta(days=40)).strftime("%Y-%m-%d %H:%M:%S")
        conn = sqlite3.connect(db_path)
        conn.execute(
            "INSERT INTO poi_cache VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            ("OLD_CODE", 37.0, 127.0, "[]", 0, 0, 0, 0, 0, 0, 0, 0, 0, old_date),
        )
        conn.commit()
        conn.close()

        mock_response = _make_kakao_response([])
        with patch("requests.get") as mock_get:
            mock_get.return_value = MagicMock(status_code=200, json=lambda: mock_response)
            collector.collect("OLD_CODE", 37.0, 127.0)
            assert mock_get.call_count > 0  # TTL 만료 → 재수집

    def test_collect_returns_empty_on_api_failure(self, collector):
        with patch("requests.get") as mock_get:
            mock_get.side_effect = Exception("network error")
            result = collector.collect("FAIL", 37.0, 127.0)
        assert isinstance(result, PoiData)
        assert result.schools_count == 0
        assert result.subway_stations == []

    def test_walk_minutes_calculation(self, collector):
        """350m → 5분 (67m/min 보행속도 기준 올림)"""
        stations = [{"place_name": "역삼역", "distance": "350"}]
        result = collector._parse_stations(stations)
        assert result[0]["walk_minutes"] == 5


def test_poi_data_has_new_fields():
    poi = PoiData(complex_code="X001")
    assert hasattr(poi, "convenience_count")
    assert hasattr(poi, "pharmacy_count")
    assert hasattr(poi, "medical_count")
    assert hasattr(poi, "park_nearest_m")
    assert hasattr(poi, "restaurant_count")
    assert hasattr(poi, "cafe_count")
    assert poi.convenience_count == 0
    assert poi.park_nearest_m == 0


def test_migrate_adds_columns_to_old_schema():
    _OLD_DDL = """
    CREATE TABLE IF NOT EXISTS poi_cache (
        complex_code    TEXT PRIMARY KEY,
        lat             REAL,
        lng             REAL,
        subway_stations TEXT,
        schools_count   INTEGER,
        academies_count INTEGER,
        marts_count     INTEGER,
        collected_at    TEXT
    );
    """
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name
    try:
        with sqlite3.connect(db_path) as conn:
            conn.executescript(_OLD_DDL)
        collector = PoiCollector(api_key="dummy", db_path=db_path)
        with sqlite3.connect(db_path) as conn:
            cols = {row[1] for row in conn.execute("PRAGMA table_info(poi_cache)")}
        expected_new = {"convenience_count", "pharmacy_count", "medical_count",
                        "park_nearest_m", "restaurant_count", "cafe_count"}
        assert expected_new.issubset(cols)
    finally:
        os.unlink(db_path)
