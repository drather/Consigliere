import json
import os
from datetime import datetime
from glob import glob
from typing import List, Optional

from core.storage import get_storage_provider, StorageProvider
from core.prompt_loader import PromptLoader
from core.llm import LLMClient
from ..models import NewsArticle, NewsAnalysisReport
from .client import NaverNewsClient

class NewsService:
    def __init__(self, storage_mode: str = "local"):
        self.storage: StorageProvider = get_storage_provider(storage_mode)
        root_storage = get_storage_provider("local", root_path=".")
        self.prompt_loader = PromptLoader(root_storage, base_dir="src/modules/real_estate/prompts")
        
        self.client = NaverNewsClient()
        self.llm = LLMClient()
        self.report_dir = "data/real_estate/news"

    def generate_daily_report(self) -> str:
        """
        Main workflow: Fetch News -> Load Context -> Analyze -> Save Report.
        """
        # 1. Fetch News
        print("📰 [News] Fetching latest real estate news...")
        items = self.client.search_news("부동산 정책 아파트 분양", display=30)
        if not items:
            return "❌ No news found or API error."
        
        # Convert to Domain Models
        articles = []
        for item in items:
            articles.append(NewsArticle(
                title=item['title'].replace('<b>', '').replace('</b>', ''),
                link=item['originallink'] or item['link'], # Use originallink if available
                description=item['description'].replace('<b>', '').replace('</b>', ''),
                pub_date=item['pubDate']
            ))

        # Format news list for LLM (Text only)
        news_text = ""
        for i, article in enumerate(articles, 1):
            news_text += f"{i}. {article.title}\n   - {article.description}\n"

        # 2. Load Historical Context (Last Report)
        history_context = self._get_last_report_summary()
        
        # 3. Analyze via LLM
        print("🧠 [News] Analyzing trends with Gemini...")
        metadata, prompt_str = self.prompt_loader.load(
            "news_analyst",
            variables={
                "today": datetime.now().strftime("%Y-%m-%d"),
                "news_list": news_text,
                "historical_context": history_context
            }
        )
        
        analysis = self.llm.generate_json(prompt_str)
        if "error" in analysis:
            return f"❌ Analysis Failed: {analysis['error']}"

        # 4. Create & Save Report
        report = NewsAnalysisReport(
            date=datetime.now().strftime("%Y-%m-%d"),
            references=articles,
            **analysis
        )
        
        self._save_report(report)
        
        return report.to_markdown()

    def _get_last_report_summary(self) -> str:
        """
        Reads the most recent markdown report to provide context.
        """
        try:
            # Find all md files in the directory
            if not os.path.exists(self.report_dir):
                return "No previous reports found."
                
            files = sorted(glob(os.path.join(self.report_dir, "*.md")))
            if not files:
                return "No previous reports found."
            
            last_file = files[-1]
            content = open(last_file, 'r').read()
            return f"--- Previous Report ({os.path.basename(last_file)}) ---\n{content[:1000]}..." # Truncate
        except Exception as e:
            return f"Error loading context: {str(e)}"

    def _save_report(self, report: NewsAnalysisReport) -> None:
        """
        Saves the markdown report to file.
        """
        if not os.path.exists(self.report_dir):
            os.makedirs(self.report_dir)
            
        filename = f"{self.report_dir}/{report.date}_News.md"
        with open(filename, "w") as f:
            f.write(report.to_markdown())
        print(f"✅ [News] Report saved to {filename}")
