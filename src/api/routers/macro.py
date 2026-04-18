from fastapi import APIRouter, Depends, HTTPException
from typing import Optional
from modules.macro.service import MacroCollectionService
from api.dependencies import get_macro_service
from core.logger import get_logger

logger = get_logger(__name__)
router = APIRouter(tags=["Macro"])


@router.post("/jobs/macro/collect")
def job_collect_macro(
    domain: Optional[str] = None,
    force_all: bool = False,
    service: MacroCollectionService = Depends(get_macro_service),
):
    """
    거시경제 지표 수집 Job.
    - domain: "real_estate" / "finance" / "common" / None(전체)
    - force_all: True면 수집 기한 무관하게 강제 수집
    """
    try:
        if force_all:
            result = service.collect_all(domain=domain)
        else:
            result = service.collect_due_indicators(domain=domain)
        return {"status": "success", **result}
    except Exception as e:
        logger.error(f"Macro Collect Job Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/dashboard/macro/latest")
def get_macro_latest(
    domain: Optional[str] = None,
    service: MacroCollectionService = Depends(get_macro_service),
):
    """지표별 최신값. domain 필터 가능."""
    try:
        return service.get_latest(domain=domain)
    except Exception as e:
        logger.error(f"Macro Latest API Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/dashboard/macro/history/{indicator_id}")
def get_macro_history_by_id(
    indicator_id: int,
    months: int = 24,
    service: MacroCollectionService = Depends(get_macro_service),
):
    """단일 지표 시계열 (최근 N개월)."""
    try:
        ind = service.repo.get_indicator_by_id(indicator_id)
        if not ind:
            raise HTTPException(status_code=404, detail=f"indicator_id={indicator_id} not found")
        records = service.get_history(indicator_id, months=months)
        return {
            "indicator": {
                "id": ind.id, "name": ind.name, "unit": ind.unit,
                "domain": ind.domain, "category": ind.category,
            },
            "records": [
                {"period": r.period, "value": r.value, "collected_at": r.collected_at}
                for r in records
            ],
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Macro History API Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
