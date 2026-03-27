import json
import os
from datetime import date, timedelta
from typing import List
from core.logger import get_logger
from modules.career.models import SkillGapSnapshot

logger = get_logger(__name__)


class HistoryTracker:
    """
    스킬 갭 스냅샷을 날짜별 JSON 파일로 저장/로드한다.
    """
    def __init__(self, data_dir: str):
        self.gap_dir = os.path.join(data_dir, "history", "skill_gap")

    def save_snapshot(self, snapshot: SkillGapSnapshot) -> None:
        os.makedirs(self.gap_dir, exist_ok=True)
        path = os.path.join(self.gap_dir, f"{snapshot.date}_skill_gap.json")
        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(snapshot.model_dump(), f, ensure_ascii=False, indent=2)
        except OSError as e:
            logger.error(f"스냅샷 저장 실패 {path}: {e}")

    def load_recent(self, weeks: int = 4) -> List[SkillGapSnapshot]:
        """최근 N주치 스냅샷을 반환한다. 손상된 파일은 건너뛴다."""
        snapshots = []
        cutoff = date.today() - timedelta(weeks=weeks)
        if not os.path.exists(self.gap_dir):
            return snapshots

        for fname in sorted(os.listdir(self.gap_dir)):
            if not fname.endswith("_skill_gap.json"):
                continue
            date_str = fname.replace("_skill_gap.json", "")
            try:
                snap_date = date.fromisoformat(date_str)
            except ValueError:
                continue
            if snap_date < cutoff:
                continue
            path = os.path.join(self.gap_dir, fname)
            try:
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                snapshots.append(SkillGapSnapshot(**data))
            except (json.JSONDecodeError, OSError, Exception) as e:
                logger.warning(f"스냅샷 파일 손상, 건너뜀 {fname}: {e}")
                continue

        return snapshots
