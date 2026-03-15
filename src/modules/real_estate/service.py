import json
import os
from datetime import datetime, date
from typing import Dict, Any, List

from core.storage import get_storage_provider, StorageProvider
from core.prompt_loader import PromptLoader
from core.llm import LLMClient
from .models import RealEstateReport, RealEstateMetadata
from .repository import ChromaRealEstateRepository
from core.logger import get_logger

logger = get_logger(__name__)


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
        logger.info(f"⏱️ [{start_time.strftime('%H:%M:%S')}] [RealEstate] Starting log_tour process...")

        # 1. Extract metadata using Gemini
        _, prompt_str = self.prompt_loader.load(
            "parser",
            variables={"input_text": user_text}
        )
        
        logger.info(f"🧠 [{datetime.now().strftime('%H:%M:%S')}] [RealEstate] Extracting metadata (calling LLM)...")
        extraction = self.llm.generate_json(prompt_str)
        logger.info(f"✅ [{datetime.now().strftime('%H:%M:%S')}] [RealEstate] Metadata extraction complete.")
        
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
        logger.info(f"💾 [{datetime.now().strftime('%H:%M:%S')}] [RealEstate] Saving to repository...")
        self.repository.save(report)
        logger.info(f"✅ [{datetime.now().strftime('%H:%M:%S')}] [RealEstate] Save complete.")

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
        logger.info(f"⏱️ [{start_time.strftime('%H:%M:%S')}] [RealEstate] Starting search_tours process...")

        # 1. Generate search filter using Gemini
        _, prompt_str = self.prompt_loader.load(
            "searcher",
            variables={"input_text": user_query}
        )
        
        logger.info(f"🧠 [{datetime.now().strftime('%H:%M:%S')}] [RealEstate] Building search query (calling LLM)...")
        query_config = self.llm.generate_json(prompt_str)
        logger.info(f"✅ [{datetime.now().strftime('%H:%M:%S')}] [RealEstate] Search query built.")
        
        if "error" in query_config:
            return f"❌ Failed to build search query: {query_config['error']}"

        # 2. Search in ChromaDB
        logger.info(f"🔍 [{datetime.now().strftime('%H:%M:%S')}] [RealEstate] Searching repository with filter: {query_config.get('where')}")
        results = self.repository.search(
            query_text=query_config.get("query_text", ""),
            where=query_config.get("where"),
            n_results=3
        )
        logger.info(f"✅ [{datetime.now().strftime('%H:%M:%S')}] [RealEstate] Search complete. Found {len(results)} results.")

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
            
        logger.info(f"📊 [RealEstate] Generating Insight Report for {target_date.strftime('%Y-%m-%d')}...")
        
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
                logger.error(f"⚠️ [RealEstate] Failed to fetch data for {d_code}: {e}")

        # Filter for the exact target date
        daily_txs = [tx.__dict__ for tx in all_transactions if tx.deal_date == target_date]
        
        # Fallback: If no transactions for the exact date, take latest 20 from gathered month
        if not daily_txs and all_transactions:
            logger.warning(f"⚠️ [RealEstate] No transactions for {target_date}, fallback to latest available in {target_ym}")
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
            logger.error(f"⚠️ [RealEstate] Failed to load persona.yaml: {e}")

        # 4. Fetch 2026 Financial Policy Context Dynamically
        from core.policy_fetcher import fetch_latest_financial_policies
        policy_context = fetch_latest_financial_policies()

        # 5. Build Initial Variables for LLM
        variables = {
            "target_date": target_date.strftime("%Y-%m-%d"),
            "tx_data": json.dumps(daily_txs, ensure_ascii=False, default=str),
            "news_data": json.dumps(news_list, ensure_ascii=False),
            "persona_data": json.dumps(persona_data, ensure_ascii=False),
            "policy_context": json.dumps(policy_context, ensure_ascii=False),
            "fallback_note": fallback_note,
            "validator_feedback": "" # Initial run has no feedback
        }

        # 6. Self-Reflection Loop (Max 100 iterations)
        MAX_ITERATIONS = 100
        current_iter = 0
        best_report_json = None
        best_score = -1

        while current_iter < MAX_ITERATIONS:
            current_iter += 1
            logger.info(f"🧠 [RealEstate] Generating Report (Iteration {current_iter}/{MAX_ITERATIONS})...")
            
            _, prompt_str = self.prompt_loader.load("insight_parser", variables=variables)
            report_json = self.llm.generate_json(prompt_str)
            
            if "error" in report_json:
                 logger.error(f"❌ [RealEstate] Insight report generation failed on iter {current_iter}: {report_json['error']}")
                 if best_report_json is None:
                     return [{"type": "section", "text": {"type": "mrkdwn", "text": "⚠️ 인사이트 리포트 생성 중 오류가 발생했습니다."}}]
                 break
            
            # Extract blocks logic to strings to pass into validator
            extracted_blocks = []
            if isinstance(report_json, dict) and "blocks" in report_json:
                if isinstance(report_json["blocks"], list):
                    extracted_blocks = report_json["blocks"]
                elif isinstance(report_json["blocks"], dict) and "blocks" in report_json["blocks"]:
                    extracted_blocks = report_json["blocks"]["blocks"]
            elif isinstance(report_json, list):
                extracted_blocks = report_json

            if not extracted_blocks:
                logger.warning(f"⚠️ [RealEstate] Could not extract blocks on iter {current_iter}. Trying again...")
                variables["validator_feedback"] = "JSON 구조 오류: 최상위에 'blocks' 리스트 객체 형태로 반환하십시오."
                continue
            
            # --- VALIDATION STEP ---
            logger.info(f"⚖️ [RealEstate] Validating Report {current_iter} Logical Soundness...")
            _, validator_prompt_str = self.prompt_loader.load(
                "insight_validator",
                variables={
                    "report_json": json.dumps(extracted_blocks, ensure_ascii=False),
                    "persona_data": json.dumps(persona_data, ensure_ascii=False),
                    "policy_context": json.dumps(policy_context, ensure_ascii=False)
                }
            )
            
            val_result = self.llm.generate_json(validator_prompt_str)
            score = val_result.get("score", 0)
            reasoning = val_result.get("reasoning", "No reasoning provided.")
            feedback = val_result.get("feedbackForImprovement", "")
            
            logger.info(f"📊 [RealEstate] Iteration {current_iter} Score: {score}/10 | Reason: {reasoning}")
            
            if score > best_score:
                best_score = score
                best_report_json = extracted_blocks
                
            if score >= 8:
                logger.info(f"✅ [RealEstate] Acceptable score ({score}>=8) achieved. Breaking loop.")
                break
            else:
                logger.warning(f"⚠️ [RealEstate] Score {score} is too low. Providing feedback and retrying.")
                # Inject feedback for next iteration so LLM can fix its mistakes
                variables["validator_feedback"] = f"이전 생성물 비인가 사유: {reasoning}\n수정 요구사항: {feedback}"

        
        # 7. Final Output Extraction & Warning Inject
        report_blocks = best_report_json if best_report_json else []
        
        if not report_blocks:
             logger.error("❌ [RealEstate] Failed to generate a valid report after all iterations.")
             return [{"type": "section", "text": {"type": "mrkdwn", "text": "⚠️ 인사이트 리포트 생성 중 치명적 오류가 발생했습니다."}}]

        # If we exhausted 10 iterations and still didn't reach score 8, append a warning
        if best_score < 8:
             logger.warning(f"🚨 [RealEstate] Final report only achieved score {best_score}/10.")
             report_blocks.append({"type": "divider"})
             report_blocks.append({
                 "type": "section",
                 "text": {
                     "type": "mrkdwn",
                     "text": "⚠️ *[AI 검증 모듈 경고]*\n본 액션플랜은 내부 논리적 타당성 채점에서 8점 미만을 기록하였습니다. 산술적 예산 산정(LTV/DSR 중첩 계산)에 구조적 비약이 있을 수 있으니 참고 목적으로만 열람하시고, 실제 진행 시 주거래 은행과의 상세한 상담을 필히 권장합니다."
                 }
             })

        logger.info(f"✅ [RealEstate] Insight report generation complete (Score {best_score}, {len(report_blocks)} blocks).")
        return report_blocks
