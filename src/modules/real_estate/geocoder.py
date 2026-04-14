"""
GeocoderService — Kakao Local API keyword search with SQLite cache.
"""
import os
import sqlite3
import logging
from datetime import datetime
from typing import Optional
from typing import Protocol, runtime_checkable
import yaml
import requests

logger = logging.getLogger(__name__)

_KAKAO_KEYWORD_URL = "https://dapi.kakao.com/v2/local/search/keyword.json"

_DDL = """
CREATE TABLE IF NOT EXISTS geocode_cache (
    cache_key TEXT PRIMARY KEY,
    lat REAL,
    lng REAL,
    created_at TEXT
)
"""

_CONFIG_PATH = os.path.join(os.path.dirname(__file__), "config.yaml")


def _load_geocode_cache_path() -> str:
    """config.yaml에서 geocode_cache_path를 읽어 반환. 없으면 기본값 사용."""
    try:
        with open(_CONFIG_PATH, "r", encoding="utf-8") as f:
            cfg = yaml.safe_load(f) or {}
        return cfg.get("geocode_cache_path", "data/geocode_cache.db")
    except Exception:
        return "data/geocode_cache.db"


@runtime_checkable
class GeocoderProtocol(Protocol):
    """지오코딩 서비스 인터페이스 (DIP)."""

    def geocode(self, apt_name: str, district_code: str) -> Optional[tuple[float, float]]:
        ...

    def batch_geocode(self, apt_keys: list[dict]) -> dict[str, tuple[float, float]]:
        ...


class GeocoderService:
    def __init__(self, api_key: str, cache_path: Optional[str] = None):
        if cache_path is None:
            cache_path = _load_geocode_cache_path()
        self._api_key = api_key
        self._cache_path = cache_path
        self._init_db()

    # ── DB helpers ───────────────────────────────────────────────────────────

    def _init_db(self):
        with sqlite3.connect(self._cache_path) as conn:
            conn.execute(_DDL)
            conn.commit()

    def _cache_get(self, cache_key: str) -> Optional[tuple[float, float]]:
        with sqlite3.connect(self._cache_path) as conn:
            row = conn.execute(
                "SELECT lat, lng FROM geocode_cache WHERE cache_key = ?",
                (cache_key,),
            ).fetchone()
        if row:
            return (row[0], row[1])
        return None

    def _cache_set(self, cache_key: str, lat: float, lng: float):
        with sqlite3.connect(self._cache_path) as conn:
            conn.execute(
                "INSERT OR REPLACE INTO geocode_cache (cache_key, lat, lng, created_at) "
                "VALUES (?, ?, ?, ?)",
                (cache_key, lat, lng, datetime.utcnow().isoformat()),
            )
            conn.commit()

    # ── Public API ───────────────────────────────────────────────────────────

    def geocode(
        self,
        apt_name: str,
        district_code: str,
        address: Optional[str] = None,
    ) -> Optional[tuple[float, float]]:
        """
        Returns (lat, lng) for the given apartment.
        Cache key: district_code__apt_name.
        Query priority: address (road/legal) → apt_name.
        """
        cache_key = f"{district_code}__{apt_name}"

        cached = self._cache_get(cache_key)
        if cached is not None:
            return cached

        query = address.strip() if address else apt_name
        try:
            resp = requests.get(
                _KAKAO_KEYWORD_URL,
                headers={"Authorization": f"KakaoAK {self._api_key}"},
                params={"query": query, "size": 1},
                timeout=5,
            )
            resp.raise_for_status()
            documents = resp.json().get("documents", [])
            if not documents:
                return None

            doc = documents[0]
            lat = float(doc["y"])
            lng = float(doc["x"])
            self._cache_set(cache_key, lat, lng)
            return (lat, lng)

        except Exception as exc:
            logger.warning("geocode failed for %s: %s", query, exc)
            return None

    def batch_geocode(self, apt_keys: list[dict]) -> dict[str, tuple[float, float]]:
        """
        Geocode multiple apartments.

        apt_keys: [{"apt_name": str, "district_code": str, "address": str (optional)}, ...]
        Returns: {"district_code__apt_name": (lat, lng), ...}
        address 필드가 있으면 Kakao 검색 쿼리로 우선 사용 (cache key는 항상 apt_name 기준).
        """
        result: dict[str, tuple[float, float]] = {}
        for item in apt_keys:
            apt_name = item["apt_name"]
            district_code = item["district_code"]
            address = item.get("address")
            coords = self.geocode(apt_name, district_code, address=address)
            if coords is not None:
                cache_key = f"{district_code}__{apt_name}"
                result[cache_key] = coords
        return result
