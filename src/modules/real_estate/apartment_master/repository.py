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

    def search(
        self,
        apt_name: str = "",
        district_code: str = "",
        min_household: int = 0,
        max_household: int = 99999,
        constructor: str = "",
        approved_year_start: int = 1970,
        approved_year_end: int = 2030,
        limit: int = 500,
    ) -> List[ApartmentMaster]:
        """동적 필터로 마스터 DB를 검색한다.

        Args:
            apt_name: 아파트명 부분일치 (빈 문자열이면 무시)
            district_code: 정확일치 (빈 문자열이면 무시)
            min_household: 최소 세대수 (0이면 무시)
            max_household: 최대 세대수 (99999이면 무시)
            constructor: 건설사 부분일치 (빈 문자열이면 무시)
            approved_year_start: 준공연도 시작 (approved_date 앞 4자리 기준)
            approved_year_end: 준공연도 종료
            limit: 최대 결과 건수 (기본 500)
        """
        conditions = []
        params: list = []

        if apt_name:
            conditions.append("cache_key LIKE ?")
            params.append(f"%{apt_name}%")
        if district_code:
            conditions.append("cache_key LIKE ?")
            params.append(f"{district_code}__%")
        if min_household > 0:
            conditions.append("household_count >= ?")
            params.append(min_household)
        if max_household < 99999:
            conditions.append("household_count <= ?")
            params.append(max_household)
        if constructor:
            conditions.append("constructor LIKE ?")
            params.append(f"%{constructor}%")
        if approved_year_start > 1970 or approved_year_end < 2030:
            conditions.append("SUBSTR(approved_date, 1, 4) BETWEEN ? AND ?")
            params.append(str(approved_year_start))
            params.append(str(approved_year_end))

        where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""
        sql = (
            f"SELECT cache_key, complex_code, household_count, building_count, parking_count, "
            f"constructor, approved_date, floor_area_ratio, building_coverage_ratio "
            f"FROM apartment_master {where_clause} LIMIT ?"
        )
        params.append(limit)

        with sqlite3.connect(self._db_path) as conn:
            rows = conn.execute(sql, params).fetchall()

        results = []
        for row in rows:
            cache_key = row[0]
            parts = cache_key.split("__", 1)
            d_code = parts[0] if len(parts) == 2 else ""
            a_name = parts[1] if len(parts) == 2 else cache_key
            results.append(ApartmentMaster(
                apt_name=a_name,
                district_code=d_code,
                complex_code=row[1] or "",
                household_count=row[2] or 0,
                building_count=row[3] or 0,
                parking_count=row[4] or 0,
                constructor=row[5] or "",
                approved_date=row[6] or "",
                floor_area_ratio=row[7],
                building_coverage_ratio=row[8],
            ))
        return results

    def get_distinct_constructors(self) -> List[str]:
        """건설사 드롭다운용 중복 없는 건설사 목록 반환."""
        with sqlite3.connect(self._db_path) as conn:
            rows = conn.execute(
                "SELECT DISTINCT constructor FROM apartment_master "
                "WHERE constructor != '' ORDER BY constructor"
            ).fetchall()
        return [r[0] for r in rows]
