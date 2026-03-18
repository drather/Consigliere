import json
import os
from datetime import datetime
from glob import glob
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any

from api.dependencies import (
    get_real_estate_agent,
    get_monitor_service,
    get_news_service,
    get_chroma_repo
)
from modules.real_estate.service import RealEstateAgent
from modules.real_estate.monitor.service import TransactionMonitorService
from modules.real_estate.news.service import NewsService
from modules.real_estate.repository import ChromaRealEstateRepository
from core.logger import get_logger

logger = get_logger(__name__)
router = APIRouter(tags=["Real Estate"])

class RealEstateRequest(BaseModel):
    text: str

class RealEstateMonitorRequest(BaseModel):
    district_code: Optional[str] = Field("41135", description="Legal Dong Code (Default: Bundang-gu)")
    year_month: Optional[str] = Field(None, description="YYYYMM (Default: Current Month)")

class NewsAnalysisRequest(BaseModel):
    keywords: Optional[str] = Field(None, description="Custom keywords to override default")

@router.post("/agent/real_estate/report")
def add_real_estate_report(request: RealEstateRequest, agent: RealEstateAgent = Depends(get_real_estate_agent)):
    try:
        response = agent.log_tour(request.text)
        return {"response": response}
    except Exception as e:
        logger.error(f"Real Estate Add Report Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/agent/real_estate/search")
def search_real_estate(request: RealEstateRequest, agent: RealEstateAgent = Depends(get_real_estate_agent)):
    try:
        response = agent.search_tours(request.text)
        return {"response": response}
    except Exception as e:
        logger.error(f"Real Estate Search Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/agent/real_estate/monitor/fetch")
def fetch_real_estate_transactions(
    request: RealEstateMonitorRequest,
    monitor_service: TransactionMonitorService = Depends(get_monitor_service),
    chroma_repo: ChromaRealEstateRepository = Depends(get_chroma_repo)
):
    try:
        target_ym = request.year_month or datetime.now().strftime("%Y%m")
        logger.info(f"[API] Triggering Monitor for {request.district_code}, {target_ym}")
        
        transactions = monitor_service.get_daily_transactions(request.district_code, target_ym)
        if not transactions:
            return {"status": "success", "message": "No transactions found", "fetched_count": 0, "saved_count": 0}

        saved_count = 0
        for tx in transactions:
            try:
                chroma_repo.save_transaction(tx)
                saved_count += 1
            except Exception as save_err:
                logger.error(f"Failed to save transaction {tx.apt_name}: {save_err}")

        return {"status": "success", "district_code": request.district_code, "year_month": target_ym, "fetched_count": len(transactions), "saved_count": saved_count}
    except Exception as e:
        logger.error(f"Monitor API Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/agent/real_estate/monitor/daily_summary")
def get_real_estate_daily_summary(district_code: str = "41135", target_date: Optional[str] = None, agent: RealEstateAgent = Depends(get_real_estate_agent)):
    try:
        from datetime import timedelta
        if not target_date:
            target_dt = (datetime.now() - timedelta(days=1)).date()
        else:
            target_dt = datetime.strptime(target_date, "%Y-%m-%d").date()
            
        logger.info(f"[API] Generating Daily Summary for {district_code}, {target_dt}")
        blocks = agent.get_daily_summary(district_code, target_dt)
        return {"status": "success", "blocks": blocks, "text": f"{target_dt.strftime('%Y-%m-%d')} 부동산 실거래가 요약"}
    except Exception as e:
        logger.error(f"Daily Summary API Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/agent/real_estate/insight_report")
def get_real_estate_insight_report(district_code: str = "11680", target_date: Optional[str] = None, agent: RealEstateAgent = Depends(get_real_estate_agent)):
    try:
        target_dt = datetime.strptime(target_date, "%Y-%m-%d").date() if target_date else datetime.now().date()
        blocks_data = agent.generate_insight_report(district_code, target_dt)
        blocks = blocks_data["blocks"] if isinstance(blocks_data, dict) and "blocks" in blocks_data else blocks_data
        return {"status": "success", "blocks": blocks, "text": f"{target_dt.strftime('%Y-%m-%d')} 부동산 종합 인사이트 리포트"}
    except Exception as e:
        logger.error(f"Insight Report API Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/agent/real_estate/news/analyze")
def analyze_real_estate_news(request: NewsAnalysisRequest, news_service: NewsService = Depends(get_news_service)):
    try:
        logger.info(f"[API] Triggering News Analysis...")
        report_content = news_service.generate_daily_report()
        if "❌" in report_content:
             raise HTTPException(status_code=500, detail=report_content)
        return {"status": "success", "report_date": datetime.now().strftime("%Y-%m-%d"), "report_content": report_content}
    except Exception as e:
        logger.error(f"News API Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/agent/real_estate/news/update_policy")
def update_policy_knowledge(news_service: NewsService = Depends(get_news_service)):
    """Triggers the Phase 2 Advanced Scraper to update ChromaDB policy facts."""
    try:
        logger.info("[API] Triggering Advanced Policy Scaping...")
        fact_count = news_service.update_policy_knowledge()
        return {"status": "success", "indexed_facts": fact_count}
    except Exception as e:
        logger.error(f"Update Policy API Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/dashboard/real-estate/monitor")
def get_real_estate_monitor(district_code: Optional[str] = None, limit: int = 50, chroma_repo: ChromaRealEstateRepository = Depends(get_chroma_repo)):
    try:
        where_clause = {"district_code": district_code} if district_code else None
        transactions = chroma_repo.get_transactions(limit=limit, where=where_clause)
        return transactions
    except Exception as e:
        logger.error(f"Monitor Dashboard API Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/dashboard/real-estate/news")
def list_real_estate_news(news_service: NewsService = Depends(get_news_service)):
    try:
        return news_service.list_reports()
    except Exception as e:
        logger.error(f"News List Dashboard API Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/dashboard/real-estate/reports")
def list_insight_reports() -> List[Dict[str, Any]]:
    """저장된 인사이트 리포트 목록을 반환한다."""
    try:
        report_dir = os.path.join(os.getenv("LOCAL_STORAGE_PATH", "./data"), "real_estate", "reports")
        if not os.path.exists(report_dir):
            return []
        files = sorted(glob(os.path.join(report_dir, "*_Report.json")), reverse=True)
        result = []
        for f in files:
            try:
                with open(f, "r", encoding="utf-8") as fh:
                    meta = json.load(fh)
                result.append({
                    "filename": os.path.basename(f),
                    "date": meta.get("date", ""),
                    "score": meta.get("score", 0),
                    "tx_count": meta.get("tx_count", 0),
                    "created_at": meta.get("created_at", ""),
                })
            except Exception:
                continue
        return result
    except Exception as e:
        logger.error(f"Report List API Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/dashboard/real-estate/reports/{filename}")
def get_insight_report(filename: str) -> Dict[str, Any]:
    """저장된 인사이트 리포트 상세 내용을 반환한다."""
    try:
        report_dir = os.path.join(os.getenv("LOCAL_STORAGE_PATH", "./data"), "real_estate", "reports")
        filepath = os.path.join(report_dir, filename)
        if not os.path.exists(filepath):
            raise HTTPException(status_code=404, detail="Report not found.")
        with open(filepath, "r", encoding="utf-8") as f:
            return json.load(f)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Report Detail API Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/dashboard/real-estate/news/{filename}")
def get_real_estate_news_content(filename: str, news_service: NewsService = Depends(get_news_service)):
    try:
        content = news_service.get_report_content(filename)
        if content.startswith("❌"):
             raise HTTPException(status_code=404, detail=content)
        return {"filename": filename, "content": content}
    except Exception as e:
        logger.error(f"News Content Dashboard API Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
