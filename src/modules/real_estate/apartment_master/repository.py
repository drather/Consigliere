"""
ApartmentMasterRepository — SQLite CRUD for apartment master data.

geocoder.py 패턴과 동일한 구조:
  - cache_key = f"{district_code}__{apt_name}"
  - INSERT OR REPLACE로 저장
"""
import sqlite3
from datetime import datetime, timezone
from typing import List, Optional

from modules.real_estate.models import ApartmentMaster

_DDL = """
CREATE TABLE IF NOT EXISTS apartment_master (
    cache_key           TEXT PRIMARY KEY,
    complex_code        TEXT DEFAULT '',
    household_count     INTEGER DEFAULT 0,
    building_count      INTEGER DEFAULT 0,
    parking_count       INTEGER DEFAULT 0,
    constructor         TEXT DEFAULT '',
    approved_date       TEXT DEFAULT '',
    floor_area_ratio    REAL,
    building_coverage_ratio REAL,
    fetched_at          TEXT
)
"""


class ApartmentMasterRepository:
    def __init__(self, db_path: str = "data/apartment_master.db"):
        self._db_path = db_path
        self._init_db()

    def _init_db(self):
        with sqlite3.connect(self._db_path) as conn:
            conn.execute(_DDL)
            conn.commit()

    @staticmethod
    def _cache_key(apt_name: str, district_code: str) -> str:
        return f"{district_code}__{apt_name}"

    def get(self, apt_name: str, district_code: str) -> Optional[ApartmentMaster]:
        key = self._cache_key(apt_name, district_code)
        with sqlite3.connect(self._db_path) as conn:
            row = conn.execute(
                "SELECT complex_code, household_count, building_count, parking_count, "
                "constructor, approved_date, floor_area_ratio, building_coverage_ratio "
                "FROM apartment_master WHERE cache_key = ?",
                (key,),
            ).fetchone()
        if row is None:
            return None
        return ApartmentMaster(
            apt_name=apt_name,
            district_code=district_code,
            complex_code=row[0] or "",
            household_count=row[1] or 0,
            building_count=row[2] or 0,
            parking_count=row[3] or 0,
            constructor=row[4] or "",
            approved_date=row[5] or "",
            floor_area_ratio=row[6],
            building_coverage_ratio=row[7],
        )

    def save(self, master: ApartmentMaster) -> None:
        key = self._cache_key(master.apt_name, master.district_code)
        fetched_at = master.fetched_at or datetime.now(timezone.utc).isoformat()
        with sqlite3.connect(self._db_path) as conn:
            conn.execute(
                "INSERT OR REPLACE INTO apartment_master "
                "(cache_key, complex_code, household_count, building_count, parking_count, "
                "constructor, approved_date, floor_area_ratio, building_coverage_ratio, fetched_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    key,
                    master.complex_code,
                    master.household_count,
                    master.building_count,
                    master.parking_count,
                    master.constructor,
                    master.approved_date,
                    master.floor_area_ratio,
                    master.building_coverage_ratio,
                    fetched_at,
                ),
            )
            conn.commit()

    def get_all_complex_codes(self) -> List[str]:
        with sqlite3.connect(self._db_path) as conn:
            rows = conn.execute(
                "SELECT complex_code FROM apartment_master WHERE complex_code != ''"
            ).fetchall()
        return [r[0] for r in rows]

    def count(self) -> int:
        with sqlite3.connect(self._db_path) as conn:
            row = conn.execute("SELECT COUNT(*) FROM apartment_master").fetchone()
        return row[0] if row else 0
