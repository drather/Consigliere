from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from agents.finance_agent import FinanceAgent

app = FastAPI(title="Consigliere API", description="Personal Knowledge Agent API")

# Initialize Agents
finance_agent = FinanceAgent(storage_mode="local")

class TransactionRequest(BaseModel):
    text: str

@app.get("/")
def read_root():
    return {"status": "ok", "service": "Consigliere API"}

@app.post("/agent/finance/add_transaction")
def add_transaction(request: TransactionRequest):
    """
    Receives unstructured text (e.g. SMS), extracts data, and updates the ledger.
    """
    try:
        response = finance_agent.process_transaction(request.text)
        return {"response": response}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
