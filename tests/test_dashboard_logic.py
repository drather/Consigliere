import unittest
import os
import pandas as pd
from datetime import date
from core.storage import get_storage_provider
from modules.finance.markdown_ledger import MarkdownLedgerRepository
from modules.finance.models import Transaction

class TestDashboardData(unittest.TestCase):
    def setUp(self):
        self.storage = get_storage_provider("local", root_path=".")
        self.repo = MarkdownLedgerRepository(self.storage, root_dir="data/Finance_Test")
        
        # Create a test ledger file using triple quotes for clarity
        self.year, self.month = 2026, 99
        path = f"data/Finance_Test/Ledger_{self.year}_{self.month:02d}.md"
        os.makedirs("data/Finance_Test", exist_ok=True)
        
        content = f"""# Ledger {self.year}_{self.month:02d}

| Date | Category | Item | Amount |
|---|---|---|---|
| 2026-09-01 | Food | Pizza | 30,000 |
| 2026-09-02 | Transport | Taxi | 15,000 |

**Total:** 45000"""
        with open(path, "w") as f:
            f.write(content)

    def tearDown(self):
        import shutil
        if os.path.exists("data/Finance_Test"):
            shutil.rmtree("data/Finance_Test")

    def test_read_ledger_as_dataframe(self):
        df = self.repo.read_ledger_as_dataframe(self.year, self.month)
        
        self.assertFalse(df.empty)
        self.assertEqual(len(df), 2)
        self.assertEqual(int(df["Amount"].sum()), 45000)
        self.assertIn("Pizza", df["Item"].values)

if __name__ == "__main__":
    unittest.main()
