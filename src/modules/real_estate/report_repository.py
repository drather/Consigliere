"""
ReportRepository — 전문 컨설턴트 리포트를 Markdown + JSON으로 저장/조회한다.
"""
import json
import os
from dataclasses import dataclass, field, asdict
from typing import List, Dict, Optional, Any

from core.logger import get_logger

logger = get_logger(__name__)


@dataclass
class ProfessionalReport:
    date: str
    budget_available: int
    macro_summary: str
    candidates_summary: List[Dict]
    location_analyses: List[Dict]
    school_analyses: List[Dict]
    strategy: Dict[str, Any]
    markdown: str


class ReportRepository:
    def __init__(self, storage_path: str):
        self._path = storage_path
        os.makedirs(storage_path, exist_ok=True)

    def save(self, report: ProfessionalReport) -> None:
        md_path = os.path.join(self._path, f"{report.date}.md")
        json_path = os.path.join(self._path, f"{report.date}.json")

        with open(md_path, "w", encoding="utf-8") as f:
            f.write(report.markdown)

        data = asdict(report)
        data.pop("markdown")
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        logger.info(f"[ReportRepository] 저장 완료: {report.date}")

    def load(self, date_str: str) -> Optional[ProfessionalReport]:
        json_path = os.path.join(self._path, f"{date_str}.json")
        md_path = os.path.join(self._path, f"{date_str}.md")
        if not os.path.exists(json_path):
            return None
        with open(json_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        markdown = ""
        if os.path.exists(md_path):
            with open(md_path, "r", encoding="utf-8") as f:
                markdown = f.read()
        return ProfessionalReport(
            date=data["date"],
            budget_available=data["budget_available"],
            macro_summary=data["macro_summary"],
            candidates_summary=data.get("candidates_summary", []),
            location_analyses=data.get("location_analyses", []),
            school_analyses=data.get("school_analyses", []),
            strategy=data.get("strategy", {}),
            markdown=markdown,
        )

    def list_dates(self) -> List[str]:
        files = [
            f[:-5] for f in os.listdir(self._path)
            if f.endswith(".json")
        ]
        return sorted(files, reverse=True)
