import re
import json
import os
from datetime import datetime, date
from typing import Dict, Any

from core.storage import get_storage_provider, StorageProvider
from core.prompt_loader import PromptLoader
from .models import Transaction, LedgerSummary
from .repository import LedgerRepository
from .markdown_ledger import MarkdownLedgerRepository
from core.llm import LLMClient

class FinanceAgent:
    def __init__(self, storage_mode: str = "local"):
        self.storage: StorageProvider = get_storage_provider(storage_mode)
        
        # PromptLoader should look at module specific prompts
        # We assume local storage for prompts for now
        root_storage = get_storage_provider("local", root_path=".")
        self.prompt_loader = PromptLoader(root_storage, base_dir="src/modules/finance/prompts")
        
        # Repository Dependency
        self.repository: LedgerRepository = MarkdownLedgerRepository(self.storage)

        # Initialize LLM Client
        self.llm = LLMClient()

    def process_transaction(self, user_text: str) -> str:
        """
        Main workflow: Receive Text -> Parse (LLM) -> Save to Repo -> Generate Response
        """
        # 1. Parse Transaction with Real AI
        try:
            transaction_data = self._llm_parse(user_text)
        except Exception as e:
             return f"⚠️ Failed to understand: {str(e)}"
        
        # 2. Convert to Domain Model
        try:
            # Handle potential date format issues from LLM
            t_date = date.fromisoformat(transaction_data.get('date', datetime.now().strftime("%Y-%m-%d")))
            
            transaction = Transaction(
                date=t_date,
                category=transaction_data.get('category', 'Uncategorized'),
                item=transaction_data.get('item', 'Unknown Item'),
                amount=int(transaction_data.get('amount', 0))
            )
        except (ValueError, KeyError) as e:
            return f"❌ Data Error: Could not convert AI response to Transaction. ({str(e)})"
        
        # 3. Save (Repository Logic)
        self.repository.save(transaction)
        
        # 4. Get Summary for Response
        summary = self.repository.get_summary(transaction.date.year, transaction.date.month)
        
        return (
            f"✅ Transaction Saved via Gemini.\n"
            f"- Added: {transaction.item} ({transaction.amount:,} KRW) [{transaction.category}]\n"
            f"- Monthly Total: {summary.total_amount:,} KRW ({summary.transaction_count} transactions)"
        )

    def _llm_parse(self, text: str) -> Dict[str, Any]:
        """
        Uses PromptLoader to prepare prompt and LLMClient to execute.
        """
        # Load Prompt Template
        metadata, prompt_str = self.prompt_loader.load(
            "parser", 
            variables={
                "current_date": datetime.now().strftime("%Y-%m-%d"),
                "user_input": text
            }
        )
        
        # Execute LLM
        print(f"🧠 Asking Gemini: {prompt_str[:50]}...")
        result = self.llm.generate_json(prompt_str)
        
        if "error" in result:
             raise ValueError(f"LLM Error: {result['error']}")
             
        return result