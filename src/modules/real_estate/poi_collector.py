"""
PoiCollector — 카카오 로컬 API 반경 키워드 검색으로 단지 주변 POI 수집.
결과는 real_estate.db의 poi_cache 테이블에 30일 TTL로 캐시된다.
"""
import json
import math
import os
import sqlite3
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import List, Dict, Optional

import requests
import yaml

from core.logger import get_logger

logger = get_logger(__name__)

_KAKAO_KEYWORD_URL = "https://dapi.kakao.com/v2/local/search/keyword.json"
_CONFIG_PATH = os.path.join(os.path.dirname(__file__), "config.yaml")

_DDL = """
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


def _load_ttl_days() -> int:
    try:
        with open(_CONFIG_PATH, "r", encoding="utf-8") as f:
            cfg = yaml.safe_load(f) or {}
        return int(cfg.get("poi_cache_ttl_days", 30))
    except Exception:
        return 30


def _load_walk_speed_mpm() -> int:
    try:
        with open(_CONFIG_PATH, "r", encoding="utf-8") as f:
            cfg = yaml.safe_load(f) or {}
        return int(cfg.get("poi", {}).get("walk_speed_mpm", 67))
    except Exception:
        return 67


@dataclass
class PoiData:
    complex_code: str = ""
    subway_stations: List[Dict] = field(default_factory=list)
    schools_count: int = 0
    academies_count: int = 0
    marts_count: int = 0
    collected_at: str = ""

    @property
    def closest_station_walk_minutes(self) -> Optional[int]:
        if not self.subway_stations:
            return None
        return min(s["walk_minutes"] for s in self.subway_stations)

    @property
    def stations_within_5min(self) -> List[Dict]:
        return [s for s in self.subway_stations if s["walk_minutes"] <= 5]


class PoiCollector:
    STATION_RADIUS = 500
    SCHOOL_RADIUS = 1000
    ACADEMY_RADIUS = 1000
    MART_RADIUS = 1000

    def __init__(self, api_key: str, db_path: str, ttl_days: Optional[int] = None):
        self._api_key = api_key
        self._db_path = db_path
        self._ttl_days = ttl_days if ttl_days is not None else _load_ttl_days()
        self._walk_speed_mpm = _load_walk_speed_mpm()
        self._init_db()

    def _init_db(self) -> None:
        with sqlite3.connect(self._db_path) as conn:
            conn.executescript(_DDL)

    def collect(self, complex_code: str, lat: float, lng: float) -> PoiData:
        cached = self._load_cache(complex_code)
        if cached:
            return cached
        try:
            return self._fetch_and_cache(complex_code, lat, lng)
        except Exception as e:
            logger.warning(f"[PoiCollector] API 실패 complex={complex_code}: {e}")
            return PoiData(complex_code=complex_code)

    def _fetch_and_cache(self, complex_code: str, lat: float, lng: float) -> PoiData:
        stations = self._search("지하철역", lat, lng, self.STATION_RADIUS, size=5)
        elem = self._search("초등학교", lat, lng, self.SCHOOL_RADIUS, size=15)
        middle = self._search("중학교", lat, lng, self.SCHOOL_RADIUS, size=15)
        seen: set = set()
        schools: list = []
        for doc in elem + middle:
            key = doc.get("id") or doc.get("place_name", "")
            if key not in seen:
                seen.add(key)
                schools.append(doc)
        academies = self._search("학원", lat, lng, self.ACADEMY_RADIUS, size=15)
        marts = self._search("대형마트 백화점", lat, lng, self.MART_RADIUS, size=15)

        poi = PoiData(
            complex_code=complex_code,
            subway_stations=self._parse_stations(stations),
            schools_count=len(schools),
            academies_count=len(academies),
            marts_count=len(marts),
            collected_at=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        )
        self._save_cache(complex_code, lat, lng, poi)
        return poi

    def _search(self, query: str, lat: float, lng: float, radius: int, size: int = 15) -> List[Dict]:
        params = {"query": query, "y": str(lat), "x": str(lng), "radius": radius, "size": size}
        headers = {"Authorization": f"KakaoAK {self._api_key}"}
        resp = requests.get(_KAKAO_KEYWORD_URL, params=params, headers=headers, timeout=10)
        resp.raise_for_status()
        return resp.json().get("documents", [])

    def _parse_stations(self, docs: List[Dict]) -> List[Dict]:
        result = []
        for d in docs:
            dist_m = int(d.get("distance", 0))
            walk_min = round(dist_m / self._walk_speed_mpm)
            result.append({"name": d.get("place_name", ""), "walk_minutes": walk_min})
        return result

    def _load_cache(self, complex_code: str) -> Optional[PoiData]:
        with sqlite3.connect(self._db_path) as conn:
            row = conn.execute(
                "SELECT subway_stations, schools_count, academies_count, marts_count, collected_at "
                "FROM poi_cache WHERE complex_code = ?",
                (complex_code,),
            ).fetchone()
        if not row:
            return None
        collected_at = row[4]
        if self._is_expired(collected_at):
            return None
        return PoiData(
            complex_code=complex_code,
            subway_stations=json.loads(row[0] or "[]"),
            schools_count=row[1] or 0,
            academies_count=row[2] or 0,
            marts_count=row[3] or 0,
            collected_at=collected_at,
        )

    def _save_cache(self, complex_code: str, lat: float, lng: float, poi: PoiData) -> None:
        with sqlite3.connect(self._db_path) as conn:
            conn.execute(
                "INSERT OR REPLACE INTO poi_cache VALUES (?,?,?,?,?,?,?,?)",
                (
                    complex_code, lat, lng,
                    json.dumps(poi.subway_stations, ensure_ascii=False),
                    poi.schools_count, poi.academies_count, poi.marts_count,
                    poi.collected_at,
                ),
            )

    def _is_expired(self, collected_at: str) -> bool:
        try:
            dt = datetime.strptime(collected_at, "%Y-%m-%d %H:%M:%S")
            return datetime.now() - dt > timedelta(days=self._ttl_days)
        except Exception:
            return True
