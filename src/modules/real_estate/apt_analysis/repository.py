import json
import sqlite3
from typing import Optional, List

from .models import AptAnalysisReport

_DDL = """
CREATE TABLE IF NOT EXISTS apt_analysis_reports (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    complex_code TEXT NOT NULL,
    apt_name     TEXT NOT NULL,
    generated_at TEXT NOT NULL,
    report_json  TEXT NOT NULL,
    llm_insight  TEXT NOT NULL,
    slack_text   TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_apt_analysis_complex
    ON apt_analysis_reports(complex_code, generated_at DESC);
"""


class AptAnalysisRepository:
    def __init__(self, db_path: str = "data/real_estate.db"):
        self._conn = sqlite3.connect(db_path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._conn.executescript(_DDL)
        self._conn.commit()

    def save(self, report: AptAnalysisReport) -> None:
        import dataclasses
        self._conn.execute(
            """INSERT INTO apt_analysis_reports
               (complex_code, apt_name, generated_at, report_json, llm_insight, slack_text)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (
                report.complex_code,
                report.apt_name,
                report.generated_at,
                json.dumps(dataclasses.asdict(report), ensure_ascii=False),
                report.llm_insight,
                report.slack_text,
            )
        )
        self._conn.commit()

    def get_latest(self, complex_code: str) -> Optional[AptAnalysisReport]:
        row = self._conn.execute(
            "SELECT report_json FROM apt_analysis_reports "
            "WHERE complex_code = ? ORDER BY generated_at DESC LIMIT 1",
            (complex_code,)
        ).fetchone()
        if row is None:
            return None
        return self._from_json(row["report_json"])

    def get_history(self, complex_code: str, limit: int = 10) -> List[AptAnalysisReport]:
        rows = self._conn.execute(
            "SELECT report_json FROM apt_analysis_reports "
            "WHERE complex_code = ? ORDER BY generated_at DESC LIMIT ?",
            (complex_code, limit)
        ).fetchall()
        return [self._from_json(r["report_json"]) for r in rows]

    @staticmethod
    def _from_json(raw: str) -> AptAnalysisReport:
        data = json.loads(raw)
        return AptAnalysisReport(**data)
