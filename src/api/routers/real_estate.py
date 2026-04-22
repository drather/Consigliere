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
    get_chroma_repo,
    get_tx_repo,
    get_apt_repo,
    get_apt_master_repo,
    get_commute_service,
)
from modules.real_estate.commute.commute_service import CommuteService
from modules.real_estate.service import RealEstateAgent
from modules.real_estate.monitor.service import TransactionMonitorService
from modules.real_estate.news.service import NewsService
from modules.real_estate.repository import ChromaRealEstateRepository
from modules.real_estate.transaction_repository import TransactionRepository
from modules.real_estate.apartment_repository import ApartmentRepository
from modules.real_estate.apt_master_repository import AptMasterRepository
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
def get_real_estate_insight_report(district_code: Optional[str] = None, target_date: Optional[str] = None, agent: RealEstateAgent = Depends(get_real_estate_agent)):
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
def get_real_estate_monitor(
    district_code: Optional[str] = None,
    complex_code: Optional[str] = None,
    apt_master_id: Optional[int] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    limit: int = 20,
    tx_repo: TransactionRepository = Depends(get_tx_repo),
):
    """실거래가 조회 — SQLite transactions 테이블.

    우선순위: apt_master_id > complex_code > district_code > 전체
    """
    try:
        limit = min(limit, 500)
        if apt_master_id is not None:
            txs = tx_repo.get_by_apt_master_id(
                apt_master_id=apt_master_id, limit=limit,
                date_from=date_from, date_to=date_to,
            )
        elif complex_code:
            txs = tx_repo.get_by_complex(
                complex_code=complex_code, limit=limit,
                date_from=date_from, date_to=date_to,
            )
        elif district_code:
            txs = tx_repo.get_by_district(
                district_code=district_code, limit=limit,
                date_from=date_from, date_to=date_to,
            )
        else:
            txs = tx_repo.get_all(limit=limit)

        return [
            {
                "apt_name":       t.apt_name,
                "district_code":  t.district_code,
                "complex_code":   t.complex_code,
                "apt_master_id":  t.apt_master_id,
                "deal_date":      t.deal_date,
                "price":          t.price,
                "floor":          t.floor,
                "exclusive_area": t.exclusive_area,
                "build_year":     t.build_year,
                "road_name":      t.road_name,
            }
            for t in txs
        ]
    except Exception as e:
        logger.error(f"Monitor Dashboard API Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/dashboard/real-estate/apt-master")
def get_apt_master(
    apt_name: Optional[str] = None,
    sido: Optional[str] = None,
    sigungu: Optional[str] = None,
    limit: int = 500,
    apt_master_repo: AptMasterRepository = Depends(get_apt_master_repo),
):
    """Transaction-First 단지 마스터 검색.

    실거래가에 등장한 모든 단지를 반환한다.
    apt_details(공동주택 기본정보) 보유 단지는 complex_code가 NULL이 아니다.
    """
    try:
        limit = min(limit, 2000)
        entries = apt_master_repo.search(
            apt_name=apt_name or "",
            sido=sido or "",
            sigungu=sigungu or "",
            limit=limit,
        )
        return [
            {
                "id":            e.id,
                "apt_name":      e.apt_name,
                "district_code": e.district_code,
                "sido":          e.sido,
                "sigungu":       e.sigungu,
                "complex_code":  e.complex_code,
                "tx_count":      e.tx_count,
                "first_traded":  e.first_traded,
                "last_traded":   e.last_traded,
            }
            for e in entries
        ]
    except Exception as e:
        logger.error(f"AptMaster Dashboard API Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/dashboard/real-estate/macro-history")
def get_macro_history(agent: RealEstateAgent = Depends(get_real_estate_agent)):
    """거시경제 지표 시계열 데이터. macro.db에서 조회 (기존 응답 포맷 유지)."""
    try:
        return agent.macro_service.fetch_macro_history()
    except Exception as e:
        logger.error(f"Macro History API Error: {e}")
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


# ─────────────────────────────────────────────
# Job Endpoints: /jobs/real-estate/
# ─────────────────────────────────────────────

class JobFetchTransactionsRequest(BaseModel):
    district_code: Optional[str] = Field(None, description="법정동 코드 (미입력 시 수도권 전체 수집)")
    year_month: Optional[str] = Field(None, description="YYYYMM (기본: 현재 월)")

class JobGenerateReportRequest(BaseModel):
    district_code: Optional[str] = Field(None, description="법정동 코드 (미입력 시 페르소나 관심 지역 전체)")
    target_date: Optional[str] = Field(None, description="YYYY-MM-DD (기본: 오늘)")

@router.post("/jobs/real-estate/fetch-transactions")
def job_fetch_transactions(
    request: JobFetchTransactionsRequest,
    agent: RealEstateAgent = Depends(get_real_estate_agent)
):
    """Job 1: 실거래가 외부 API 수집 → ChromaDB 저장."""
    try:
        result = agent.fetch_transactions(request.district_code, request.year_month)
        return {"status": "success", **result}
    except Exception as e:
        logger.error(f"Job1 Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/jobs/real-estate/fetch-news")
def job_fetch_news(agent: RealEstateAgent = Depends(get_real_estate_agent)):
    """Job 2: 뉴스 수집 & 분석 → 마크다운 리포트 저장."""
    try:
        result = agent.fetch_news()
        return {"status": "success", **result}
    except Exception as e:
        logger.error(f"Job2 Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/jobs/real-estate/fetch-macro")
def job_fetch_macro(agent: RealEstateAgent = Depends(get_real_estate_agent)):
    """Job 3: 한국은행 거시경제 지표 수집 → JSON 저장."""
    try:
        result = agent.fetch_macro_data()
        return {"status": "success", **result}
    except Exception as e:
        logger.error(f"Job3 Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/jobs/real-estate/generate-report")
def job_generate_report(
    request: JobGenerateReportRequest,
    agent: RealEstateAgent = Depends(get_real_estate_agent)
):
    """Job 4: 저장된 데이터 기반으로 인사이트 리포트 생성."""
    try:
        from datetime import date as date_type
        target_dt = datetime.strptime(request.target_date, "%Y-%m-%d").date() if request.target_date else date_type.today()
        result = agent.generate_report(request.district_code, target_dt)
        return {"status": "success", **result}
    except Exception as e:
        logger.error(f"Job4 Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/jobs/real-estate/build-apartment-master")
def job_build_apartment_master(agent: RealEstateAgent = Depends(get_real_estate_agent)):
    """Job 0: 수도권 아파트 마스터 DB 전수 구축 (최초 1회 또는 갱신 시 사용)."""
    try:
        result = agent.build_apartment_master()
        return {"status": "success", **result}
    except Exception as e:
        logger.error(f"Job0 (ApartmentMaster) Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/jobs/real-estate/run-pipeline")
def job_run_pipeline(
    request: JobGenerateReportRequest,
    send_slack: bool = True,
    agent: RealEstateAgent = Depends(get_real_estate_agent)
):
    """Pipeline: Job1 → Job2 → Job3 → Job4 → Slack 전송."""
    try:
        from datetime import date as date_type
        target_dt = datetime.strptime(request.target_date, "%Y-%m-%d").date() if request.target_date else date_type.today()
        result = agent.run_insight_pipeline(request.district_code, target_dt, send_slack)
        return {"status": "success", "pipeline": result}
    except Exception as e:
        logger.error(f"Pipeline Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

class PersonaUpdateRequest(BaseModel):
    user: Optional[Dict[str, Any]] = None
    investment_style: Optional[str] = None
    commute: Optional[Dict[str, Any]] = None
    apartment_preferences: Optional[Dict[str, Any]] = None
    priority_weights: Optional[Dict[str, int]] = None

@router.get("/dashboard/real-estate/persona")
def get_persona(agent: RealEstateAgent = Depends(get_real_estate_agent)):
    """현재 persona.yaml 반환."""
    try:
        return agent.get_persona()
    except Exception as e:
        logger.error(f"Persona GET Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.patch("/dashboard/real-estate/persona")
def update_persona(request: PersonaUpdateRequest, agent: RealEstateAgent = Depends(get_real_estate_agent)):
    """persona.yaml 부분 수정 + 이력 백업."""
    try:
        updates = {k: v for k, v in request.dict().items() if v is not None}
        if not updates:
            raise HTTPException(status_code=400, detail="변경할 항목이 없습니다.")
        new_persona = agent.update_persona(updates)
        return {"status": "ok", "persona": new_persona}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Persona PATCH Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

class PreferenceRuleItem(BaseModel):
    id: str
    enabled: bool
    description: str
    constraint: str

class PreferenceRulesUpdateRequest(BaseModel):
    rules: List[PreferenceRuleItem]

@router.get("/dashboard/real-estate/preference-rules")
def get_preference_rules(agent: RealEstateAgent = Depends(get_real_estate_agent)):
    """preference_rules.yaml 전체 목록 반환."""
    try:
        return {"rules": agent.get_preference_rules()}
    except Exception as e:
        logger.error(f"PreferenceRules GET Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/dashboard/real-estate/preference-rules")
def update_preference_rules(
    request: PreferenceRulesUpdateRequest,
    agent: RealEstateAgent = Depends(get_real_estate_agent)
):
    """preference_rules.yaml 전체 목록을 교체 저장."""
    try:
        rules = [r.dict() for r in request.rules]
        saved = agent.update_preference_rules(rules)
        return {"status": "ok", "rules": saved}
    except Exception as e:
        logger.error(f"PreferenceRules PUT Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/dashboard/real-estate/districts")
def get_districts():
    """config.yaml의 구/시 목록 반환 (이름 검색용)."""
    from modules.real_estate.config import RealEstateConfig
    cfg = RealEstateConfig()
    return cfg.get("districts", [])

@router.get("/dashboard/real-estate/policy-facts")
def get_policy_facts(
    query: str = "부동산 정책 공급 개발",
    n_results: int = 10,
    chroma_repo: ChromaRealEstateRepository = Depends(get_chroma_repo)
):
    """ChromaDB policy_knowledge 컬렉션 검색."""
    try:
        results = chroma_repo.search_policy(query=query, n_results=n_results)
        return results
    except Exception as e:
        logger.error(f"Policy Facts API Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/dashboard/real-estate/commute")
def get_commute_time(
    address: str,
    apt_name: str,
    district_code: str,
    commute_service: CommuteService = Depends(get_commute_service),
):
    """아파트 주소 → 삼성역 출퇴근 시간 조회 (대중교통·자차·도보 3가지).

    캐시 히트 시 즉시 반환, 캐시 미스 시 T-map API 호출 후 저장.
    """
    try:
        origin_key = f"{district_code}__{apt_name}"
        results = commute_service.get_all_modes(
            origin_key=origin_key,
            road_address=address,
            apt_name=apt_name,
            district_code=district_code,
        )
        return {
            "apt_name": apt_name,
            "destination": "삼성역",
            "transit": results["transit"].duration_minutes if "transit" in results else None,
            "car": results["car"].duration_minutes if "car" in results else None,
            "walking": results["walking"].duration_minutes if "walking" in results else None,
            "cached": all(r.cached for r in results.values()) if results else False,
        }
    except Exception as e:
        logger.error(f"Commute API Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
