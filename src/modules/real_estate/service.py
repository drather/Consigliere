import asyncio
import json
import os
import aiohttp
from datetime import date, datetime, timedelta
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
        """Job 1: aiohttp 비동기 병렬 수집 + 7일 필터 + 1년 데이터 삭제.

        district_code=None → config.yaml의 전체 지구(수도권) 수집
        district_code 지정 → 해당 지구만 수집
        """
        from .monitor.api_client import MOLITClient

        target_ym = year_month or datetime.now().strftime("%Y%m")
        today = date.today()
        cutoff_3days = today - timedelta(days=7)
        cutoff_1year = today - timedelta(days=365)

        if district_code:
            targets = [{"code": district_code, "name": district_code}]
        else:
            targets = self.config.get("districts", [])
            logger.info(f"[Job1] 비동기 수집: {len(targets)}개 지구, {target_ym}")

        # Step 0: 1년 이상 된 데이터 삭제
        deleted = self.repository.delete_old_transactions(cutoff_1year)

        # Step 1: 비동기 병렬 fetch
        molit_client = MOLITClient()
        loop = asyncio.new_event_loop()
        try:
            fetched_results = loop.run_until_complete(
                self._async_fetch_all(targets, target_ym, molit_client, cutoff_3days)
            )
        finally:
            loop.close()

        # Step 2: 직렬 ChromaDB save (onnxruntime 임베딩 동시 실행 시 OOM)
        total_fetched, total_saved, results = 0, 0, []
        for name, code, txs in fetched_results:
            total_fetched += len(txs)
            if not txs:
                continue
            try:
                saved = self.repository.save_transactions_batch(txs)
                total_saved += saved
                results.append({"district": name, "fetched": len(txs), "saved": saved})
                logger.info(f"[Job1] {name}({code}): {len(txs)}건(7일) 수집, {saved}건 저장")
            except Exception as e:
                logger.error(f"[Job1] Save 실패 {name}({code}): {e}")

        return {
            "fetched_count": total_fetched,
            "saved_count": total_saved,
            "district_count": len(targets),
            "year_month": target_ym,
            "deleted_old_count": deleted,
            "details": results,
        }

    async def _async_fetch_all(self, targets, target_ym, molit_client, cutoff_3days):
        semaphore = asyncio.Semaphore(2)
        async with aiohttp.ClientSession() as session:
            tasks = [
                self._fetch_one_district(d, target_ym, semaphore, session, molit_client, cutoff_3days)
                for d in targets
            ]
            return await asyncio.gather(*tasks)

    async def _fetch_one_district(self, district, target_ym, semaphore, session, molit_client, cutoff_3days):
        from .monitor.service import _parse_item_to_transaction
        code = district["code"]
        name = district.get("name", code)
        async with semaphore:
            for attempt in range(3):
                try:
                    params = {
                        "serviceKey": molit_client.service_key,
                        "pageNo": "1",
                        "numOfRows": "100",
                        "LAWD_CD": code,
                        "DEAL_YMD": target_ym,
                    }
                    async with session.get(
                        molit_client.BASE_URL, params=params,
                        timeout=aiohttp.ClientTimeout(total=15)
                    ) as resp:
                        if resp.status == 429:
                            wait = 2 ** attempt
                            logger.warning(f"[Job1] 429 {name}({code}), {wait}s 재시도")
                            await asyncio.sleep(wait)
                            continue
                        xml_text = await resp.text()
                        success_codes = ["<resultCode>0</resultCode>", "<resultCode>00</resultCode>", "<resultCode>000</resultCode>"]
                        if "<resultCode>" in xml_text and not any(c in xml_text for c in success_codes):
                            logger.error(f"[Job1] API 오류 {name}: {xml_text[:150]}")
                            return name, code, []
                        dict_items = molit_client.parse_xml_to_dict_list(xml_text)
                        all_txs = [t for item in dict_items if (t := _parse_item_to_transaction(item, code)) is not None]
                        recent = [tx for tx in all_txs if tx.deal_date >= cutoff_3days]
                        return name, code, recent
                except asyncio.TimeoutError:
                    logger.error(f"[Job1] Timeout {name}({code}) ({attempt+1}/3)")
                except Exception as e:
                    logger.error(f"[Job1] 오류 {name}({code}): {e}")
                    return name, code, []
        return name, code, []

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

    def generate_report(self, district_code: Optional[str] = None, target_date: Optional[date] = None) -> Dict[str, Any]:
        """Job 4: Generate insight report using stored data (macro from file, txs from ChromaDB).

        district_code=None → persona.interest_areas 기반 4개 구 동시 수집
        district_code 지정 → 해당 구만 수집
        """
        if target_date is None:
            target_date = date.today()
        logger.info(f"[Job4] Generating report for {target_date}, district_code={district_code}")

        # Load macro: prefer stored file, fallback to real-time
        macro_dict = self._load_stored_macro(target_date) or self.macro_service.fetch_latest_macro_data().model_dump()
        # Phase 3: Load Job2 news summary
        news_summary = self._load_stored_news(target_date)

        # Load persona + policy context
        persona_data = self._load_persona()

        # Resolve target districts
        target_codes = self._resolve_interest_districts(persona_data, district_code)
        logger.info(f"[Job4] Collecting from districts: {target_codes}")

        # Load transactions from ChromaDB across all target districts
        all_txs: List[Dict[str, Any]] = []
        for code in target_codes:
            try:
                where_clause = {"district_code": {"$eq": code}}
                txs = self.repository.get_transactions(limit=50, where=where_clause)
                all_txs.extend(txs)
            except Exception as e:
                logger.error(f"[Job4] ChromaDB query failed for {code}: {e}")

        # Dedup by composite key
        seen_keys = set()
        deduped_txs = []
        for tx in all_txs:
            key = f"{tx.get('apt_name')}_{tx.get('exclusive_area')}_{tx.get('deal_date')}_{tx.get('floor')}"
            if key not in seen_keys:
                seen_keys.add(key)
                deduped_txs.append(tx)

        daily_txs = [t for t in deduped_txs if str(t.get("deal_date", "")) == target_date.isoformat()][:20]
        if not daily_txs:
            daily_txs = deduped_txs[:20]

        # Enrich with area intel
        area_intel = self._load_area_intel()
        daily_txs = self._enrich_transactions(daily_txs, area_intel)

        from core.policy_fetcher import fetch_latest_financial_policies
        policy_context = fetch_latest_financial_policies()
        try:
            area = persona_data.get("user", {}).get("interest_areas", ["수도권"])[0]
            policy_facts = self.repository.search_policy(query=f"{area} 부동산 정책 공급 개발", n_results=3)
        except Exception:
            policy_facts = []
        budget_plan = self.calculator.calculate_budget(persona_data, policy_context)

        # Phase 1: 예산 이하 단지만 LLM에 전달 (구조적 강제)
        budget_ceiling = budget_plan.final_max_price
        pre_filter_count = len(daily_txs)
        daily_txs = [tx for tx in daily_txs if tx.get("price", 0) <= budget_ceiling]
        filtered_tx_count = pre_filter_count - len(daily_txs)
        if filtered_tx_count > 0:
            logger.info(f"[Job4] Budget filter: {filtered_tx_count}건 제거 (한도: {budget_ceiling/1e8:.1f}억, 잔여: {len(daily_txs)}건)")

        report_json = self.insight_orchestrator.generate_strategy(
            target_date=target_date,
            macro_dict=macro_dict,
            policy_context=policy_context,
            daily_txs=daily_txs,
            persona_data=persona_data.get("user", {}),
            policy_facts=policy_facts,
            budget_dict=budget_plan.model_dump(),
            filtered_tx_count=filtered_tx_count,
            news_summary=news_summary,
            fallback_note=f"({target_date} 저장 데이터 기준, {len(target_codes)}개 구)"
        )

        score = report_json.get("_score", 0)
        self._save_report(report_json, target_date, len(daily_txs))
        return {"success": True, "score": score, "tx_count": len(daily_txs), "date": target_date.isoformat()}

    def run_insight_pipeline(self, district_code: Optional[str] = None, target_date: Optional[date] = None, send_slack: bool = True) -> Dict[str, Any]:
        """Pipeline: Job1 → Job2 → Job3 → Job4 → Slack.

        district_code=None → persona.interest_areas 기반 4개 구 동시 수집
        """
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
                    sender.send("📊 부동산 인사이트 리포트가 도착했습니다.", blocks=saved.get("blocks", []))
                    results["slack"] = "sent"
            except Exception as e:
                logger.error(f"[Pipeline] Slack send failed: {e}")
                results["slack"] = f"error: {e}"

        return results

    def _resolve_interest_districts(self, persona_data: Dict[str, Any], override_code: Optional[str]) -> List[str]:
        """persona.interest_areas 이름 → config.yaml 코드 목록 변환.

        override_code가 지정된 경우 그 단일 코드만 반환.
        """
        if override_code:
            return [override_code]

        interest_areas = persona_data.get("user", {}).get("interest_areas", [])
        if not interest_areas:
            return ["11680"]

        all_districts = self.config.get("districts", [])
        name_to_code = {d["name"]: d["code"] for d in all_districts}

        codes = []
        for area in interest_areas:
            # 직접 매핑 시도
            if area in name_to_code:
                codes.append(name_to_code[area])
                continue
            # 부분 매핑: "성남시 분당구" → "분당구" 등
            matched = next((d["code"] for d in all_districts if area in d["name"] or d["name"] in area), None)
            if matched:
                codes.append(matched)
            else:
                logger.warning(f"[Job4] interest_area '{area}' not found in config.yaml — skipping")

        return codes if codes else ["11680"]

    def _load_area_intel(self) -> Dict[str, Any]:
        """data/static/area_intel.json 로드. 파일이 없으면 빈 dict 반환."""
        intel_path = os.path.join(os.path.dirname(__file__), "..", "..", "..", "data", "static", "area_intel.json")
        intel_path = os.path.abspath(intel_path)
        if not os.path.exists(intel_path):
            logger.warning(f"[Job4] area_intel.json not found at {intel_path}")
            return {}
        try:
            with open(intel_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"[Job4] Failed to load area_intel.json: {e}")
            return {}

    def _enrich_transactions(self, txs: List[Dict[str, Any]], area_intel: Dict[str, Any]) -> List[Dict[str, Any]]:
        """각 거래 dict에 commute_minutes, nearest_stations, school_zone, reconstruction 정보 부착.

        매칭 우선순위: apt_name → notable_complexes 포함 여부 → 구 기본값
        """
        if not area_intel:
            return txs

        districts_intel = area_intel.get("districts", {})
        apt_overrides = area_intel.get("apartment_overrides", {})

        enriched = []
        for tx in txs:
            tx = dict(tx)
            apt_name = tx.get("apt_name", "")
            district_code = str(tx.get("district_code", ""))

            # 재건축 정보: apartment_overrides에서 exact match
            for override_key, override_val in apt_overrides.items():
                if override_key in apt_name or apt_name in override_key:
                    tx["reconstruction_status"] = override_val.get("reconstruction_status", "")
                    tx["reconstruction_potential"] = override_val.get("reconstruction_potential", "UNKNOWN")
                    tx["gtx_benefit"] = override_val.get("gtx_benefit", False)
                    break

            # 역세권/출퇴근/학군: district → dong 순서로 매칭
            dist_intel = districts_intel.get(district_code, {})
            if not dist_intel:
                enriched.append(tx)
                continue

            matched_dong = None
            for dong_name, dong_data in dist_intel.get("dongs", {}).items():
                notable = dong_data.get("notable_complexes", [])
                if any(nc in apt_name or apt_name in nc for nc in notable):
                    matched_dong = dong_data
                    break

            # fallback: 구의 첫 번째 dong 또는 district default
            if not matched_dong:
                dongs = dist_intel.get("dongs", {})
                matched_dong = next(iter(dongs.values()), None) if dongs else None

            if matched_dong:
                tx["commute_minutes_to_samsung"] = matched_dong.get("commute_minutes_to_samsung",
                                                                     dist_intel.get("default_commute_minutes", 99))
                tx["nearest_stations"] = matched_dong.get("nearest_stations", [])
                tx["school_zone_notes"] = matched_dong.get("school_zone_notes", "")
                tx["elementary_schools"] = matched_dong.get("elementary_schools", [])
            else:
                tx["commute_minutes_to_samsung"] = dist_intel.get("default_commute_minutes", 99)

            enriched.append(tx)

        return enriched

    def _load_stored_news(self, target_date: date) -> str:
        """당일 Job2 뉴스 마크다운 파일 로드. 없으면 빈 문자열 반환."""
        news_dir = os.path.join(os.getenv("LOCAL_STORAGE_PATH", "./data"), "real_estate", "news")
        filename = os.path.join(news_dir, f"{target_date.isoformat()}_News.md")
        if os.path.exists(filename):
            try:
                with open(filename, "r", encoding="utf-8") as f:
                    content = f.read()
                logger.info(f"[Job4] Loaded news summary: {filename}")
                return content[:3000]  # 토큰 절약을 위해 앞부분만 전달
            except Exception as e:
                logger.error(f"[Job4] Failed to load news file: {e}")
        logger.warning(f"[Job4] No news file found for {target_date} — skipping news section")
        return ""

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
