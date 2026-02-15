import re
from datetime import date
from typing import List

from core.storage import StorageProvider
from .models import Transaction, LedgerSummary
from .repository import LedgerRepository

class MarkdownLedgerRepository(LedgerRepository):
    """
    Implementation of LedgerRepository using Markdown files on the storage provider.
    Path: Finance/Ledger_{YYYY}_{MM}.md
    """
    
    def __init__(self, storage: StorageProvider, root_dir: str = "Finance"):
        self.storage = storage
        self.root_dir = root_dir

    def _get_path(self, year: int, month: int) -> str:
        return f"{self.root_dir}/Ledger_{year}_{month:02d}.md"

    def _ensure_file_exists(self, year: int, month: int) -> str:
        path = self._get_path(year, month)
        if not self.storage.exists(path):
            header = (
                f"# Ledger {year}_{month:02d}\n\n"
                "| Date | Category | Item | Amount |\n"
                "|---|---|---|---|"
                "**Total:** 0"
            )
            self.storage.write_file(path, header)
            return header
        return self.storage.read_file(path)

    def save(self, transaction: Transaction) -> None:
        year, month = transaction.date.year, transaction.date.month
        content = self._ensure_file_exists(year, month)
        
        # Calculate new total
        current_total = self._extract_total(content)
        new_total = current_total + transaction.amount
        
        # Create row
        new_row = f"| {transaction.date} | {transaction.category} | {transaction.item} | {transaction.amount:,} |"
        
        # Insert before Total line
        if "**Total:**" in content:
            parts = content.split("**Total:**")
            first_part = parts[0].rstrip()
            updated_content = f"{first_part}\n{new_row}\n**Total:** {new_total}"
        else:
            updated_content = f"{content}\n{new_row}\n**Total:** {new_total}"
            
        self.storage.write_file(self._get_path(year, month), updated_content)

    def get_monthly_transactions(self, year: int, month: int) -> List[Transaction]:
        path = self._get_path(year, month)
        if not self.storage.exists(path):
            return []
            
        content = self.storage.read_file(path)
        transactions = []
        
        # Simple regex to parse table rows
        # Row format: | Date | Category | Item | Amount |
        for line in content.splitlines():
            if line.strip().startswith("|") and "Date" not in line and "---" not in line:
                parts = [p.strip() for p in line.split("|") if p.strip()]
                if len(parts) >= 4:
                    try:
                        t_date = date.fromisoformat(parts[0])
                        amount = int(parts[3].replace(",", ""))
                        transactions.append(Transaction(
                            date=t_date,
                            category=parts[1],
                            item=parts[2],
                            amount=amount
                        ))
                    except ValueError:
                        continue
        return transactions

    def get_summary(self, year: int, month: int) -> LedgerSummary:
        transactions = self.get_monthly_transactions(year, month)
        total = sum(t.amount for t in transactions)
        
        return LedgerSummary(
            year=year,
            month=month,
            total_amount=total,
            transaction_count=len(transactions),
            recent_transactions=transactions[-5:] # Last 5
        )

    def _extract_total(self, content: str) -> int:
        match = re.search(r"\*\*Total:\*\*\s*(\d+)", content)
        if match:
            return int(match.group(1))
        return 0