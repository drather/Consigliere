import sqlite3
from typing import List, Optional
from .models import MacroIndicatorDef, MacroRecord

_DDL = """
CREATE TABLE IF NOT EXISTS macro_indicator_definitions (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    code                TEXT NOT NULL,
    item_code           TEXT NOT NULL,
    name                TEXT NOT NULL,
    unit                TEXT NOT NULL,
    frequency           TEXT NOT NULL,
    collect_every_days  INTEGER NOT NULL,
    domain              TEXT NOT NULL,
    category            TEXT NOT NULL,
    is_active           INTEGER DEFAULT 1,
    last_collected_at   TEXT,
    created_at          TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS macro_records (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    indicator_id    INTEGER NOT NULL REFERENCES macro_indicator_definitions(id),
    period          TEXT NOT NULL,
    value           REAL NOT NULL,
    collected_at    TEXT NOT NULL,
    UNIQUE(indicator_id, period, collected_at)
);

CREATE INDEX IF NOT EXISTS idx_mr_ind_period ON macro_records(indicator_id, period);
CREATE INDEX IF NOT EXISTS idx_mr_collected  ON macro_records(collected_at);
CREATE INDEX IF NOT EXISTS idx_mid_domain    ON macro_indicator_definitions(domain);
CREATE INDEX IF NOT EXISTS idx_mid_active    ON macro_indicator_definitions(is_active);
"""


class MacroRepository:
    def __init__(self, db_path: str = "data/macro.db"):
        self.db_path = db_path
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self):
        with self._connect() as conn:
            conn.executescript(_DDL)

    # ── Indicator Definitions ────────────────────────────────────

    def insert_indicator(self, ind: MacroIndicatorDef) -> int:
        sql = """
        INSERT INTO macro_indicator_definitions
            (code, item_code, name, unit, frequency, collect_every_days,
             domain, category, is_active, last_collected_at, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        with self._connect() as conn:
            cur = conn.execute(sql, (
                ind.code, ind.item_code, ind.name, ind.unit, ind.frequency,
                ind.collect_every_days, ind.domain, ind.category,
                1 if ind.is_active else 0,
                ind.last_collected_at, ind.created_at,
            ))
            return cur.lastrowid

    def get_active_indicators(self, domain: Optional[str] = None) -> List[MacroIndicatorDef]:
        sql = "SELECT * FROM macro_indicator_definitions WHERE is_active = 1"
        params: list = []
        if domain:
            sql += " AND (domain = ? OR domain = 'common')"
            params.append(domain)
        with self._connect() as conn:
            rows = conn.execute(sql, params).fetchall()
        return [_row_to_def(r) for r in rows]

    def get_indicator_by_id(self, indicator_id: int) -> Optional[MacroIndicatorDef]:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM macro_indicator_definitions WHERE id = ?", (indicator_id,)
            ).fetchone()
        return _row_to_def(row) if row else None

    def update_last_collected(self, indicator_id: int, collected_at: str):
        with self._connect() as conn:
            conn.execute(
                "UPDATE macro_indicator_definitions SET last_collected_at = ? WHERE id = ?",
                (collected_at, indicator_id),
            )

    # ── Records ─────────────────────────────────────────────────

    def insert_records(self, records: List[MacroRecord]):
        sql = """
        INSERT OR IGNORE INTO macro_records (indicator_id, period, value, collected_at)
        VALUES (?, ?, ?, ?)
        """
        with self._connect() as conn:
            conn.executemany(
                sql,
                [(r.indicator_id, r.period, r.value, r.collected_at) for r in records],
            )

    def get_history(self, indicator_id: int, months: int = 24) -> List[MacroRecord]:
        """period별 최신 수집값 기준 시계열, 최근 N개월."""
        sql = """
        SELECT id, indicator_id, period, value, collected_at
        FROM macro_records
        WHERE indicator_id = ?
          AND collected_at = (
              SELECT MAX(r2.collected_at)
              FROM macro_records r2
              WHERE r2.indicator_id = macro_records.indicator_id
                AND r2.period = macro_records.period
          )
        ORDER BY period DESC
        LIMIT ?
        """
        with self._connect() as conn:
            rows = conn.execute(sql, (indicator_id, months)).fetchall()
        return [_row_to_record(r) for r in rows]

    def get_latest(self, domain: Optional[str] = None) -> List[dict]:
        """각 지표별 최신 period, 최신 수집값 반환."""
        domain_filter = "AND (d.domain = ? OR d.domain = 'common')" if domain else ""
        params = [domain] if domain else []
        sql = f"""
        SELECT d.id, d.name, d.unit, d.domain, d.category,
               r.period, r.value, r.collected_at
        FROM macro_indicator_definitions d
        JOIN macro_records r ON r.indicator_id = d.id
        WHERE d.is_active = 1
          {domain_filter}
          AND r.collected_at = (
              SELECT MAX(r2.collected_at)
              FROM macro_records r2
              WHERE r2.indicator_id = r.indicator_id AND r2.period = r.period
          )
          AND r.period = (
              SELECT MAX(r3.period)
              FROM macro_records r3
              WHERE r3.indicator_id = d.id
          )
        ORDER BY d.category, d.name
        """
        with self._connect() as conn:
            rows = conn.execute(sql, params).fetchall()
        return [dict(r) for r in rows]


# ── Row Converters ───────────────────────────────────────────────

def _row_to_def(row: sqlite3.Row) -> MacroIndicatorDef:
    return MacroIndicatorDef(
        id=row["id"],
        code=row["code"],
        item_code=row["item_code"],
        name=row["name"],
        unit=row["unit"],
        frequency=row["frequency"],
        collect_every_days=row["collect_every_days"],
        domain=row["domain"],
        category=row["category"],
        is_active=bool(row["is_active"]),
        last_collected_at=row["last_collected_at"],
        created_at=row["created_at"],
    )


def _row_to_record(row: sqlite3.Row) -> MacroRecord:
    return MacroRecord(
        id=row["id"],
        indicator_id=row["indicator_id"],
        period=row["period"],
        value=row["value"],
        collected_at=row["collected_at"],
    )
