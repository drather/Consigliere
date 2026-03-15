from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Any

from api.dependencies import get_finance_agent
from modules.finance.service import FinanceAgent
from core.logger import get_logger

logger = get_logger(__name__)
router = APIRouter(tags=["Finance"])

class TransactionRequest(BaseModel):
    text: str

@router.post("/agent/finance/transaction")
def add_transaction(request: TransactionRequest, agent: FinanceAgent = Depends(get_finance_agent)):
    """
    Parses natural language transaction text and saves it to the ledger.
    """
    try:
        response = agent.process_transaction(request.text)
        return {"response": response}
    except Exception as e:
        logger.error(f"Finance API Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/dashboard/finance/ledger")
def get_finance_ledger(year: int, month: int, agent: FinanceAgent = Depends(get_finance_agent)):
    """
    Returns the monthly ledger data for dashboard visualization.
    """
    try:
        df = agent.get_monthly_ledger_df(year, month)
        if df.empty:
            return []
        
        records = df.to_dict(orient="records")
        return records
    except Exception as e:
        logger.error(f"Dashboard Finance API Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
