import sqlite3
from datetime import date, timedelta
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

    def save(self, tx: JeonseTransaction) -> None:
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
        cutoff = (date.today() - timedelta(days=months * 30)).isoformat()
        contract_filter = "AND contract_type = 'jeonse'" if jeonse_only else ""

        if complex_code:
            rows = self._conn.execute(
                f"""SELECT * FROM jeonse_transactions
                    WHERE complex_code = ?
                      AND exclusive_area BETWEEN ? AND ?
                      AND deal_date >= ?
                      {contract_filter}
                    ORDER BY deal_date DESC""",
                (complex_code, area - 5, area + 5, cutoff)
            ).fetchall()
        elif apt_name and district_code:
            rows = self._conn.execute(
                f"""SELECT * FROM jeonse_transactions
                    WHERE apt_name = ?
                      AND district_code = ?
                      AND exclusive_area BETWEEN ? AND ?
                      AND deal_date >= ?
                      {contract_filter}
                    ORDER BY deal_date DESC""",
                (apt_name, district_code, area - 5, area + 5, cutoff)
            ).fetchall()
        else:
            return []

        return [JeonseTransaction(
            id=r["id"], complex_code=r["complex_code"], apt_name=r["apt_name"],
            district_code=r["district_code"], deal_date=r["deal_date"],
            exclusive_area=r["exclusive_area"], deposit=r["deposit"],
            monthly_rent=r["monthly_rent"], contract_type=r["contract_type"],
            floor=r["floor"]
        ) for r in rows]
