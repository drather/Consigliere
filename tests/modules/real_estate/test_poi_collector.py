import os
import sys
import sqlite3
import json
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
        mock_schools = [_make_school("역삼초등학교", 450), _make_school("언주중학교", 820)]
        mock_academies = [_make_place(f"학원{i}", 500) for i in range(25)]
        mock_marts = [_make_place("이마트", 300), _make_place("홈플러스", 900)]

        responses = [
            _make_kakao_response(mock_stations),
            _make_kakao_response(mock_schools),
            _make_kakao_response(mock_academies),
            _make_kakao_response(mock_marts),
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
        assert result.academies_count == 25
        assert result.marts_count == 2

    def test_collect_caches_result(self, collector, db_path):
        mock_response = _make_kakao_response([])
        with patch("requests.get") as mock_get:
            mock_get.return_value = MagicMock(status_code=200, json=lambda: mock_response)
            collector.collect("CODE1", 37.0, 127.0)
            first_call_count = mock_get.call_count
            collector.collect("CODE1", 37.0, 127.0)
            assert mock_get.call_count == first_call_count  # 캐시 히트 → 추가 호출 없음

    def test_collect_refreshes_after_ttl(self, collector, db_path):
        conn = sqlite3.connect(db_path)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS poi_cache (
                complex_code TEXT PRIMARY KEY,
                lat REAL, lng REAL,
                subway_stations TEXT,
                schools_count INTEGER,
                academies_count INTEGER,
                marts_count INTEGER,
                collected_at TEXT
            )
        """)
        old_date = (datetime.now() - timedelta(days=40)).strftime("%Y-%m-%d %H:%M:%S")
        conn.execute(
            "INSERT INTO poi_cache VALUES (?,?,?,?,?,?,?,?)",
            ("OLD_CODE", 37.0, 127.0, "[]", 0, 0, 0, old_date),
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
