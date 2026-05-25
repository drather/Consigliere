import sqlite3
import threading
from datetime import date
from typing import List, Optional
from .models import JeonseTransaction

_DDL = """
CREATE TABLE IF NOT EXISTS jeonse_transactions (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    complex_code  TEXT,
    apt_name      TEXT NOT NULL,
    district_code TEXT NOT NULL,
    deal_date     TEXT NOT NULL,
    exclusive_area REAL NOT NULL,
    deposit       INTEGER NOT NULL,
    monthly_rent  INTEGER NOT NULL DEFAULT 0,
    contract_type TEXT NOT NULL DEFAULT 'jeonse',
    floor         INTEGER NOT NULL DEFAULT 0,
    collected_at  TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE(apt_name, district_code, deal_date, floor, deposit, exclusive_area)
);
CREATE INDEX IF NOT EXISTS idx_jeonse_complex ON jeonse_transactions(complex_code);
CREATE INDEX IF NOT EXISTS idx_jeonse_date    ON jeonse_transactions(deal_date);
"""


class JeonseRepository:
    def __init__(self, db_path: str):
        self._conn = sqlite3.connect(db_path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._conn.executescript(_DDL)
        self._conn.commit()
        self._lock = threading.Lock()

    def save(self, tx: JeonseTransaction) -> None:
        with self._lock:
            self._conn.execute(
                """INSERT OR IGNORE INTO jeonse_transactions
                   (complex_code, apt_name, district_code, deal_date,
                    exclusive_area, deposit, monthly_rent, contract_type, floor)
                   VALUES (?,?,?,?,?,?,?,?,?)""",
                (tx.complex_code, tx.apt_name, tx.district_code, tx.deal_date,
                 tx.exclusive_area, tx.deposit, tx.monthly_rent, tx.contract_type, tx.floor)
            )
            self._conn.commit()

    def save_bulk(self, txs: List[JeonseTransaction]) -> int:
        saved = 0
        with self._lock:
            for tx in txs:
                cur = self._conn.execute(
                    """INSERT OR IGNORE INTO jeonse_transactions
                       (complex_code, apt_name, district_code, deal_date,
                        exclusive_area, deposit, monthly_rent, contract_type, floor)
                       VALUES (?,?,?,?,?,?,?,?,?)""",
                    (tx.complex_code, tx.apt_name, tx.district_code, tx.deal_date,
                     tx.exclusive_area, tx.deposit, tx.monthly_rent, tx.contract_type, tx.floor)
                )
                saved += cur.rowcount
            self._conn.commit()
        return saved

    def get_recent(
        self,
        complex_code: Optional[str],
        area: float,
        months: int = 6,
        apt_name: Optional[str] = None,
        district_code: Optional[str] = None,
        jeonse_only: bool = False,
    ) -> List[JeonseTransaction]:
        today = date.today()
        year = today.year - (months // 12)
        month = today.month - (months % 12)
        if month <= 0:
            month += 12
            year -= 1
        cutoff = today.replace(year=year, month=month).isoformat()

        clauses = ["exclusive_area BETWEEN ? AND ?", "deal_date >= ?"]
        params: list = [area - 5, area + 5, cutoff]

        if jeonse_only:
            clauses.append("contract_type = ?")
            params.append("jeonse")

        if complex_code:
            clauses.insert(0, "complex_code = ?")
            params.insert(0, complex_code)
        elif apt_name and district_code:
            clauses.insert(0, "district_code = ?")
            params.insert(0, district_code)
            clauses.insert(0, "apt_name = ?")
            params.insert(0, apt_name)
        else:
            return []

        sql = "SELECT * FROM jeonse_transactions WHERE " + " AND ".join(clauses) + " ORDER BY deal_date DESC"
        rows = self._conn.execute(sql, params).fetchall()

        return [JeonseTransaction(
            id=r["id"], complex_code=r["complex_code"], apt_name=r["apt_name"],
            district_code=r["district_code"], deal_date=r["deal_date"],
            exclusive_area=r["exclusive_area"], deposit=r["deposit"],
            monthly_rent=r["monthly_rent"], contract_type=r["contract_type"],
            floor=r["floor"]
        ) for r in rows]
