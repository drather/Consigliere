import json
import os
from datetime import datetime, timezone, timedelta
from email.utils import parsedate_to_datetime
from glob import glob
from typing import List, Optional, Dict, Any

from core.storage import get_storage_provider, StorageProvider
from core.prompt_loader import PromptLoader
from core.llm import LLMClient
from ..models import NewsArticle, NewsAnalysisReport
from .client import NaverNewsClient
from core.logger import get_logger

logger = get_logger(__name__)


class NewsService:
    def __init__(self, storage_mode: str = "local"):
        self.storage: StorageProvider = get_storage_provider(storage_mode)
        root_storage = get_storage_provider("local", root_path=".")
        self.prompt_loader = PromptLoader(root_storage, base_dir="src/modules/real_estate/prompts")
        
        self.client = NaverNewsClient()
        self.llm = LLMClient()
        self.report_dir = "data/real_estate/news"
        
        # Phase 2: Advanced Scraper
        from .advanced_scraper import AdvancedScraper
        self.advanced_scraper = AdvancedScraper()

    def update_policy_knowledge(self) -> int:
        """Triggers the high-fidelity policy scraping and indexing."""
        return self.advanced_scraper.run_daily_scraping()

    def generate_daily_report(self) -> str:
        """
        Main workflow: Fetch News -> Load Context -> Analyze -> Save Report.
        Skips LLM call if today's report already exists (same-day cache).
        """
        # Cache check: return existing report if already generated today
        today = datetime.now().strftime("%Y-%m-%d")
        cached_file = os.path.join(self.report_dir, f"{today}_News.md")
        if os.path.exists(cached_file):
            logger.info(f"✅ [News] Today's report already exists, skipping LLM call.")
            with open(cached_file, "r", encoding="utf-8") as f:
                return f.read()

        # 1. Fetch News
        logger.info("📰 [News] Fetching latest real estate news...")
        items = self.client.search_news("부동산 정책 아파트 분양", display=30)
        if not items:
            return "❌ No news found or API error."
        
        # Convert to Domain Models — filter to last 7 days only
        cutoff = datetime.now(timezone.utc) - timedelta(days=7)
        articles = []
        for item in items:
            try:
                pub_dt = parsedate_to_datetime(item['pubDate'])
                if pub_dt.tzinfo is None:
                    pub_dt = pub_dt.replace(tzinfo=timezone.utc)
                if pub_dt < cutoff:
                    continue
            except Exception:
                pass  # 파싱 실패 시 포함
            articles.append(NewsArticle(
                title=item['title'].replace('<b>', '').replace('</b>', ''),
                link=item['originallink'] or item['link'],
                description=item['description'].replace('<b>', '').replace('</b>', ''),
                pub_date=item['pubDate']
            ))

        if not articles:
            return "❌ No recent news found (within 7 days)."

        # Format news list for LLM — include pub_date so LLM can judge recency
        news_text = ""
        for i, article in enumerate(articles, 1):
            news_text += f"{i}. [{article.pub_date}] {article.title}\n   - {article.description}\n"

        # 2. Load Historical Context (Last Report)
        history_context = self._get_last_report_summary()
        
        # 3. Analyze via LLM
        logger.info("🧠 [News] Analyzing trends with Gemini...")
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
        logger.info(f"✅ [News] Report saved to {filename}")

    def list_reports(self) -> List[str]:
        """
        Returns a sorted list of available news report filenames.
        """
        if not os.path.exists(self.report_dir):
            return []
            
        files = sorted(glob(os.path.join(self.report_dir, "*.md")), reverse=True)
        return [os.path.basename(f) for f in files]

    def get_report_content(self, filename: str) -> str:
        """
        Reads and returns the content of a specific report file.
        """
        filepath = os.path.join(self.report_dir, filename)
        if not os.path.exists(filepath):
            return "❌ File not found."
            
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                return f.read()
        except Exception as e:
            return f"❌ Error reading file: {str(e)}"
    def get_categorized_news(self, query: str = "부동산 정책 아파트 개발 GTX", display: int = 10) -> List[Dict[str, Any]]:
        """
        Fetches news and returns them as a list of dictionaries for internal use.
        """
        logger.info(f"📰 [News] Fetching news for query: {query}")
        items = self.client.search_news(query, display=display)
        if not items:
            return []
        
        articles = []
        for item in items:
            articles.append({
                "title": item['title'].replace('<b>', '').replace('</b>', ''),
                "link": item['originallink'] or item['link'],
                "description": item['description'].replace('<b>', '').replace('</b>', ''),
                "pub_date": item['pubDate']
            })
        return articles
