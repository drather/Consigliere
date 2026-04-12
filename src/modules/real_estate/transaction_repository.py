"""
TransactionRepository — real_estate.db / transactions 테이블 CRUD.

complex_code(FK) 자동 해소 포함.
기존 ChromaDB 거래 저장을 대체한다.
"""
import sqlite3
from datetime import date
from typing import List, Optional, TYPE_CHECKING

try:
    from modules.real_estate.models import RealEstateTransaction
except ImportError:
    from src.modules.real_estate.models import RealEstateTransaction

if TYPE_CHECKING:
    try:
        from modules.real_estate.apartment_repository import ApartmentRepository
    except ImportError:
        from src.modules.real_estate.apartment_repository import ApartmentRepository

_DDL = """
CREATE TABLE IF NOT EXISTS transactions (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    complex_code   TEXT,
    apt_name       TEXT NOT NULL,
    district_code  TEXT NOT NULL,
    deal_date      TEXT NOT NULL,
    price          INTEGER NOT NULL,
    floor          INTEGER NOT NULL DEFAULT 0,
    exclusive_area REAL NOT NULL DEFAULT 0.0,
    build_year     INTEGER NOT NULL DEFAULT 0,
    road_name      TEXT NOT NULL DEFAULT '',
    FOREIGN KEY (complex_code) REFERENCES apartments(complex_code)
);
CREATE INDEX IF NOT EXISTS idx_tx_complex  ON transactions(complex_code);
CREATE INDEX IF NOT EXISTS idx_tx_district ON transactions(district_code);
CREATE INDEX IF NOT EXISTS idx_tx_date     ON transactions(deal_date);
CREATE UNIQUE INDEX IF NOT EXISTS idx_tx_dedup
    ON transactions(district_code, apt_name, deal_date, floor, price);
"""

_INSERT_SQL = """
INSERT OR IGNORE INTO transactions
    (complex_code, apt_name, district_code, deal_date, price, floor, exclusive_area, build_year, road_name)
VALUES
    (:complex_code, :apt_name, :district_code, :deal_date, :price, :floor, :exclusive_area, :build_year, :road_name)
"""


def _row_to_tx(row: sqlite3.Row) -> RealEstateTransaction:
    return RealEstateTransaction(
        apt_name=row["apt_name"],
        district_code=row["district_code"],
        deal_date=row["deal_date"],
        price=row["price"],
        floor=row["floor"],
        exclusive_area=row["exclusive_area"],
        build_year=row["build_year"],
        road_name=row["road_name"],
        complex_code=row["complex_code"],
    )


def _tx_to_params(tx: RealEstateTransaction) -> dict:
    return {
        "complex_code":   tx.complex_code,
        "apt_name":       tx.apt_name,
        "district_code":  tx.district_code,
        "deal_date":      str(tx.deal_date),
        "price":          tx.price,
        "floor":          tx.floor,
        "exclusive_area": tx.exclusive_area,
        "build_year":     tx.build_year,
        "road_name":      tx.road_name or "",
    }


class TransactionRepository:
    """real_estate.db / transactions 테이블 접근 객체."""

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

    def save(self, tx: RealEstateTransaction) -> None:
        with self._conn() as conn:
            conn.execute(_INSERT_SQL, _tx_to_params(tx))

    def save_batch(self, txs: List[RealEstateTransaction]) -> int:
        """중복 제거 후 일괄 저장. 저장된 건수 반환."""
        seen, unique = set(), []
        for tx in txs:
            key = tx.dedup_key()
            if key not in seen:
                seen.add(key)
                unique.append(tx)

        if not unique:
            return 0

        with self._conn() as conn:
            before = conn.execute("SELECT COUNT(*) FROM transactions").fetchone()[0]
            conn.executemany(_INSERT_SQL, [_tx_to_params(t) for t in unique])
            after = conn.execute("SELECT COUNT(*) FROM transactions").fetchone()[0]
        return after - before

    # ── 조회 ──────────────────────────────────────────────────────────────────

    def get_by_complex(
        self,
        complex_code: str,
        limit: int = 50,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
    ) -> List[RealEstateTransaction]:
        """단지 코드로 조회 (최신순). 단지 상세 패널용."""
        clauses = ["complex_code = ?"]
        params: list = [complex_code]
        if date_from:
            clauses.append("deal_date >= ?")
            params.append(date_from)
        if date_to:
            clauses.append("deal_date <= ?")
            params.append(date_to)
        params.append(limit)
        sql = f"SELECT * FROM transactions WHERE {' AND '.join(clauses)} ORDER BY deal_date DESC LIMIT ?"
        with self._conn() as conn:
            rows = conn.execute(sql, params).fetchall()
        return [_row_to_tx(r) for r in rows]

    def get_by_district(
        self,
        district_code: str,
        limit: int = 500,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
    ) -> List[RealEstateTransaction]:
        """지구코드로 조회 (최신순). 모니터·지도용."""
        clauses = ["district_code = ?"]
        params: list = [district_code]
        if date_from:
            clauses.append("deal_date >= ?")
            params.append(date_from)
        if date_to:
            clauses.append("deal_date <= ?")
            params.append(date_to)
        params.append(limit)
        sql = f"SELECT * FROM transactions WHERE {' AND '.join(clauses)} ORDER BY deal_date DESC LIMIT ?"
        with self._conn() as conn:
            rows = conn.execute(sql, params).fetchall()
        return [_row_to_tx(r) for r in rows]

    def get_by_districts(
        self,
        district_codes: List[str],
        limit: int = 2000,
    ) -> List[RealEstateTransaction]:
        """복수 지구코드로 조회 (지도 뷰용)."""
        if not district_codes:
            return []
        placeholders = ",".join("?" * len(district_codes))
        sql = (
            f"SELECT * FROM transactions WHERE district_code IN ({placeholders})"
            f" ORDER BY deal_date DESC LIMIT ?"
        )
        with self._conn() as conn:
            rows = conn.execute(sql, [*district_codes, limit]).fetchall()
        return [_row_to_tx(r) for r in rows]

    def get_all(self, limit: int = 500, offset: int = 0) -> List[RealEstateTransaction]:
        """전체 조회 (모니터 대시보드용)."""
        with self._conn() as conn:
            rows = conn.execute(
                "SELECT * FROM transactions ORDER BY deal_date DESC LIMIT ? OFFSET ?",
                (limit, offset),
            ).fetchall()
        return [_row_to_tx(r) for r in rows]

    # ── 유지보수 ───────────────────────────────────────────────────────────────

    def delete_before(self, cutoff: date) -> int:
        """cutoff 이전 거래 삭제. 삭제 건수 반환."""
        with self._conn() as conn:
            cur = conn.execute(
                "DELETE FROM transactions WHERE deal_date < ?", (cutoff.isoformat(),)
            )
        return cur.rowcount

    @staticmethod
    def _name_fuzzy_match(tx_nm: str, apt_nm: str) -> bool:
        """아파트명 fuzzy 매칭.

        1차: 양방향 substring (기존)
        2차: 짧은 이름의 끝 4자 이상이 긴 이름에 포함 (suffix 매칭)
             예) 래미안하이베르  vs  래미안신당하이베르 → '하이베르'(4) 공통 → True
        """
        if tx_nm in apt_nm or apt_nm in tx_nm:
            return True
        shorter, longer = (tx_nm, apt_nm) if len(tx_nm) <= len(apt_nm) else (apt_nm, tx_nm)
        if len(shorter) < 4:
            return False
        for suffix_len in range(4, len(shorter) + 1):
            if shorter[-suffix_len:] in longer:
                return True
        return False

    def resolve_complex_codes(self, apt_repo: "ApartmentRepository") -> int:
        """complex_code가 NULL인 거래를 apt_repo 기준으로 fuzzy 매칭하여 채움.

        매칭 규칙: 같은 district_code 내에서 _name_fuzzy_match() 통과 시 매칭.
        반환: 해소된 건수
        """
        with self._conn() as conn:
            null_rows = conn.execute(
                "SELECT id, apt_name, district_code FROM transactions WHERE complex_code IS NULL"
            ).fetchall()

        if not null_rows:
            return 0

        # district별 master 목록 캐시
        district_cache: dict = {}
        resolved = 0

        with self._conn() as conn:
            for row in null_rows:
                dc = row["district_code"]
                if dc not in district_cache:
                    district_cache[dc] = apt_repo.get_by_district(dc)

                masters = district_cache[dc]
                tx_nm = row["apt_name"].strip().lower()

                matched = None
                for m in masters:
                    apt_nm = m.apt_name.strip().lower()
                    if self._name_fuzzy_match(tx_nm, apt_nm):
                        matched = m.complex_code
                        break

                if matched:
                    conn.execute(
                        "UPDATE transactions SET complex_code = ? WHERE id = ?",
                        (matched, row["id"]),
                    )
                    resolved += 1

        return resolved
