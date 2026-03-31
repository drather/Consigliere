"""
TDD tests for GeocoderService (Kakao API + SQLite cache)
"""
import sqlite3
import tempfile
import os
import pytest
from unittest.mock import patch, MagicMock

try:
    from modules.real_estate.geocoder import GeocoderService
except ImportError:
    from src.modules.real_estate.geocoder import GeocoderService


@pytest.fixture
def tmp_db(tmp_path):
    return str(tmp_path / "geocode_cache.db")


@pytest.fixture
def geocoder(tmp_db):
    return GeocoderService(api_key="test_key", cache_path=tmp_db)


def _seed_cache(db_path: str, cache_key: str, lat: float, lng: float):
    conn = sqlite3.connect(db_path)
    conn.execute(
        "CREATE TABLE IF NOT EXISTS geocode_cache "
        "(cache_key TEXT PRIMARY KEY, lat REAL, lng REAL, created_at TEXT)"
    )
    conn.execute(
        "INSERT INTO geocode_cache (cache_key, lat, lng, created_at) VALUES (?, ?, ?, datetime('now'))",
        (cache_key, lat, lng),
    )
    conn.commit()
    conn.close()


# ── Test 1: cache hit — no HTTP call ─────────────────────────────────────────
def test_geocode_cache_hit(tmp_db):
    _seed_cache(tmp_db, "1168010700__래미안퍼스티지", 37.5172, 127.0473)
    geocoder = GeocoderService(api_key="test_key", cache_path=tmp_db)
    with patch("requests.get") as mock_get:
        result = geocoder.geocode("래미안퍼스티지", "1168010700")
    assert result == (37.5172, 127.0473)
    mock_get.assert_not_called()


# ── Test 2: cache miss → calls Kakao API ─────────────────────────────────────
def test_geocode_cache_miss_calls_api(geocoder):
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "documents": [{"y": "37.5172", "x": "127.0473"}]
    }
    mock_response.raise_for_status = MagicMock()

    with patch("requests.get", return_value=mock_response) as mock_get:
        result = geocoder.geocode("래미안퍼스티지", "1168010700")

    assert result == pytest.approx((37.5172, 127.0473))
    mock_get.assert_called_once()
    # Verify URL contains kakao endpoint
    call_url = mock_get.call_args[0][0]
    assert "dapi.kakao.com" in call_url


# ── Test 3: requests exception → returns None ────────────────────────────────
def test_geocode_returns_none_on_api_failure(geocoder):
    with patch("requests.get", side_effect=Exception("network error")):
        result = geocoder.geocode("래미안퍼스티지", "1168010700")
    assert result is None


# ── Test 4: empty API result → returns None ──────────────────────────────────
def test_geocode_returns_none_on_empty_result(geocoder):
    mock_response = MagicMock()
    mock_response.json.return_value = {"documents": []}
    mock_response.raise_for_status = MagicMock()

    with patch("requests.get", return_value=mock_response):
        result = geocoder.geocode("없는아파트", "9999999999")
    assert result is None


# ── Test 5: batch_geocode returns dict with correct keys ─────────────────────
def test_batch_geocode_returns_dict(geocoder):
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "documents": [{"y": "37.5172", "x": "127.0473"}]
    }
    mock_response.raise_for_status = MagicMock()

    apt_keys = [
        {"apt_name": "래미안퍼스티지", "district_code": "1168010700"},
        {"apt_name": "아크로리버파크", "district_code": "1156010500"},
    ]
    with patch("requests.get", return_value=mock_response):
        result = geocoder.batch_geocode(apt_keys)

    assert isinstance(result, dict)
    assert "1168010700__래미안퍼스티지" in result
    assert "1156010500__아크로리버파크" in result


# ── Test 6: batch_geocode skips failed items ─────────────────────────────────
def test_batch_geocode_skips_failed(geocoder):
    """1건 성공, 1건 None 반환 시 결과 dict에 성공 키만 포함"""
    success_response = MagicMock()
    success_response.json.return_value = {
        "documents": [{"y": "37.5172", "x": "127.0473"}]
    }
    success_response.raise_for_status = MagicMock()

    fail_response = MagicMock()
    fail_response.json.return_value = {"documents": []}
    fail_response.raise_for_status = MagicMock()

    apt_keys = [
        {"apt_name": "래미안퍼스티지", "district_code": "1168010700"},
        {"apt_name": "없는아파트", "district_code": "9999999999"},
    ]
    with patch("requests.get", side_effect=[success_response, fail_response]):
        result = geocoder.batch_geocode(apt_keys)

    # 성공한 키 1개만 존재
    assert len(result) == 1
    assert "1168010700__래미안퍼스티지" in result
    # 실패 항목이 결과에 포함되지 않음
    assert "9999999999__없는아파트" not in result


# ── Test 7: cache persistence across instances ───────────────────────────────
def test_cache_persistence_across_instances(tmp_db):
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "documents": [{"y": "37.5172", "x": "127.0473"}]
    }
    mock_response.raise_for_status = MagicMock()

    geocoder1 = GeocoderService(api_key="test_key", cache_path=tmp_db)
    with patch("requests.get", return_value=mock_response):
        result1 = geocoder1.geocode("래미안퍼스티지", "1168010700")
    assert result1 == pytest.approx((37.5172, 127.0473))

    # New instance — should read from DB without any HTTP call
    geocoder2 = GeocoderService(api_key="test_key", cache_path=tmp_db)
    with patch("requests.get") as mock_get:
        result2 = geocoder2.geocode("래미안퍼스티지", "1168010700")
    assert result2 == pytest.approx((37.5172, 127.0473))
    mock_get.assert_not_called()
