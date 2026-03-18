import json
import os
from datetime import date, datetime
from typing import Dict, Any, List

from core.storage import get_storage_provider, StorageProvider
from core.prompt_loader import PromptLoader
from core.llm import LLMClient
from core.logger import get_logger
from .repository import ChromaRealEstateRepository
from .config import RealEstateConfig
from .tour_service import TourService
from .insight_orchestrator import InsightOrchestrator
from .presenter import RealEstatePresenter
from .macro.bok_service import MacroService
from .news.service import NewsService
from .calculator import FinancialCalculator

logger = get_logger(__name__)

class RealEstateAgent:
    """
    Facade for the Real Estate module. 
    Delegates specialized tasks to internal services for SOLID compliance.
    """
    def __init__(self, storage_mode: str = "local"):
        self.config = RealEstateConfig()
        
        # Core Infrastructure
        self.storage: StorageProvider = get_storage_provider(storage_mode)
        root_storage = get_storage_provider("local", root_path=".")
        self.prompt_loader = PromptLoader(root_storage, base_dir="src/modules/real_estate/prompts")
        self.llm = LLMClient()
        self.repository = ChromaRealEstateRepository()
        
        # Specialized Services
        self.tour_service = TourService(self.llm, self.prompt_loader, self.repository)
        self.insight_orchestrator = InsightOrchestrator(self.llm, self.prompt_loader)
        self.presenter = RealEstatePresenter()
        self.macro_service = MacroService()
        self.news_service = NewsService()
        self.calculator = FinancialCalculator()

    def log_tour(self, user_text: str) -> str:
        return self.tour_service.log_tour(user_text)

    def search_tours(self, user_query: str) -> str:
        return self.tour_service.search_tours(user_query)

    def get_daily_summary(self, district_code: str, target_date: date) -> List[Dict[str, Any]]:
        """
        Fetches daily transactions and returns Slack Block Kit formatting via Presenter.
        """
        from .monitor.service import TransactionMonitorService
        monitor_service = TransactionMonitorService()
        
        target_ym = target_date.strftime("%Y%m")
        transactions = monitor_service.get_daily_transactions(district_code, target_ym)
        daily_txs = [tx for tx in transactions if tx.deal_date == target_date]
        
        if not daily_txs:
             return [{"type": "section", "text": {"type": "mrkdwn", "text": f"*{target_date.strftime('%Y-%m-%d')}* 내역이 없습니다."}}]

        # Deduplicate
        grouped_txs = {}
        for tx in daily_txs:
            key = f"{tx.apt_name}_{round(tx.exclusive_area, 1)}"
            if key not in grouped_txs: grouped_txs[key] = []
            grouped_txs[key].append(tx)
            
        dedup_txs = sorted([(v[0], len(v)) for v in grouped_txs.values()], key=lambda x: x[0].price, reverse=True)
        return self.presenter.format_daily_summary(target_date, dedup_txs)

    def generate_insight_report(self, district_code: str = "11680", target_date: date = None) -> List[Dict[str, Any]]:
        """
        Orchestrates multi-source data gathering and triggers the Multi-Agent Strategy loop.
        """
        if target_date is None: target_date = date.today()
        logger.info(f"📊 [RealEstateAgent] Generating report for {target_date}...")

        # 1. Gather Data
        from .monitor.service import TransactionMonitorService
        monitor_service = TransactionMonitorService()
        target_ym = target_date.strftime("%Y%m")
        
        # Use districts from dynamic config
        district_list = self.config.get("districts", [{"code": "11680", "name": "강남"}])
        all_transactions = []
        for d in district_list:
            try:
                all_transactions.extend(monitor_service.get_daily_transactions(d["code"], target_ym))
            except Exception as e:
                logger.error(f"⚠️ [RealEstateAgent] Data fetch failed for {d['code']}: {e}")

        daily_txs = [tx.__dict__ for tx in all_transactions if tx.deal_date == target_date][:15]
        if not daily_txs: daily_txs = [tx.__dict__ for tx in sorted(all_transactions, key=lambda x: x.deal_date, reverse=True)[:15]]
        
        # 2. External Contexts
        persona_data = self._load_persona()
        from core.policy_fetcher import fetch_latest_financial_policies
        policy_context = fetch_latest_financial_policies()
        macro_data = self.macro_service.fetch_latest_macro_data()
        
        # RAG for Policy Facts
        try:
            area = persona_data.get("user", {}).get("interest_areas", ["수도권"])[0]
            policy_facts = self.repository.search_policy(query=f"{area} 부동산 정책 공급 개발", n_results=3)
        except:
            policy_facts = []

        # 3. Dynamic Budget
        budget_plan = self.calculator.calculate_budget(persona_data, policy_context)

        # 4. Agent Orchestration (Phase 3 Loop)
        report_json = self.insight_orchestrator.generate_strategy(
            target_date=target_date,
            macro_dict=macro_data.model_dump(),
            policy_context=policy_context,
            daily_txs=daily_txs,
            persona_data=persona_data.get("user", {}),
            policy_facts=policy_facts,
            budget_dict=budget_plan.model_dump(),
            fallback_note=f"({target_date} 데이터 기준)"
        )

        self._save_report(report_json, target_date, len(daily_txs))
        return report_json.get("blocks", [])

    def _save_report(self, report_json: Dict[str, Any], target_date: date, tx_count: int) -> None:
        """생성된 리포트를 JSON 파일로 저장한다."""
        try:
            report_dir = os.path.join(os.getenv("LOCAL_STORAGE_PATH", "./data"), "real_estate", "reports")
            os.makedirs(report_dir, exist_ok=True)

            score = report_json.pop("_score", 0)
            save_data = {
                "date": target_date.isoformat(),
                "score": score,
                "tx_count": tx_count,
                "created_at": datetime.now().isoformat(),
                "blocks": report_json.get("blocks", [])
            }

            filename = os.path.join(report_dir, f"{target_date.isoformat()}_Report.json")
            with open(filename, "w", encoding="utf-8") as f:
                json.dump(save_data, f, ensure_ascii=False, indent=2)
            logger.info(f"✅ [RealEstateAgent] Report saved: {filename}")
        except Exception as e:
            logger.error(f"⚠️ [RealEstateAgent] Failed to save report: {e}")

    def _load_persona(self) -> Dict[str, Any]:
        try:
            import yaml
            persona_path = os.path.join(os.path.dirname(__file__), "persona.yaml")
            with open(persona_path, "r", encoding="utf-8") as f:
                return yaml.safe_load(f)
        except Exception as e:
            logger.error(f"⚠️ Failed to load persona: {e}")
            return {"user": {}}
