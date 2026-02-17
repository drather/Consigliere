from datetime import datetime
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from typing import Optional

from modules.finance.service import FinanceAgent
from modules.real_estate.service import RealEstateAgent
from modules.real_estate.monitor.service import TransactionMonitorService
from modules.real_estate.news.service import NewsService
from modules.real_estate.repository import ChromaRealEstateRepository

app = FastAPI(title="Consigliere API", description="Personal Knowledge Agent API")

# Initialize Agents & Services
finance_agent = FinanceAgent(storage_mode="local")
real_estate_agent = RealEstateAgent(storage_mode="local")
monitor_service = TransactionMonitorService()
news_service = NewsService(storage_mode="local")
chroma_repo = ChromaRealEstateRepository()

class TransactionRequest(BaseModel):
    text: str

class RealEstateRequest(BaseModel):
    text: str

class RealEstateMonitorRequest(BaseModel):
    district_code: Optional[str] = Field("41135", description="Legal Dong Code (Default: Bundang-gu)")
    year_month: Optional[str] = Field(None, description="YYYYMM (Default: Current Month)")

class NewsAnalysisRequest(BaseModel):
    keywords: Optional[str] = Field(None, description="Custom keywords to override default")

@app.get("/")
def read_root():
    return {"status": "ok", "service": "Consigliere API"}

@app.post("/agent/finance/transaction")
def add_transaction(request: TransactionRequest):
    """
    Parses natural language transaction text and saves it to the ledger.
    """
    try:
        response = finance_agent.process_transaction(request.text)
        return {"response": response}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/agent/real_estate/report")
def add_real_estate_report(request: RealEstateRequest):
    """
    Logs a new real estate tour report.
    """
    try:
        response = real_estate_agent.log_tour(request.text)
        return {"response": response}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/agent/real_estate/search")
def search_real_estate(request: RealEstateRequest):
    """
    Searches for real estate reports based on natural language query.
    """
    try:
        response = real_estate_agent.search_tours(request.text)
        return {"response": response}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/agent/real_estate/monitor/fetch")
def fetch_real_estate_transactions(request: RealEstateMonitorRequest):
    """
    Triggers the Real Estate Monitor to fetch data from MOLIT API and save to ChromaDB.
    """
    try:
        # Default to current month if not provided
        target_ym = request.year_month
        if not target_ym:
            now = datetime.now()
            target_ym = now.strftime("%Y%m")

        print(f"🚀 [API] Triggering Monitor for {request.district_code}, {target_ym}")
        
        # 1. Fetch from API
        transactions = monitor_service.get_daily_transactions(request.district_code, target_ym)
        
        if not transactions:
            return {
                "status": "success",
                "message": "No transactions found or API error.",
                "fetched_count": 0,
                "saved_count": 0
            }

        # 2. Save to ChromaDB
        saved_count = 0
        for tx in transactions:
            try:
                chroma_repo.save_transaction(tx)
                saved_count += 1
            except Exception as save_err:
                print(f"⚠️ Failed to save transaction {tx.apt_name}: {save_err}")

        return {
            "status": "success",
            "district_code": request.district_code,
            "year_month": target_ym,
            "fetched_count": len(transactions),
            "saved_count": saved_count
        }

    except Exception as e:
        print(f"❌ Monitor API Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/agent/real_estate/news/analyze")
def analyze_real_estate_news(request: NewsAnalysisRequest):
    """
    Triggers the News Insight Agent to fetch news, analyze with LLM, and save report.
    """
    try:
        print(f"🚀 [API] Triggering News Analysis...")
        # Note: We currently don't support custom keywords in generate_daily_report, 
        # but we can extend it later. For now, use default.
        report_content = news_service.generate_daily_report()
        
        if "❌" in report_content:
             raise HTTPException(status_code=500, detail=report_content)

        return {
            "status": "success",
            "report_date": datetime.now().strftime("%Y-%m-%d"),
            "report_content": report_content
        }
    except Exception as e:
        print(f"❌ News API Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
