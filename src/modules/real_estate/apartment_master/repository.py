"""
ApartmentMasterRepository — SQLite CRUD for apartment master data.

스키마: cache_key = f"{district_code}__{apt_name}"
마이그레이션: _init_db()가 신규 컬럼을 자동으로 ALTER TABLE 추가 (기존 DB 보존)
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
    road_address        TEXT DEFAULT '',
    legal_address       TEXT DEFAULT '',
    top_floor           INTEGER DEFAULT 0,
    base_floor          INTEGER DEFAULT 0,
    total_area          REAL DEFAULT 0.0,
    heat_type           TEXT DEFAULT '',
    developer           TEXT DEFAULT '',
    elevator_count      INTEGER DEFAULT 0,
    units_60            INTEGER DEFAULT 0,
    units_85            INTEGER DEFAULT 0,
    units_135           INTEGER DEFAULT 0,
    units_136_plus      INTEGER DEFAULT 0,
    sido                TEXT DEFAULT '',
    sigungu             TEXT DEFAULT '',
    eupmyeondong        TEXT DEFAULT '',
    ri                  TEXT DEFAULT '',
    fetched_at          TEXT
)
"""

# 기존 DB에 없을 수 있는 신규 컬럼 목록 (컬럼명, 타입, 기본값)
_NEW_COLUMNS = [
    ("road_address",  "TEXT",    "''"),
    ("legal_address", "TEXT",    "''"),
    ("top_floor",     "INTEGER", "0"),
    ("base_floor",    "INTEGER", "0"),
    ("total_area",    "REAL",    "0.0"),
    ("heat_type",     "TEXT",    "''"),
    ("developer",     "TEXT",    "''"),
    ("elevator_count","INTEGER", "0"),
    ("units_60",      "INTEGER", "0"),
    ("units_85",      "INTEGER", "0"),
    ("units_135",     "INTEGER", "0"),
    ("units_136_plus","INTEGER", "0"),
    ("sido",          "TEXT",    "''"),
    ("sigungu",       "TEXT",    "''"),
    ("eupmyeondong",  "TEXT",    "''"),
    ("ri",            "TEXT",    "''"),
]


class ApartmentMasterRepository:
    def __init__(self, db_path: str = "data/apartment_master.db"):
        self._db_path = db_path
        self._init_db()

    def _init_db(self):
        with sqlite3.connect(self._db_path) as conn:
            conn.execute(_DDL)
            conn.commit()
            # 기존 DB 마이그레이션: 신규 컬럼이 없으면 추가
            self._migrate(conn)

    def _migrate(self, conn: sqlite3.Connection) -> None:
        """기존 DB에 신규 컬럼이 없으면 ALTER TABLE로 추가한다."""
        existing = {row[1] for row in conn.execute("PRAGMA table_info(apartment_master)").fetchall()}
        for col_name, col_type, default in _NEW_COLUMNS:
            if col_name not in existing:
                conn.execute(
                    f"ALTER TABLE apartment_master ADD COLUMN {col_name} {col_type} DEFAULT {default}"
                )
        conn.commit()

    @staticmethod
    def _cache_key(apt_name: str, district_code: str) -> str:
        return f"{district_code}__{apt_name}"

    def get(self, apt_name: str, district_code: str) -> Optional[ApartmentMaster]:
        key = self._cache_key(apt_name, district_code)
        with sqlite3.connect(self._db_path) as conn:
            row = conn.execute(
                "SELECT complex_code, household_count, building_count, parking_count, "
                "constructor, approved_date, "
                "road_address, legal_address, top_floor, base_floor, total_area, "
                "heat_type, developer, elevator_count, "
                "units_60, units_85, units_135, units_136_plus, "
                "sido, sigungu, eupmyeondong, ri "
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
            road_address=row[6] or "",
            legal_address=row[7] or "",
            top_floor=row[8] or 0,
            base_floor=row[9] or 0,
            total_area=row[10] or 0.0,
            heat_type=row[11] or "",
            developer=row[12] or "",
            elevator_count=row[13] or 0,
            units_60=row[14] or 0,
            units_85=row[15] or 0,
            units_135=row[16] or 0,
            units_136_plus=row[17] or 0,
            sido=row[18] or "",
            sigungu=row[19] or "",
            eupmyeondong=row[20] or "",
            ri=row[21] or "",
        )

    def save(self, master: ApartmentMaster) -> None:
        key = self._cache_key(master.apt_name, master.district_code)
        fetched_at = master.fetched_at or datetime.now(timezone.utc).isoformat()
        with sqlite3.connect(self._db_path) as conn:
            conn.execute(
                "INSERT OR REPLACE INTO apartment_master "
                "(cache_key, complex_code, household_count, building_count, parking_count, "
                "constructor, approved_date, "
                "road_address, legal_address, top_floor, base_floor, total_area, "
                "heat_type, developer, elevator_count, "
                "units_60, units_85, units_135, units_136_plus, "
                "sido, sigungu, eupmyeondong, ri, fetched_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    key,
                    master.complex_code,
                    master.household_count,
                    master.building_count,
                    master.parking_count,
                    master.constructor,
                    master.approved_date,
                    master.road_address,
                    master.legal_address,
                    master.top_floor,
                    master.base_floor,
                    master.total_area,
                    master.heat_type,
                    master.developer,
                    master.elevator_count,
                    master.units_60,
                    master.units_85,
                    master.units_135,
                    master.units_136_plus,
                    master.sido,
                    master.sigungu,
                    master.eupmyeondong,
                    master.ri,
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
        sido: str = "",
        sigungu: str = "",
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
            district_code: 시군구코드 prefix 매칭 (빈 문자열이면 무시)
            sido: 시도 완전일치 (빈 문자열이면 무시, 예: 서울특별시)
            sigungu: 시군구 완전일치 (빈 문자열이면 무시, 예: 강남구)
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
        if sido:
            conditions.append("sido = ?")
            params.append(sido)
        if sigungu:
            conditions.append("sigungu = ?")
            params.append(sigungu)
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
            f"constructor, approved_date, "
            f"road_address, legal_address, top_floor, base_floor, total_area, "
            f"heat_type, developer, elevator_count, "
            f"units_60, units_85, units_135, units_136_plus, "
            f"sido, sigungu, eupmyeondong, ri "
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
                road_address=row[7] or "",
                legal_address=row[8] or "",
                top_floor=row[9] or 0,
                base_floor=row[10] or 0,
                total_area=row[11] or 0.0,
                heat_type=row[12] or "",
                developer=row[13] or "",
                elevator_count=row[14] or 0,
                units_60=row[15] or 0,
                units_85=row[16] or 0,
                units_135=row[17] or 0,
                units_136_plus=row[18] or 0,
                sido=row[19] or "",
                sigungu=row[20] or "",
                eupmyeondong=row[21] or "",
                ri=row[22] or "",
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

    def truncate(self) -> None:
        """모든 레코드를 삭제한다 (재구축용)."""
        with sqlite3.connect(self._db_path) as conn:
            conn.execute("DELETE FROM apartment_master")
            conn.commit()

    def get_distinct_sidos(self) -> List[str]:
        """시도 드롭다운용 목록 반환."""
        with sqlite3.connect(self._db_path) as conn:
            rows = conn.execute(
                "SELECT DISTINCT sido FROM apartment_master "
                "WHERE sido != '' ORDER BY sido"
            ).fetchall()
        return [r[0] for r in rows]

    def get_distinct_sigungus(self, sido: str = "") -> List[str]:
        """시군구 드롭다운용 목록 반환. sido 지정 시 해당 시도 내 시군구만 반환."""
        with sqlite3.connect(self._db_path) as conn:
            if sido:
                rows = conn.execute(
                    "SELECT DISTINCT sigungu FROM apartment_master "
                    "WHERE sigungu != '' AND sido = ? ORDER BY sigungu",
                    (sido,),
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT DISTINCT sigungu FROM apartment_master "
                    "WHERE sigungu != '' ORDER BY sigungu"
                ).fetchall()
        return [r[0] for r in rows]
