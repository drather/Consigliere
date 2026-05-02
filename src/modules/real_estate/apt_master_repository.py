"""
AptMasterRepository — real_estate.db / apt_master 테이블 CRUD.

Transaction-First 아키텍처의 핵심 마스터 저장소.
실거래가에 등장한 모든 단지를 관리하며 apt_details(공동주택 기본정보)는 optional 조인.
"""
import sqlite3
from datetime import datetime, timezone
from typing import List, Optional

try:
    from modules.real_estate.models import AptMasterEntry
    from core.logger import get_logger
except ImportError:
    from src.modules.real_estate.models import AptMasterEntry
    from core.logger import get_logger

logger = get_logger(__name__)


_DDL = """
CREATE TABLE IF NOT EXISTS apt_master (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    apt_name      TEXT NOT NULL,
    district_code TEXT NOT NULL,
    sido          TEXT NOT NULL DEFAULT '',
    sigungu       TEXT NOT NULL DEFAULT '',
    complex_code  TEXT,
    tx_count      INTEGER DEFAULT 0,
    first_traded  TEXT,
    last_traded   TEXT,
    created_at    TEXT NOT NULL,
    UNIQUE(apt_name, district_code)
);
CREATE INDEX IF NOT EXISTS idx_am_district ON apt_master(district_code);
CREATE INDEX IF NOT EXISTS idx_am_sido     ON apt_master(sido);
CREATE INDEX IF NOT EXISTS idx_am_sigungu  ON apt_master(sigungu);
CREATE INDEX IF NOT EXISTS idx_am_name     ON apt_master(apt_name);
"""

# ON CONFLICT: tx_count/sido/sigungu 갱신, complex_code는 기존 값 보존(COALESCE)
_UPSERT_SQL = """
INSERT INTO apt_master
    (apt_name, district_code, sido, sigungu, complex_code, tx_count, first_traded, last_traded, created_at)
VALUES
    (:apt_name, :district_code, :sido, :sigungu, :complex_code,
     :tx_count, :first_traded, :last_traded, :created_at)
ON CONFLICT(apt_name, district_code) DO UPDATE SET
    sido         = excluded.sido,
    sigungu      = excluded.sigungu,
    complex_code = COALESCE(excluded.complex_code, apt_master.complex_code),
    tx_count     = excluded.tx_count,
    first_traded = excluded.first_traded,
    last_traded  = excluded.last_traded
"""

_MIGRATE_ADD_PNU_COLS = [
    "ALTER TABLE apt_master ADD COLUMN pnu TEXT",
    "ALTER TABLE apt_master ADD COLUMN mapping_score REAL",
]


def _row_to_entry(row: sqlite3.Row) -> AptMasterEntry:
    keys = row.keys()
    return AptMasterEntry(
        id=row["id"],
        apt_name=row["apt_name"],
        district_code=row["district_code"],
        sido=row["sido"],
        sigungu=row["sigungu"],
        complex_code=row["complex_code"],
        tx_count=row["tx_count"],
        first_traded=row["first_traded"],
        last_traded=row["last_traded"],
        created_at=row["created_at"],
        pnu=row["pnu"] if "pnu" in keys else None,
        mapping_score=row["mapping_score"] if "mapping_score" in keys else None,
        household_count=row["household_count"] if "household_count" in keys else None,
        road_address=row["road_address"] if "road_address" in keys else None,
        approved_date=row["approved_date"] if "approved_date" in keys else None,
    )


class AptMasterRepository:
    """real_estate.db / apt_master 테이블 접근 객체.

    Transaction-First 아키텍처: 실거래가에 등장한 모든 단지가 존재하며,
    공동주택 기본정보(apt_details)는 optional 조인으로 표시한다.
    """

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

    def _init_db(self) -> None:
        conn = self._conn()
        conn.executescript(_DDL)
        for sql in _MIGRATE_ADD_PNU_COLS:
            try:
                conn.execute(sql)
            except sqlite3.OperationalError:
                pass  # column already exists
        conn.commit()

    # ── CRUD ──────────────────────────────────────────────────────────────────

    def upsert(self, entry: AptMasterEntry) -> None:
        """신규 단지 삽입 또는 기존 단지 통계 갱신."""
        params = {
            "apt_name":      entry.apt_name,
            "district_code": entry.district_code,
            "sido":          entry.sido,
            "sigungu":       entry.sigungu,
            "complex_code":  entry.complex_code,
            "tx_count":      entry.tx_count,
            "first_traded":  entry.first_traded,
            "last_traded":   entry.last_traded,
            "created_at":    entry.created_at or datetime.now(timezone.utc).isoformat(),
        }
        with self._conn() as conn:
            conn.execute(_UPSERT_SQL, params)

    def get_by_id(self, entry_id: int) -> Optional[AptMasterEntry]:
        """PK로 단지 조회."""
        with self._conn() as conn:
            row = conn.execute(
                "SELECT * FROM apt_master WHERE id = ?", (entry_id,)
            ).fetchone()
        return _row_to_entry(row) if row else None

    def get_by_name_district(self, apt_name: str, district_code: str) -> Optional[AptMasterEntry]:
        """(apt_name, district_code) 정확 조회."""
        with self._conn() as conn:
            row = conn.execute(
                "SELECT * FROM apt_master WHERE apt_name = ? AND district_code = ?",
                (apt_name, district_code),
            ).fetchone()
        return _row_to_entry(row) if row else None

    def count(self) -> int:
        """저장된 단지 수 반환."""
        with self._conn() as conn:
            return conn.execute("SELECT COUNT(*) FROM apt_master").fetchone()[0]

    # ── 검색 ──────────────────────────────────────────────────────────────────

    def search(
        self,
        apt_name: str = "",
        sido: str = "",
        sigungu: str = "",
        min_household_count: int = 0,
        limit: int = 500,
    ) -> List[AptMasterEntry]:
        """apt_name(부분일치) / sido / sigungu 필터 검색.

        min_household_count > 0이면 apartments 테이블 LEFT JOIN으로 세대수 필터링.
        apartments 매핑이 없는 단지(complex_code=None 또는 apartments 미매핑)는 필터 적용 시 제외된다.
        apartments 테이블이 없는 환경에서는 JOIN 없이 fallback (필터 미적용, 경고 로그 발생).
        """
        clauses: list = []
        params: list = []

        if apt_name:
            clauses.append("am.apt_name LIKE ?")
            params.append(f"%{apt_name}%")
        if sido:
            clauses.append("am.sido = ?")
            params.append(sido)
        if sigungu:
            clauses.append("am.sigungu = ?")
            params.append(sigungu)
        if min_household_count > 0:
            clauses.append("a.household_count >= ?")
            params.append(min_household_count)

        where = ("WHERE " + " AND ".join(clauses)) if clauses else ""
        order = "ORDER BY COALESCE(a.household_count, 0) DESC" if min_household_count > 0 else "ORDER BY am.apt_name"
        sql = (
            f"SELECT am.*, a.household_count, a.road_address, a.approved_date "
            f"FROM apt_master am "
            f"LEFT JOIN apartments a ON am.complex_code = a.complex_code "
            f"{where} {order} LIMIT ?"
        )
        params.append(limit)

        try:
            with self._conn() as conn:
                rows = conn.execute(sql, params).fetchall()
            return [_row_to_entry(r) for r in rows]
        except sqlite3.OperationalError as e:
            if "no such table" not in str(e):
                raise
            # apartments 테이블이 없는 환경 fallback — JOIN 없이 재시도
            if min_household_count > 0:
                logger.warning(
                    "[AptMasterRepository] apartments 테이블 없음 — min_household_count=%d 필터 미적용",
                    min_household_count,
                )
            plain_clauses: list = []
            plain_params: list = []
            if apt_name:
                plain_clauses.append("apt_name LIKE ?")
                plain_params.append(f"%{apt_name}%")
            if sido:
                plain_clauses.append("sido = ?")
                plain_params.append(sido)
            if sigungu:
                plain_clauses.append("sigungu = ?")
                plain_params.append(sigungu)
            plain_where = ("WHERE " + " AND ".join(plain_clauses)) if plain_clauses else ""
            plain_sql = f"SELECT * FROM apt_master {plain_where} ORDER BY apt_name LIMIT ?"
            plain_params.append(limit)
            with self._conn() as conn:
                rows = conn.execute(plain_sql, plain_params).fetchall()
            return [_row_to_entry(r) for r in rows]

    # ── 필터 옵션 ─────────────────────────────────────────────────────────────

    def get_distinct_sidos(self) -> List[str]:
        """시도 목록 조회 (드롭다운용)."""
        with self._conn() as conn:
            rows = conn.execute(
                "SELECT DISTINCT sido FROM apt_master WHERE sido != '' ORDER BY sido"
            ).fetchall()
        return [r[0] for r in rows]

    def get_distinct_sigungus(self, sido: str = "") -> List[str]:
        """시군구 목록 조회. sido 지정 시 해당 시도만 반환."""
        if sido:
            sql = ("SELECT DISTINCT sigungu FROM apt_master "
                   "WHERE sido = ? AND sigungu != '' ORDER BY sigungu")
            params: tuple = (sido,)
        else:
            sql = ("SELECT DISTINCT sigungu FROM apt_master "
                   "WHERE sigungu != '' ORDER BY sigungu")
            params = ()
        with self._conn() as conn:
            rows = conn.execute(sql, params).fetchall()
        return [r[0] for r in rows]

    # ── 빌드 / 마이그레이션 헬퍼 ──────────────────────────────────────────────

    def build_from_transactions(self, details_table: str = "apartments") -> int:
        """transactions 테이블에서 apt_master를 초기 구축한다.

        Args:
            details_table: sido/sigungu를 가져올 상세정보 테이블명
                           (마이그레이션 전: 'apartments', 이후: 'apt_details')

        Returns:
            신규 삽입된 단지 수 (이미 존재하는 단지는 제외)
        """
        # Step 1: transactions → apt_master 집계 삽입
        # details_table이 없으면 sido/sigungu를 빈 문자열로 처리
        try:
            insert_sql = f"""
            INSERT OR IGNORE INTO apt_master
                (apt_name, district_code, sido, sigungu, tx_count, first_traded, last_traded, created_at)
            SELECT
                t.apt_name,
                t.district_code,
                COALESCE(a.sido, '')     AS sido,
                COALESCE(a.sigungu, '')  AS sigungu,
                COUNT(*)                 AS tx_count,
                MIN(t.deal_date)         AS first_traded,
                MAX(t.deal_date)         AS last_traded,
                datetime('now')          AS created_at
            FROM transactions t
            LEFT JOIN {details_table} a ON t.complex_code = a.complex_code
            GROUP BY t.apt_name, t.district_code
            """
            with self._conn() as conn:
                before = conn.execute("SELECT COUNT(*) FROM apt_master").fetchone()[0]
                conn.execute(insert_sql)
                after = conn.execute("SELECT COUNT(*) FROM apt_master").fetchone()[0]
        except Exception:
            # details_table이 없거나 JOIN 실패 시 sido/sigungu 없이 삽입
            insert_sql_plain = """
            INSERT OR IGNORE INTO apt_master
                (apt_name, district_code, sido, sigungu, tx_count, first_traded, last_traded, created_at)
            SELECT
                apt_name,
                district_code,
                '',
                '',
                COUNT(*),
                MIN(deal_date),
                MAX(deal_date),
                datetime('now')
            FROM transactions
            GROUP BY apt_name, district_code
            """
            with self._conn() as conn:
                before = conn.execute("SELECT COUNT(*) FROM apt_master").fetchone()[0]
                conn.execute(insert_sql_plain)
                after = conn.execute("SELECT COUNT(*) FROM apt_master").fetchone()[0]

        # Step 2: transactions에 complex_code가 있으면 apt_master.complex_code 채우기
        fill_sql = """
        UPDATE apt_master SET complex_code = (
            SELECT complex_code FROM transactions
            WHERE apt_name  = apt_master.apt_name
              AND district_code = apt_master.district_code
              AND complex_code IS NOT NULL
            LIMIT 1
        )
        WHERE complex_code IS NULL
        """
        with self._conn() as conn:
            conn.execute(fill_sql)

        return after - before

    def sync_from_new_transactions(self, transactions: list) -> int:
        """신규 수집된 거래 목록을 apt_master에 동기화한다.

        save_batch() 이후에 호출 — transactions 테이블에 이미 저장된 데이터를 기준으로 집계.
        - 신규 단지: INSERT
        - 기존 단지: tx_count / first_traded / last_traded 갱신
                     complex_code는 COALESCE 보존 (기존 값 우선)

        Args:
            transactions: 방금 수집된 RealEstateTransaction 목록 (정규화 전 원본)

        Returns:
            신규 삽입된 단지 수
        """
        if not transactions:
            return 0

        import re as _re

        def _norm(name: str) -> str:
            """TransactionRepository._normalize_name과 동일한 정규화."""
            n = name.strip()
            n = _re.sub(r"[()]", "", n)
            return n.replace(" ", "")

        # transactions 테이블에 저장된 정규화 이름 기준으로 페어 구성
        pairs = list({(_norm(tx.apt_name), tx.district_code) for tx in transactions})
        now = datetime.now(timezone.utc).isoformat()

        values_clause = ", ".join("(?, ?)" for _ in pairs)
        flat_pairs = [v for p in pairs for v in p]

        try:
            upsert_sql = f"""
            INSERT INTO apt_master
                (apt_name, district_code, sido, sigungu, complex_code,
                 tx_count, first_traded, last_traded, created_at)
            SELECT
                t.apt_name,
                t.district_code,
                COALESCE(MAX(a.sido),    '') AS sido,
                COALESCE(MAX(a.sigungu), '') AS sigungu,
                MAX(t.complex_code)          AS complex_code,
                COUNT(*)                     AS tx_count,
                MIN(t.deal_date)             AS first_traded,
                MAX(t.deal_date)             AS last_traded,
                ?                            AS created_at
            FROM transactions t
            LEFT JOIN apartments a ON t.complex_code = a.complex_code
            WHERE (t.apt_name, t.district_code) IN (VALUES {values_clause})
            GROUP BY t.apt_name, t.district_code
            ON CONFLICT(apt_name, district_code) DO UPDATE SET
                tx_count     = excluded.tx_count,
                first_traded = excluded.first_traded,
                last_traded  = excluded.last_traded,
                complex_code = COALESCE(excluded.complex_code, apt_master.complex_code),
                sido    = CASE WHEN excluded.sido    != '' THEN excluded.sido    ELSE apt_master.sido    END,
                sigungu = CASE WHEN excluded.sigungu != '' THEN excluded.sigungu ELSE apt_master.sigungu END
            """
            with self._conn() as conn:
                before = conn.execute("SELECT COUNT(*) FROM apt_master").fetchone()[0]
                conn.execute(upsert_sql, [now] + flat_pairs)
                after = conn.execute("SELECT COUNT(*) FROM apt_master").fetchone()[0]
        except Exception:
            # apartments 테이블이 없는 환경 (테스트 등) fallback
            upsert_sql_plain = f"""
            INSERT INTO apt_master
                (apt_name, district_code, sido, sigungu, complex_code,
                 tx_count, first_traded, last_traded, created_at)
            SELECT
                apt_name, district_code, '', '',
                MAX(complex_code) AS complex_code,
                COUNT(*)          AS tx_count,
                MIN(deal_date)    AS first_traded,
                MAX(deal_date)    AS last_traded,
                ?                 AS created_at
            FROM transactions
            WHERE (apt_name, district_code) IN (VALUES {values_clause})
            GROUP BY apt_name, district_code
            ON CONFLICT(apt_name, district_code) DO UPDATE SET
                tx_count     = excluded.tx_count,
                first_traded = excluded.first_traded,
                last_traded  = excluded.last_traded,
                complex_code = COALESCE(excluded.complex_code, apt_master.complex_code)
            """
            with self._conn() as conn:
                before = conn.execute("SELECT COUNT(*) FROM apt_master").fetchone()[0]
                conn.execute(upsert_sql_plain, [now] + flat_pairs)
                after = conn.execute("SELECT COUNT(*) FROM apt_master").fetchone()[0]

        return after - before

    def refresh_stats(self) -> None:
        """모든 단지의 tx_count/first_traded/last_traded를 transactions 기준으로 재계산."""
        sql = """
        UPDATE apt_master SET
            tx_count     = (
                SELECT COUNT(*) FROM transactions t
                WHERE t.apt_name      = apt_master.apt_name
                  AND t.district_code = apt_master.district_code
            ),
            first_traded = (
                SELECT MIN(deal_date) FROM transactions t
                WHERE t.apt_name      = apt_master.apt_name
                  AND t.district_code = apt_master.district_code
            ),
            last_traded  = (
                SELECT MAX(deal_date) FROM transactions t
                WHERE t.apt_name      = apt_master.apt_name
                  AND t.district_code = apt_master.district_code
            )
        """
        with self._conn() as conn:
            conn.execute(sql)

    def update_building_mapping(
        self, apt_id: int, mgm_pk: str, score: float
    ) -> None:
        with self._conn() as conn:
            conn.execute(
                "UPDATE apt_master SET pnu = ?, mapping_score = ? WHERE id = ?",
                (mgm_pk, score, apt_id),
            )

    def get_all_for_mapping(self) -> List[AptMasterEntry]:
        """Returns all apt_master rows where pnu IS NULL (unmapped entries)."""
        with self._conn() as conn:
            rows = conn.execute(
                "SELECT * FROM apt_master WHERE pnu IS NULL"
            ).fetchall()
        return [_row_to_entry(r) for r in rows]

    def get_apt_addresses_by_complex(self) -> dict:
        """apartments 테이블에서 complex_code → road_address 매핑 반환."""
        try:
            with self._conn() as conn:
                rows = conn.execute(
                    "SELECT complex_code, road_address FROM apartments "
                    "WHERE complex_code IS NOT NULL AND road_address != ''"
                ).fetchall()
            return {r[0]: r[1] for r in rows}
        except sqlite3.OperationalError:
            return {}
