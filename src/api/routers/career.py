from datetime import date
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional, List, Dict, Any

from api.dependencies import get_career_agent
from modules.career.service import CareerAgent
from core.logger import get_logger

logger = get_logger(__name__)
router = APIRouter(tags=["Career"])


class PersonaUpdateRequest(BaseModel):
    updates: Dict[str, Any]


# ── 파이프라인 실행 ────────────────────────────────────────────────────

@router.post("/jobs/career/fetch-jobs")
async def fetch_jobs(target_date: Optional[str] = None, agent: CareerAgent = Depends(get_career_agent)):
    try:
        d = date.fromisoformat(target_date) if target_date else date.today()
        postings = await agent.fetch_jobs(d)
        return {"count": len(postings), "date": str(d)}
    except Exception as e:
        logger.error(f"fetch_jobs error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/jobs/career/fetch-trends")
async def fetch_trends(target_date: Optional[str] = None, agent: CareerAgent = Depends(get_career_agent)):
    try:
        d = date.fromisoformat(target_date) if target_date else date.today()
        data = await agent.fetch_trends(d)
        return {
            "date": str(d),
            "repos": len(data.get("repos", [])),
            "stories": len(data.get("stories", [])),
            "articles": len(data.get("articles", [])),
        }
    except Exception as e:
        logger.error(f"fetch_trends error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/jobs/career/fetch-community")
async def fetch_community(target_date: Optional[str] = None, agent: CareerAgent = Depends(get_career_agent)):
    try:
        d = date.fromisoformat(target_date) if target_date else date.today()
        data = await agent.fetch_community(d)
        status = data.get("collection_status", {})
        return {
            "date": str(d),
            "reddit": len(data.get("reddit", [])),
            "nitter": len(data.get("nitter", [])),
            "clien": len(data.get("clien", [])),
            "dcinside": len(data.get("dcinside", [])),
            "collection_status": status,
        }
    except Exception as e:
        logger.error(f"fetch_community error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/jobs/career/generate-report")
async def generate_report(target_date: Optional[str] = None, agent: CareerAgent = Depends(get_career_agent)):
    try:
        d = date.fromisoformat(target_date) if target_date else date.today()
        report_md = await agent.generate_report(d)
        return {"date": str(d), "report": report_md}
    except Exception as e:
        logger.error(f"generate_report error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/jobs/career/run-pipeline")
async def run_pipeline(target_date: Optional[str] = None, agent: CareerAgent = Depends(get_career_agent)):
    try:
        d = date.fromisoformat(target_date) if target_date else date.today()
        result = await agent.run_pipeline(d)
        return {"date": str(d), "report_preview": result["report_md"][:500], "slack_blocks_count": len(result["slack_blocks"].get("blocks", []))}
    except Exception as e:
        logger.error(f"run_pipeline error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/jobs/career/generate-weekly-report")
async def generate_weekly_report(iso_week: Optional[str] = None, agent: CareerAgent = Depends(get_career_agent)):
    try:
        report_md = await agent.generate_weekly_report(iso_week)
        return {"iso_week": iso_week, "report": report_md}
    except Exception as e:
        logger.error(f"generate_weekly_report error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/jobs/career/generate-monthly-report")
async def generate_monthly_report(year_month: Optional[str] = None, agent: CareerAgent = Depends(get_career_agent)):
    try:
        report_md = await agent.generate_monthly_report(year_month)
        return {"year_month": year_month, "report": report_md}
    except Exception as e:
        logger.error(f"generate_monthly_report error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ── 대시보드 조회 ─────────────────────────────────────────────────────

@router.get("/dashboard/career/reports/daily")
def list_daily_reports(agent: CareerAgent = Depends(get_career_agent)):
    return {"dates": agent.list_daily_reports()}


@router.get("/dashboard/career/reports/daily/{report_date}")
def get_daily_report(report_date: str, agent: CareerAgent = Depends(get_career_agent)):
    report = agent.get_daily_report(report_date)
    if report is None:
        raise HTTPException(status_code=404, detail="리포트 없음")
    return {"date": report_date, "report": report}


@router.get("/dashboard/career/reports/weekly")
def list_weekly_reports(agent: CareerAgent = Depends(get_career_agent)):
    return {"weeks": agent.list_weekly_reports()}


@router.get("/dashboard/career/reports/monthly")
def list_monthly_reports(agent: CareerAgent = Depends(get_career_agent)):
    return {"months": agent.list_monthly_reports()}


@router.get("/dashboard/career/skill-gap/history")
def get_skill_gap_history(weeks: int = 4, agent: CareerAgent = Depends(get_career_agent)):
    return {"history": agent.get_skill_gap_history(weeks=weeks)}


@router.get("/dashboard/career/persona")
def get_persona(agent: CareerAgent = Depends(get_career_agent)):
    return agent.get_persona()


@router.patch("/dashboard/career/persona")
def update_persona(request: PersonaUpdateRequest, agent: CareerAgent = Depends(get_career_agent)):
    updated = agent.update_persona(request.updates)
    return updated
