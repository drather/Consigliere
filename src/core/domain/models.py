from datetime import date
from typing import List
from pydantic import BaseModel

class Transaction(BaseModel):
    date: date
    category: str
    item: str
    amount: int

class LedgerSummary(BaseModel):
    year: int
    month: int
    total_amount: int
    transaction_count: int
    recent_transactions: List[Transaction]
