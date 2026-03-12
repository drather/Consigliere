import json
import os
from datetime import datetime, date
from typing import Dict, Any, List

from core.storage import get_storage_provider, StorageProvider
from core.prompt_loader import PromptLoader
from core.llm import LLMClient
from .models import RealEstateReport, RealEstateMetadata
from .repository import ChromaRealEstateRepository

class RealEstateAgent:
    def __init__(self, storage_mode: str = "local"):
        self.storage: StorageProvider = get_storage_provider(storage_mode)
        # Always use local project root for prompts
        root_storage = get_storage_provider("local", root_path=".")
        self.prompt_loader = PromptLoader(root_storage, base_dir="src/modules/real_estate/prompts")
        
        # LLM Client
        self.llm = LLMClient()
        
        # Repository (ChromaDB)
        self.repository = ChromaRealEstateRepository()

    def log_tour(self, user_text: str) -> str:
        """
        Parses tour notes and saves them into the vector database.
        """
        start_time = datetime.now()
        print(f"⏱️ [{start_time.strftime('%H:%M:%S')}] [RealEstate] Starting log_tour process...")

        # 1. Extract metadata using Gemini
        _, prompt_str = self.prompt_loader.load(
            "parser",
            variables={"input_text": user_text}
        )
        
        print(f"🧠 [{datetime.now().strftime('%H:%M:%S')}] [RealEstate] Extracting metadata (calling LLM)...")
        extraction = self.llm.generate_json(prompt_str)
        print(f"✅ [{datetime.now().strftime('%H:%M:%S')}] [RealEstate] Metadata extraction complete.")
        
        if "error" in extraction:
            return f"❌ Failed to parse tour note: {extraction['error']}"

        # 2. Construct Domain Model
        metadata = RealEstateMetadata(**extraction)
        report = RealEstateReport(
            report_id=metadata.complex_name, # Use complex name as ID
            metadata=metadata,
            content=user_text
        )

        # 3. Save to Repository
        print(f"💾 [{datetime.now().strftime('%H:%M:%S')}] [RealEstate] Saving to repository...")
        self.repository.save(report)
        print(f"✅ [{datetime.now().strftime('%H:%M:%S')}] [RealEstate] Save complete.")

        elapsed = (datetime.now() - start_time).total_seconds()
        return (
            f"✅ Real Estate Tour Logged (took {elapsed:.2f}s).\n"
            f"- Complex: {metadata.complex_name}\n"
            f"- Price: {f'{metadata.price:,} KRW' if metadata.price else 'N/A'}\n"
            f"- School: {'Yes' if metadata.has_elementary_school else 'No'}"
        )

    def search_tours(self, user_query: str) -> str:
        """
        Translates question into query and retrieves matching reports.
        """
        start_time = datetime.now()
        print(f"⏱️ [{start_time.strftime('%H:%M:%S')}] [RealEstate] Starting search_tours process...")

        # 1. Generate search filter using Gemini
        _, prompt_str = self.prompt_loader.load(
            "searcher",
            variables={"input_text": user_query}
        )
        
        print(f"🧠 [{datetime.now().strftime('%H:%M:%S')}] [RealEstate] Building search query (calling LLM)...")
        query_config = self.llm.generate_json(prompt_str)
        print(f"✅ [{datetime.now().strftime('%H:%M:%S')}] [RealEstate] Search query built.")
        
        if "error" in query_config:
            return f"❌ Failed to build search query: {query_config['error']}"

        # 2. Search in ChromaDB
        print(f"🔍 [{datetime.now().strftime('%H:%M:%S')}] [RealEstate] Searching repository with filter: {query_config.get('where')}")
        results = self.repository.search(
            query_text=query_config.get("query_text", ""),
            where=query_config.get("where"),
            n_results=3
        )
        print(f"✅ [{datetime.now().strftime('%H:%M:%S')}] [RealEstate] Search complete. Found {len(results)} results.")

        if not results:
            return "🔍 No matching complexes found for your criteria."

        # 3. Format Response
        response = f"🔍 I found {len(results)} matching complexes (took {(datetime.now() - start_time).total_seconds():.2f}s):\n\n"
        for i, report in enumerate(results, 1):
            m = report.metadata
            response += (
                f"{i}. **{m.complex_name}**\n"
                f"   - Price: {f'{m.price:,} KRW' if m.price else 'N/A'}\n"
                f"   - Features: {', '.join(m.pros)}\n"
                f"   - Note: {report.content[:100]}...\n\n"
            )
        
        return response

    def get_daily_summary(self, district_code: str, target_date: date) -> List[Dict[str, Any]]:
        """
        Fetches transactions for the target date, deduplicates them, and creates a Slack Block Kit message.
        """
        from .monitor.service import TransactionMonitorService
        monitor_service = TransactionMonitorService()
        
        # 1. Fetch transactions for the given month (API requirement)
        target_ym = target_date.strftime("%Y%m")
        transactions = monitor_service.get_daily_transactions(district_code, target_ym)
        
        # 2. Filter for the exact target date
        daily_txs = [tx for tx in transactions if tx.deal_date == target_date]
        
        if not daily_txs:
             return [
                 {
                     "type": "section",
                     "text": {
                         "type": "mrkdwn",
                         "text": f"*{target_date.strftime('%Y-%m-%d')}* 부동산 실거래가 내역이 없습니다."
                     }
                 }
             ]

        # 3. Deduplicate (same apartment, similar area/price)
        # Simplified dedup: group by apt_name and exclusive_area (rounded to 1 decimal)
        grouped_txs = {}
        for tx in daily_txs:
            key = f"{tx.apt_name}_{round(tx.exclusive_area, 1)}"
            if key not in grouped_txs:
                grouped_txs[key] = []
            grouped_txs[key].append(tx)
            
        dedup_txs = []
        for key, tx_list in grouped_txs.items():
            # If multiple records, we just take the first one but note the count
            primary_tx = tx_list[0]
            count = len(tx_list)
            dedup_txs.append((primary_tx, count))

        # 4. Sort by price descending
        dedup_txs.sort(key=lambda x: x[0].price, reverse=True)

        # 5. Build Slack Block Kit
        blocks = [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": f"🏢 {target_date.strftime('%Y-%m-%d')} 실거래가 요약",
                    "emoji": True
                }
            },
            {
                "type": "divider"
            }
        ]
        
        for tx, count in dedup_txs:
             # Convert price to Eok and Manwon (e.g. 15억 5000)
             eok = tx.price // 100000000
             man = (tx.price % 100000000) // 10000
             price_str = f"{eok}억"
             if man > 0:
                 price_str += f" {man}만"
             
             count_str = f"외 {count-1}건" if count > 1 else ""
             
             # Block structure
             blocks.append({
                 "type": "section",
                 "text": {
                     "type": "mrkdwn",
                     "text": f"*{tx.apt_name}* ({tx.exclusive_area:g}m² / {tx.floor}층) {count_str}\n💰 *{price_str}*원  |  🏗️ {tx.build_year}년식"
                 },
                 "accessory": {
                     "type": "button",
                     "text": {
                         "type": "plain_text",
                         "text": "지도 보기",
                         "emoji": True
                     },
                     "value": "view_map",
                     "url": tx.naver_map_url,
                     "action_id": f"map_btn_{tx.apt_name}"
                 }
             })

        return blocks
    def generate_insight_report(self, district_code: str = "11680", target_date: date = None) -> List[Dict[str, Any]]:
        """
        Generates a comprehensive insight report combining transactions and news.
        """
        if target_date is None:
            target_date = date.today()
            
        print(f"📊 [RealEstate] Generating Insight Report for {target_date.strftime('%Y-%m-%d')}...")
        
        # 1. Fetch Transactions
        from .monitor.service import TransactionMonitorService
        monitor_service = TransactionMonitorService()
        target_ym = target_date.strftime("%Y%m")
        transactions = monitor_service.get_daily_transactions(district_code, target_ym)
        daily_txs = [tx.__dict__ for tx in transactions if tx.deal_date == target_date]
        
        # 2. Fetch News
        from .news.service import NewsService
        news_service = NewsService()
        news_list = news_service.get_categorized_news()
        
        # 3. Load Persona Data
        persona_data = {}
        try:
            import yaml
            persona_path = os.path.join(os.path.dirname(__file__), "persona.yaml")
            if os.path.exists(persona_path):
                with open(persona_path, "r", encoding="utf-8") as f:
                    persona_data = yaml.safe_load(f)
        except Exception as e:
            print(f"⚠️ [RealEstate] Failed to load persona.yaml: {e}")

        # 4. Call LLM for Insights & Formatting
        _, prompt_str = self.prompt_loader.load(
            "insight_parser",
            variables={
                "tx_data": json.dumps(daily_txs, ensure_ascii=False, default=str),
                "news_data": json.dumps(news_list, ensure_ascii=False),
                "persona_data": json.dumps(persona_data, ensure_ascii=False)
            }
        )
        
        print(f"🧠 [RealEstate] Analyzing insights and formatting (calling LLM)...")
        report_blocks = self.llm.generate_json(prompt_str)
        
        if "error" in report_blocks:
             print(f"❌ [RealEstate] Insight report generation failed: {report_blocks['error']}")
             return [{"type": "section", "text": {"type": "mrkdwn", "text": "⚠️ 인사이트 리포트 생성 중 오류가 발생했습니다."}}]

        print(f"✅ [RealEstate] Insight report generation complete.")
        return report_blocks
