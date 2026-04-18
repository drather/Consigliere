from datetime import datetime, timedelta, timezone
from typing import Optional, List, Dict, Any

from .models import MacroIndicatorDef, MacroRecord
from .repository import MacroRepository
from .bok_client import BOKClient

try:
    from core.logger import get_logger
    logger = get_logger(__name__)
except ImportError:
    import logging
    logger = logging.getLogger(__name__)


class MacroCollectionService:
    def __init__(self, db_path: str = "data/macro.db", api_key: Optional[str] = None):
        self.repo = MacroRepository(db_path=db_path)
        self.client = BOKClient(api_key=api_key)

    # ── 수집 ────────────────────────────────────────────────────

    def collect_due_indicators(self, domain: Optional[str] = None) -> Dict[str, Any]:
        """collect_every_days 기준으로 수집 기한이 된 지표만 수집."""
        indicators = self.repo.get_active_indicators(domain=domain)
        collected, skipped, errors = [], [], []

        for ind in indicators:
            if not self._is_due(ind):
                skipped.append(ind.name)
                continue
            try:
                self._collect_one(ind)
                collected.append(ind.name)
            except Exception as e:
                logger.error(f"[MacroCollectionService] {ind.name}: {e}")
                errors.append({"name": ind.name, "error": str(e)})

        return {"collected": collected, "skipped": skipped, "errors": errors}

    def collect_all(self, domain: Optional[str] = None) -> Dict[str, Any]:
        """기한 무관하게 전체 강제 수집. 초기 시딩 및 수동 트리거용."""
        indicators = self.repo.get_active_indicators(domain=domain)
        collected, errors = [], []

        for ind in indicators:
            try:
                self._collect_one(ind)
                collected.append(ind.name)
            except Exception as e:
                logger.error(f"[MacroCollectionService] {ind.name}: {e}")
                errors.append({"name": ind.name, "error": str(e)})

        return {"collected": collected, "errors": errors}

    def _is_due(self, ind: MacroIndicatorDef) -> bool:
        if not ind.last_collected_at:
            return True
        last = datetime.fromisoformat(ind.last_collected_at)
        if last.tzinfo is None:
            last = last.replace(tzinfo=timezone.utc)
        return datetime.now(timezone.utc) >= last + timedelta(days=ind.collect_every_days)

    def _collect_one(self, ind: MacroIndicatorDef):
        now = datetime.now(timezone.utc).isoformat()
        rows = self.client.get_statistic_series(
            stat_code=ind.code,
            item_code=ind.item_code,
            months=24,
            frequency=ind.frequency,
        )
        records = []
        for r in rows:
            try:
                records.append(MacroRecord(
                    id=None,
                    indicator_id=ind.id,
                    period=r["TIME"],
                    value=float(r["DATA_VALUE"]),
                    collected_at=now,
                ))
            except (KeyError, ValueError):
                continue
        if records:
            self.repo.insert_records(records)
        self.repo.update_last_collected(ind.id, now)

    # ── 조회 ────────────────────────────────────────────────────

    def get_latest(self, domain: Optional[str] = None) -> List[dict]:
        return self.repo.get_latest(domain=domain)

    def get_history(self, indicator_id: int, months: int = 24) -> List[MacroRecord]:
        return self.repo.get_history(indicator_id, months)
