import json
import os
from datetime import date, datetime
from typing import Dict, Any, List, Optional

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

    # ─────────────────────────────────────────────
    # Job Methods (independently callable)
    # ─────────────────────────────────────────────

    def fetch_transactions(self, district_code: Optional[str] = None, year_month: Optional[str] = None) -> Dict[str, Any]:
        """Job 1: Fetch transactions from external API and save to ChromaDB.

        district_code=None → config.yaml의 전체 지구(수도권) 순회
        district_code 지정 → 해당 지구만 수집
        """
        from .monitor.service import TransactionMonitorService
        monitor_service = TransactionMonitorService()
        target_ym = year_month or datetime.now().strftime("%Y%m")

        # 수집 대상 지구 결정
        if district_code:
            targets = [{"code": district_code, "name": district_code}]
        else:
            targets = self.config.get("districts", [])
            logger.info(f"[Job1] 전체 수도권 수집 모드: {len(targets)}개 지구, {target_ym}")

        total_fetched = 0
        total_saved = 0
        results = []

        for district in targets:
            code = district["code"]
            name = district.get("name", code)
            try:
                transactions = monitor_service.get_daily_transactions(code, target_ym)
                saved = 0
                for tx in transactions:
                    try:
                        self.repository.save_transaction(tx)
                        saved += 1
                    except Exception as e:
                        logger.error(f"[Job1] Save failed {name} {tx.apt_name}: {e}")
                total_fetched += len(transactions)
                total_saved += saved
                if transactions:
                    results.append({"district": name, "fetched": len(transactions), "saved": saved})
                    logger.info(f"[Job1] {name}({code}): {len(transactions)}건 수집, {saved}건 저장")
            except Exception as e:
                logger.error(f"[Job1] Failed for {name}({code}): {e}")

        return {
            "fetched_count": total_fetched,
            "saved_count": total_saved,
            "district_count": len(targets),
            "year_month": target_ym,
            "details": results
        }

    def fetch_news(self) -> Dict[str, Any]:
        """Job 2: Fetch & analyze news, save daily markdown report."""
        logger.info("[Job2] Fetching & analyzing news...")
        result = self.news_service.generate_daily_report()
        success = not result.startswith("❌")
        return {"success": success, "report_date": datetime.now().strftime("%Y-%m-%d"), "summary": result[:200]}

    def fetch_macro_data(self) -> Dict[str, Any]:
        """Job 3: Fetch macro data from BOK and save to data/real_estate/macro/{date}_macro.json."""
        logger.info("[Job3] Fetching macro data from BOK...")
        macro_data = self.macro_service.fetch_latest_macro_data()
        macro_dict = macro_data.model_dump()

        macro_dir = os.path.join(os.getenv("LOCAL_STORAGE_PATH", "./data"), "real_estate", "macro")
        os.makedirs(macro_dir, exist_ok=True)
        today = datetime.now().strftime("%Y-%m-%d")
        filename = os.path.join(macro_dir, f"{today}_macro.json")
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(macro_dict, f, ensure_ascii=False, indent=2)
        logger.info(f"[Job3] Macro saved: {filename}")
        return {"success": True, "date": today, "macro": macro_dict}

    def generate_report(self, district_code: str = "11680", target_date: Optional[date] = None) -> Dict[str, Any]:
        """Job 4: Generate insight report using stored data (macro from file, txs from ChromaDB)."""
        if target_date is None:
            target_date = date.today()
        logger.info(f"[Job4] Generating report for {target_date}, {district_code}")

        # Load macro: prefer stored file, fallback to real-time
        macro_dict = self._load_stored_macro(target_date) or self.macro_service.fetch_latest_macro_data().model_dump()

        # Load transactions from ChromaDB
        where_clause = {"district_code": {"$eq": district_code}}
        stored_txs = self.repository.get_transactions(limit=50, where=where_clause)
        daily_txs = [t for t in stored_txs if str(t.get("deal_date", "")) == target_date.isoformat()][:15]
        if not daily_txs:
            daily_txs = stored_txs[:15]

        # Load persona + policy context
        persona_data = self._load_persona()
        from core.policy_fetcher import fetch_latest_financial_policies
        policy_context = fetch_latest_financial_policies()
        try:
            area = persona_data.get("user", {}).get("interest_areas", ["수도권"])[0]
            policy_facts = self.repository.search_policy(query=f"{area} 부동산 정책 공급 개발", n_results=3)
        except Exception:
            policy_facts = []
        budget_plan = self.calculator.calculate_budget(persona_data, policy_context)

        report_json = self.insight_orchestrator.generate_strategy(
            target_date=target_date,
            macro_dict=macro_dict,
            policy_context=policy_context,
            daily_txs=daily_txs,
            persona_data=persona_data.get("user", {}),
            policy_facts=policy_facts,
            budget_dict=budget_plan.model_dump(),
            fallback_note=f"({target_date} 저장 데이터 기준)"
        )

        score = report_json.get("_score", 0)
        self._save_report(report_json, target_date, len(daily_txs))
        return {"success": True, "score": score, "tx_count": len(daily_txs), "date": target_date.isoformat()}

    def run_insight_pipeline(self, district_code: str = "11680", target_date: Optional[date] = None, send_slack: bool = True) -> Dict[str, Any]:
        """Pipeline: Job1 → Job2 → Job3 → Job4 → Slack."""
        if target_date is None:
            target_date = date.today()
        year_month = target_date.strftime("%Y%m")

        results = {}
        results["job1"] = self.fetch_transactions(district_code, year_month)
        results["job2"] = self.fetch_news()
        results["job3"] = self.fetch_macro_data()
        results["job4"] = self.generate_report(district_code, target_date)

        if send_slack:
            try:
                from core.notify.slack import SlackSender
                sender = SlackSender()
                report_dir = os.path.join(os.getenv("LOCAL_STORAGE_PATH", "./data"), "real_estate", "reports")
                filename = os.path.join(report_dir, f"{target_date.isoformat()}_Report.json")
                if os.path.exists(filename):
                    with open(filename, "r", encoding="utf-8") as f:
                        saved = json.load(f)
                    sender.send_blocks(saved.get("blocks", []))
                    results["slack"] = "sent"
            except Exception as e:
                logger.error(f"[Pipeline] Slack send failed: {e}")
                results["slack"] = f"error: {e}"

        return results

    def _load_stored_macro(self, target_date: date) -> Optional[Dict[str, Any]]:
        """Loads today's saved macro JSON if available."""
        macro_dir = os.path.join(os.getenv("LOCAL_STORAGE_PATH", "./data"), "real_estate", "macro")
        filename = os.path.join(macro_dir, f"{target_date.isoformat()}_macro.json")
        if os.path.exists(filename):
            try:
                with open(filename, "r", encoding="utf-8") as f:
                    logger.info(f"[Job4] Using stored macro: {filename}")
                    return json.load(f)
            except Exception:
                pass
        return None

    def _load_persona(self) -> Dict[str, Any]:
        try:
            import yaml
            persona_path = os.path.join(os.path.dirname(__file__), "persona.yaml")
            with open(persona_path, "r", encoding="utf-8") as f:
                return yaml.safe_load(f)
        except Exception as e:
            logger.error(f"⚠️ Failed to load persona: {e}")
            return {"user": {}}
