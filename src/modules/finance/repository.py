from abc import ABC, abstractmethod
from typing import List, Optional
from datetime import date
from .models import Transaction, LedgerSummary

class LedgerRepository(ABC):
    """
    Abstract Interface for Ledger Storage.
    Implementations can be Markdown, SQLite, Google Sheets, etc.
    """

    @abstractmethod
    def save(self, transaction: Transaction) -> None:
        """Saves a new transaction."""
        pass

    @abstractmethod
    def get_monthly_transactions(self, year: int, month: int) -> List[Transaction]:
        """Retrieves all transactions for a specific month."""
        pass

    @abstractmethod
    def get_summary(self, year: int, month: int) -> LedgerSummary:
        """Calculates total amount and returns summary."""
        pass
