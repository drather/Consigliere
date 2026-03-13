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
        
        # 1. Fetch Transactions from Multiple Districts (Metropolitan Area)
        # Major areas: Gangnam(11680), Songpa(11710), Seocho(11650), Seongdong(11200), Yongsan(11170), 
        # Bundang(41135), Gwacheon(41290), Gwangmyeong(41210), Hanam(41450)
        districts = {
            "11680": "강남구", "11710": "송파구", "11650": "서초구", 
            "11200": "성동구", "11170": "용산구", "41135": "분당구",
            "41290": "과천시", "41210": "광명시", "41450": "하남시"
        }
        
        from .monitor.service import TransactionMonitorService
        monitor_service = TransactionMonitorService()
        target_ym = target_date.strftime("%Y%m")
        
        all_transactions = []
        for d_code in districts.keys():
            try:
                txs = monitor_service.get_daily_transactions(d_code, target_ym)
                all_transactions.extend(txs)
            except Exception as e:
                print(f"⚠️ [RealEstate] Failed to fetch data for {d_code}: {e}")

        # Filter for the exact target date
        daily_txs = [tx.__dict__ for tx in all_transactions if tx.deal_date == target_date]
        
        # Fallback: If no transactions for the exact date, take latest 20 from gathered month
        if not daily_txs and all_transactions:
            print(f"⚠️ [RealEstate] No transactions for {target_date}, fallback to latest available in {target_ym}")
            sorted_txs = sorted(all_transactions, key=lambda x: x.deal_date, reverse=True)
            daily_txs = [tx.__dict__ for tx in sorted_txs[:20]]
            fallback_note = f"(안내) {target_date.strftime('%Y-%m-%d')} 당일 실거래 내역이 없어, 해당 월({target_ym})의 최신 데이터로 대체되었습니다."
        else:
            fallback_note = ""
        
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

        # 4. Define 2026 Financial Policy Context
        policy_context = {
            "standard_year": 2026,
            "ltv": {
                "first_time_buyer": "80% (최대 6억)",
                "non_regulated_area": "70%",
                "regulated_area": "50%"
            },
            "dsr": {
                "limit": "40%",
                "stress_dsr": "3단계 본격 시행 (수도권 스트레스 금리 100% 적용, 약 1.5%p 가산)"
            },
            "news": "지방권은 2026년 상반기까지 스트레스 DSR 2단계 한시 유지, 수도권은 3단계 강화 적용"
        }

        # 5. Call LLM for Insights & Formatting
        _, prompt_str = self.prompt_loader.load(
            "insight_parser",
            variables={
                "target_date": target_date.strftime("%Y-%m-%d"),
                "tx_data": json.dumps(daily_txs, ensure_ascii=False, default=str),
                "news_data": json.dumps(news_list, ensure_ascii=False),
                "persona_data": json.dumps(persona_data, ensure_ascii=False),
                "policy_context": json.dumps(policy_context, ensure_ascii=False),
                "fallback_note": fallback_note
            }
        )
        
        print(f"🧠 [RealEstate] Analyzing insights and formatting (calling LLM)...")
        report_json = self.llm.generate_json(prompt_str)
        
        if "error" in report_json:
             print(f"❌ [RealEstate] Insight report generation failed: {report_json['error']}")
             return [{"type": "section", "text": {"type": "mrkdwn", "text": "⚠️ 인사이트 리포트 생성 중 오류가 발생했습니다."}}]

        # Extract blocks list if wrapped in a dictionary (Aggressive check)
        report_blocks = []
        if isinstance(report_json, dict):
            # Case 1: {"blocks": [...]}
            if "blocks" in report_json and isinstance(report_json["blocks"], list):
                report_blocks = report_json["blocks"]
            # Case 2: {"blocks": {"blocks": [...]}}
            elif "blocks" in report_json and isinstance(report_json["blocks"], dict) and "blocks" in report_json["blocks"]:
                report_blocks = report_json["blocks"]["blocks"]
            else:
                # If it's a dict but no blocks key, but maybe it IS the block list? No, probably error.
                print(f"❌ [RealEstate] Unexpected dictionary format: {report_json.keys()}")
                return [{"type": "section", "text": {"type": "mrkdwn", "text": "⚠️ 인사이트 리포트 형식이 올바르지 않습니다."}}]
        elif isinstance(report_json, list):
            report_blocks = report_json
        
        if not report_blocks:
             print(f"❌ [RealEstate] Failed to extract blocks from: {report_json}")
             return [{"type": "section", "text": {"type": "mrkdwn", "text": "⚠️ 인사이트 리포트 생성 중 오류가 발생했습니다."}}]

        print(f"✅ [RealEstate] Insight report generation complete (extracted {len(report_blocks)} blocks).")
        return report_blocks
