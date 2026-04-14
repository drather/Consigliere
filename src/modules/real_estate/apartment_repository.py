"""
ApartmentRepository — real_estate.db / apartments 테이블 CRUD.

PK: complex_code (kaptCode).
기존 ApartmentMasterRepository(apartment_master.db)를 대체한다.
"""
import sqlite3
from typing import List, Optional

try:
    from modules.real_estate.models import ApartmentMaster
except ImportError:
    from src.modules.real_estate.models import ApartmentMaster

_DDL = """
CREATE TABLE IF NOT EXISTS apartments (
    complex_code     TEXT PRIMARY KEY,
    apt_name         TEXT NOT NULL,
    district_code    TEXT NOT NULL DEFAULT '',
    sido             TEXT NOT NULL DEFAULT '',
    sigungu          TEXT NOT NULL DEFAULT '',
    eupmyeondong     TEXT NOT NULL DEFAULT '',
    ri               TEXT NOT NULL DEFAULT '',
    road_address     TEXT NOT NULL DEFAULT '',
    legal_address    TEXT NOT NULL DEFAULT '',
    household_count  INTEGER NOT NULL DEFAULT 0,
    building_count   INTEGER NOT NULL DEFAULT 0,
    parking_count    INTEGER NOT NULL DEFAULT 0,
    constructor      TEXT NOT NULL DEFAULT '',
    developer        TEXT NOT NULL DEFAULT '',
    approved_date    TEXT NOT NULL DEFAULT '',
    top_floor        INTEGER NOT NULL DEFAULT 0,
    base_floor       INTEGER NOT NULL DEFAULT 0,
    total_area       REAL NOT NULL DEFAULT 0.0,
    heat_type        TEXT NOT NULL DEFAULT '',
    elevator_count   INTEGER NOT NULL DEFAULT 0,
    units_60         INTEGER NOT NULL DEFAULT 0,
    units_85         INTEGER NOT NULL DEFAULT 0,
    units_135        INTEGER NOT NULL DEFAULT 0,
    units_136_plus   INTEGER NOT NULL DEFAULT 0,
    fetched_at       TEXT NOT NULL DEFAULT ''
);
CREATE INDEX IF NOT EXISTS idx_apt_district  ON apartments(district_code);
CREATE INDEX IF NOT EXISTS idx_apt_sido      ON apartments(sido);
CREATE INDEX IF NOT EXISTS idx_apt_sigungu   ON apartments(sigungu);
CREATE INDEX IF NOT EXISTS idx_apt_name      ON apartments(apt_name);
"""

def _normalize_name(name: str) -> str:
    """아파트 이름 정규화: 공백 및 괄호 기호 제거, 내용 보존.

    저장 시 항상 적용하여 데이터 클렌징을 파이프라인에서 보장한다.
    예) "래미안 대치 팰리스" → "래미안대치팰리스"
        "경희궁자이1단지(임대아파트)" → "경희궁자이1단지임대아파트"
    """
    import re as _re
    n = name.strip()
    n = _re.sub(r"[()]", "", n)
    n = n.replace(" ", "")
    return n


_UPSERT_SQL = """
INSERT OR REPLACE INTO apartments (
    complex_code, apt_name, district_code,
    sido, sigungu, eupmyeondong, ri,
    road_address, legal_address,
    household_count, building_count, parking_count,
    constructor, developer, approved_date,
    top_floor, base_floor, total_area,
    heat_type, elevator_count,
    units_60, units_85, units_135, units_136_plus,
    fetched_at
) VALUES (
    :complex_code, :apt_name, :district_code,
    :sido, :sigungu, :eupmyeondong, :ri,
    :road_address, :legal_address,
    :household_count, :building_count, :parking_count,
    :constructor, :developer, :approved_date,
    :top_floor, :base_floor, :total_area,
    :heat_type, :elevator_count,
    :units_60, :units_85, :units_135, :units_136_plus,
    :fetched_at
)
"""


def _row_to_master(row: dict) -> ApartmentMaster:
    return ApartmentMaster(
        complex_code=row["complex_code"],
        apt_name=row["apt_name"],
        district_code=row["district_code"],
        sido=row["sido"],
        sigungu=row["sigungu"],
        eupmyeondong=row["eupmyeondong"],
        ri=row["ri"],
        road_address=row["road_address"],
        legal_address=row["legal_address"],
        household_count=row["household_count"],
        building_count=row["building_count"],
        parking_count=row["parking_count"],
        constructor=row["constructor"],
        developer=row["developer"],
        approved_date=row["approved_date"],
        top_floor=row["top_floor"],
        base_floor=row["base_floor"],
        total_area=row["total_area"],
        heat_type=row["heat_type"],
        elevator_count=row["elevator_count"],
        units_60=row["units_60"],
        units_85=row["units_85"],
        units_135=row["units_135"],
        units_136_plus=row["units_136_plus"],
        fetched_at=row["fetched_at"],
    )


class ApartmentRepository:
    """real_estate.db / apartments 테이블 접근 객체."""

    def __init__(self, db_path: str = "data/real_estate.db"):
        self._db_path = db_path
        # :memory: DB는 커넥션마다 새 DB → 단일 커넥션 고정
        if db_path == ":memory:":
            self._shared_conn: Optional[sqlite3.Connection] = sqlite3.connect(":memory:")
            self._shared_conn.row_factory = sqlite3.Row
        else:
            self._shared_conn = None
        self._init_db()

    def _conn(self) -> sqlite3.Connection:
        if self._shared_conn is not None:
            return self._shared_conn
        conn = sqlite3.connect(self._db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self):
        conn = self._conn()
        conn.executescript(_DDL)
        conn.commit()

    # ── CRUD ──────────────────────────────────────────────────────────────────

    def save(self, master: ApartmentMaster) -> None:
        with self._conn() as conn:
            conn.execute(_UPSERT_SQL, {
                "complex_code":   master.complex_code,
                "apt_name":       _normalize_name(master.apt_name),
                "district_code":  master.district_code,
                "sido":           master.sido,
                "sigungu":        master.sigungu,
                "eupmyeondong":   master.eupmyeondong,
                "ri":             master.ri,
                "road_address":   master.road_address,
                "legal_address":  master.legal_address,
                "household_count": master.household_count,
                "building_count": master.building_count,
                "parking_count":  master.parking_count,
                "constructor":    master.constructor,
                "developer":      master.developer,
                "approved_date":  master.approved_date,
                "top_floor":      master.top_floor,
                "base_floor":     master.base_floor,
                "total_area":     master.total_area,
                "heat_type":      master.heat_type,
                "elevator_count": master.elevator_count,
                "units_60":       master.units_60,
                "units_85":       master.units_85,
                "units_135":      master.units_135,
                "units_136_plus": master.units_136_plus,
                "fetched_at":     master.fetched_at,
            })

    def get(self, complex_code: str) -> Optional[ApartmentMaster]:
        with self._conn() as conn:
            row = conn.execute(
                "SELECT * FROM apartments WHERE complex_code = ?", (complex_code,)
            ).fetchone()
        return _row_to_master(row) if row else None

    def count(self) -> int:
        with self._conn() as conn:
            return conn.execute("SELECT COUNT(*) FROM apartments").fetchone()[0]

    def truncate(self) -> None:
        with self._conn() as conn:
            conn.execute("DELETE FROM apartments")

    # ── 검색 ──────────────────────────────────────────────────────────────────

    def search(
        self,
        apt_name: str = "",
        sido: str = "",
        sigungu: str = "",
        district_code: str = "",
        min_household: int = 0,
        max_household: int = 99999,
        constructor: str = "",
        approved_year_start: int = 1970,
        approved_year_end: int = 2030,
        limit: int = 500,
    ) -> List[ApartmentMaster]:
        clauses, params = [], []

        if apt_name:
            clauses.append("apt_name LIKE ?")
            params.append(f"%{apt_name}%")
        if sido:
            clauses.append("sido = ?")
            params.append(sido)
        if sigungu:
            clauses.append("sigungu = ?")
            params.append(sigungu)
        if district_code:
            clauses.append("district_code = ?")
            params.append(district_code)
        if min_household > 0:
            clauses.append("household_count >= ?")
            params.append(min_household)
        if max_household < 99999:
            clauses.append("household_count <= ?")
            params.append(max_household)
        if constructor:
            clauses.append("constructor LIKE ?")
            params.append(f"%{constructor}%")
        if approved_year_start > 1970:
            clauses.append("SUBSTR(approved_date, 1, 4) >= ?")
            params.append(str(approved_year_start))
        if approved_year_end < 2030:
            clauses.append("SUBSTR(approved_date, 1, 4) <= ?")
            params.append(str(approved_year_end))

        where = ("WHERE " + " AND ".join(clauses)) if clauses else ""
        sql = f"SELECT * FROM apartments {where} ORDER BY apt_name LIMIT ?"
        params.append(limit)

        with self._conn() as conn:
            rows = conn.execute(sql, params).fetchall()
        return [_row_to_master(r) for r in rows]

    # ── 필터 옵션 ─────────────────────────────────────────────────────────────

    def get_distinct_sidos(self) -> List[str]:
        with self._conn() as conn:
            rows = conn.execute(
                "SELECT DISTINCT sido FROM apartments WHERE sido != '' ORDER BY sido"
            ).fetchall()
        return [r[0] for r in rows]

    def get_distinct_sigungus(self, sido: str = "") -> List[str]:
        if sido:
            sql = "SELECT DISTINCT sigungu FROM apartments WHERE sido = ? AND sigungu != '' ORDER BY sigungu"
            params = (sido,)
        else:
            sql = "SELECT DISTINCT sigungu FROM apartments WHERE sigungu != '' ORDER BY sigungu"
            params = ()
        with self._conn() as conn:
            rows = conn.execute(sql, params).fetchall()
        return [r[0] for r in rows]

    def get_distinct_constructors(self) -> List[str]:
        with self._conn() as conn:
            rows = conn.execute(
                "SELECT DISTINCT constructor FROM apartments WHERE constructor != '' ORDER BY constructor"
            ).fetchall()
        return [r[0] for r in rows]

    def get_by_district(self, district_code: str) -> List[ApartmentMaster]:
        """지구코드 내 전체 단지 반환 (complex_code 해소용)."""
        with self._conn() as conn:
            rows = conn.execute(
                "SELECT * FROM apartments WHERE district_code = ?", (district_code,)
            ).fetchall()
        return [_row_to_master(r) for r in rows]
