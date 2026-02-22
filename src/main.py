from datetime import datetime
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any

from modules.finance.service import FinanceAgent
from modules.real_estate.service import RealEstateAgent
from modules.real_estate.monitor.service import TransactionMonitorService
from modules.real_estate.news.service import NewsService
from modules.real_estate.repository import ChromaRealEstateRepository
from modules.automation.service import AutomationService

app = FastAPI(title="Consigliere API", description="Personal Knowledge Agent API")

# Initialize Agents & Services
finance_agent = FinanceAgent(storage_mode="local")
real_estate_agent = RealEstateAgent(storage_mode="local")
monitor_service = TransactionMonitorService()
news_service = NewsService(storage_mode="local")
chroma_repo = ChromaRealEstateRepository()
automation_service = AutomationService()

class TransactionRequest(BaseModel):
    text: str

class RealEstateRequest(BaseModel):
    text: str

class RealEstateMonitorRequest(BaseModel):
    district_code: Optional[str] = Field("41135", description="Legal Dong Code (Default: Bundang-gu)")
    year_month: Optional[str] = Field(None, description="YYYYMM (Default: Current Month)")

class NewsAnalysisRequest(BaseModel):
    keywords: Optional[str] = Field(None, description="Custom keywords to override default")

class WorkflowDeployRequest(BaseModel):
    workflow_json: Dict[str, Any] = Field(..., description="The n8n workflow JSON definition")

class WorkflowActivateRequest(BaseModel):
    workflow_id: str
    active: bool = True

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


# --- Automation & MCP API (n8n Integration) ---

@app.get("/agent/automation/workflows")
def list_workflows():
    """
    List all workflows currently active or stored in n8n.
    Used by MCP to retrieve context of running automations.
    """
    try:
        workflows = automation_service.list_workflows()
        return {"status": "success", "workflows": workflows}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/agent/automation/workflow/deploy")
def deploy_workflow(request: WorkflowDeployRequest):
    """
    Deploy a new workflow using a JSON template.
    Called by Gemini via MCP tool after generating the workflow.
    """
    try:
        result = automation_service.deploy_workflow(request.workflow_json)
        if "error" in result:
             raise HTTPException(status_code=500, detail=result["error"])
        
        return {"status": "success", "workflow": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/agent/automation/workflow/activate")
def activate_workflow(request: WorkflowActivateRequest):
    """
    Activate or deactivate an existing workflow by its ID.
    """
    try:
        result = automation_service.activate_workflow(request.workflow_id, request.active)
        if "error" in result:
             raise HTTPException(status_code=500, detail=result["error"])
        
        return {"status": "success", "result": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# --- Dashboard API ---

@app.get("/dashboard/finance/ledger")
def get_finance_ledger(year: int, month: int):
    """
    Returns the monthly ledger data for dashboard visualization.
    """
    try:
        df = finance_agent.get_monthly_ledger_df(year, month)
        if df.empty:
            return []
        
        # Convert DataFrame to JSON-compatible list of dicts
        # Handle date serialization
        records = df.to_dict(orient="records")
        return records
    except Exception as e:
        print(f"❌ Dashboard API Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/dashboard/real-estate/monitor")
def get_real_estate_monitor(district_code: Optional[str] = None, limit: int = 50):
    """
    Returns monitored real estate transactions from ChromaDB.
    """
    try:
        where_clause = {}
        if district_code:
            where_clause["district_code"] = district_code
            
        # If no filter, pass None to get all
        transactions = chroma_repo.get_transactions(limit=limit, where=where_clause if where_clause else None)
        return transactions
    except Exception as e:
        print(f"❌ Monitor API Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/dashboard/real-estate/news")
def list_real_estate_news():
    """
    Returns list of available news report filenames.
    """
    try:
        return news_service.list_reports()
    except Exception as e:
        print(f"❌ News List API Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/dashboard/real-estate/news/{filename}")
def get_real_estate_news_content(filename: str):
    """
    Returns content of a specific news report.
    """
    try:
        content = news_service.get_report_content(filename)
        if content.startswith("❌"):
             raise HTTPException(status_code=404, detail=content)
        return {"filename": filename, "content": content}
    except Exception as e:
        print(f"❌ News Content API Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
