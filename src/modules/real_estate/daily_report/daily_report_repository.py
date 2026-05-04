import os
from typing import List, Optional

from core.logger import get_logger
from .models import DailyReport

logger = get_logger(__name__)


class DailyReportRepository:
    """data/daily_reports/ 디렉토리에 MD 파일 형식으로 daily report를 저장·조회한다."""

    def __init__(self, storage_path: str = "data/daily_reports"):
        self._path = storage_path
        os.makedirs(storage_path, exist_ok=True)

    def save(self, report: DailyReport) -> str:
        """리포트를 MD 파일로 저장하고 파일 경로를 반환한다."""
        filename = f"daily_{report.date}.md"
        filepath = os.path.join(self._path, filename)
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(report.markdown)
        logger.info("[DailyReportRepository] 저장: %s", filepath)
        return filepath

    def load_markdown(self, date_str: str) -> Optional[str]:
        """날짜(YYYY-MM-DD) 기준 MD 파일 내용을 반환. 없으면 None."""
        filepath = os.path.join(self._path, f"daily_{date_str}.md")
        if not os.path.exists(filepath):
            return None
        with open(filepath, "r", encoding="utf-8") as f:
            return f.read()

    def list_dates(self) -> List[str]:
        """저장된 모든 리포트 날짜 목록을 최신순으로 반환."""
        dates = []
        for fname in os.listdir(self._path):
            if fname.startswith("daily_") and fname.endswith(".md"):
                date_str = fname[len("daily_"):-len(".md")]
                dates.append(date_str)
        return sorted(dates, reverse=True)

    def exists(self, date_str: str) -> bool:
        filepath = os.path.join(self._path, f"daily_{date_str}.md")
        return os.path.exists(filepath)
