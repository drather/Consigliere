import asyncio
import json
import os
import aiohttp
from datetime import date, datetime, timedelta
from typing import Dict, Any, List, Optional

from core.storage import get_storage_provider, StorageProvider
from core.prompt_loader import PromptLoader
from core.llm import LLMClient
from core.llm_pipeline import build_llm_pipeline
from core.logger import get_logger
from core.policy_fetcher import fetch_latest_financial_policies
from .repository import ChromaRealEstateRepository
from .config import RealEstateConfig
from .tour_service import TourService
from .insight_orchestrator import InsightOrchestrator
from .presenter import RealEstatePresenter
from .macro.service import MacroService
from .news.service import NewsService
from .calculator import FinancialCalculator
from .persona_manager import PersonaManager, PreferenceRulesManager
from .apartment_master.client import ApartmentMasterClient
from .apartment_master.repository import ApartmentMasterRepository
from .apartment_master.service import ApartmentMasterService
from .models import ApartmentMaster
from .apartment_repository import ApartmentRepository
# NOTE: _normalize_name is also defined in apartment_repository.py — extract to shared utils when refactoring
from .transaction_repository import TransactionRepository, _normalize_name
from .apt_master_repository import AptMasterRepository

logger = get_logger(__name__)


def _make_dedup_key(tx: dict) -> str:
    """중복 제거 키 — apt_name은 정규화하여 표기 차이를 무시한다.

    exclusive_area 또는 deal_date가 없는 불완전 레코드는 uuid로 처리해 dedup 대상에서 제외한다.
    """
    import uuid as _uuid
    area = tx.get("exclusive_area")
    deal = tx.get("deal_date")
    if area is None or deal is None:
        return str(_uuid.uuid4())
    return (
        f"{_normalize_name(tx.get('apt_name', ''))}"
        f"_{area}_{deal}"
        f"_{tx.get('floor', 0)}"
        f"_{tx.get('price', 0)}"
    )


def _area_matches(area: str, text: str) -> bool:
    """전체 지명 또는 공백 분리 토큰(2자 이상) 중 하나라도 포함되면 True."""
    if area in text:
        return True
    return any(token in text for token in area.split() if len(token) >= 2)


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
        self.llm = build_llm_pipeline()
        self.repository = ChromaRealEstateRepository()

        # Specialized Services
        self.tour_service = TourService(self.llm, self.prompt_loader, self.repository)
        self.insight_orchestrator = InsightOrchestrator(self.llm, self.prompt_loader)
        self.presenter = RealEstatePresenter()
        self.macro_service = MacroService()
        self.news_service = NewsService()
        self.calculator = FinancialCalculator()

        # Apartment Master (legacy — apartment_master.db, 빌드 스크립트용)
        apt_master_db = self.config.get("apartment_master_db_path", "data/apartment_master.db")
        apt_master_rate = float(self.config.get("apartment_master_rate_limit_sec", 0.3))
        self.apt_master_service = ApartmentMasterService(
            client=ApartmentMasterClient(),
            repository=ApartmentMasterRepository(db_path=apt_master_db),
            rate_limit_sec=apt_master_rate,
        )

        # New SQLite repositories (real_estate.db)
        re_db = self.config.get("real_estate_db_path", "data/real_estate.db")
        self.apt_repo = ApartmentRepository(db_path=re_db)
        self.tx_repo = TransactionRepository(db_path=re_db)
        self.apt_master_repo = AptMasterRepository(db_path=re_db)

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

    def generate_insight_report(self, district_code: str = None, target_date: date = None) -> List[Dict[str, Any]]:
        """
        Live insight report: fetches transactions directly and delegates to generate_report().
        """
        if target_date is None:
            target_date = date.today()
        logger.info(f"📊 [RealEstateAgent] generate_insight_report → delegating to generate_report for {target_date}")
        self.generate_report(district_code, target_date)

        # Return saved report blocks
        report_dir = os.path.join(os.getenv("LOCAL_STORAGE_PATH", "./data"), "real_estate", "reports")
        filename = os.path.join(report_dir, f"{target_date.isoformat()}_Report.json")
        if os.path.exists(filename):
            try:
                with open(filename, "r", encoding="utf-8") as f:
                    saved = json.load(f)
                return saved.get("blocks", [])
            except Exception as e:
                logger.error(f"[generate_insight_report] Failed to load saved report: {e}")
        return []

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

        # cutoff가 이전 달에 걸치면 이전 달도 조회
        cutoff_ym = cutoff_3days.strftime("%Y%m")
        fetch_months = [target_ym]
        if cutoff_ym != target_ym:
            fetch_months.insert(0, cutoff_ym)
            logger.info(f"[Job1] cutoff({cutoff_3days}) ← 이전 달 포함: {fetch_months}")

        # Step 0: 1년 이상 된 데이터 삭제
        deleted = self.tx_repo.delete_before(cutoff_1year)

        # Step 1: 비동기 병렬 fetch (월별로 순차 실행, 지구별 병렬)
        molit_client = MOLITClient()
        loop = asyncio.new_event_loop()
        try:
            all_fetched: list = []
            for ym in fetch_months:
                month_results = loop.run_until_complete(
                    self._async_fetch_all(targets, ym, molit_client, cutoff_3days)
                )
                all_fetched.extend(month_results)
            # 같은 지구의 결과를 병합 (지구별로 txs 합산)
            merged: dict = {}
            for name, code, txs in all_fetched:
                if code not in merged:
                    merged[code] = (name, code, [])
                merged[code][2].extend(txs)
            fetched_results = list(merged.values())
        finally:
            loop.close()

        # Step 2: SQLite 저장
        total_fetched, total_saved, results = 0, 0, []
        all_new_txs: list = []
        for name, code, txs in fetched_results:
            total_fetched += len(txs)
            if not txs:
                continue
            try:
                saved = self.tx_repo.save_batch(txs)
                total_saved += saved
                all_new_txs.extend(txs)
                results.append({"district": name, "fetched": len(txs), "saved": saved})
                logger.info(f"[Job1] {name}({code}): {len(txs)}건(7일) 수집, {saved}건 저장")
            except Exception as e:
                logger.error(f"[Job1] Save 실패 {name}({code}): {e}")

        # Step 3: apt_master 동기화 (신규 단지 INSERT + 기존 단지 통계 갱신)
        master_synced = 0
        if all_new_txs:
            try:
                master_synced = self.apt_master_repo.sync_from_new_transactions(all_new_txs)
                logger.info(f"[Job1] apt_master 동기화: {master_synced}건 신규 단지")
            except Exception as e:
                logger.error(f"[Job1] apt_master sync 실패: {e}")

        # Step 4: transactions.apt_master_id FK 채우기
        apt_master_filled = 0
        if all_new_txs:
            try:
                apt_master_filled = self.tx_repo.fill_apt_master_ids(self.apt_master_repo)
                if apt_master_filled:
                    logger.info(f"[Job1] apt_master_id 채우기: {apt_master_filled}건")
            except Exception as e:
                logger.error(f"[Job1] fill_apt_master_ids 실패: {e}")

        # Step 5: NULL complex_code 해소
        resolved = self.tx_repo.resolve_complex_codes(self.apt_repo)
        if resolved:
            logger.info(f"[Job1] complex_code 해소: {resolved}건")

        return {
            "fetched_count": total_fetched,
            "saved_count": total_saved,
            "district_count": len(targets),
            "year_month": target_ym,
            "deleted_old_count": deleted,
            "master_synced_count": master_synced,
            "apt_master_id_filled": apt_master_filled,
            "resolved_count": resolved,
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
        """Job 3: 거시경제 지표 수집 → macro.db 저장 + JSON 백업."""
        logger.info("[Job3] Fetching macro data via MacroCollectionService...")
        result = self.macro_service.collect_real_estate_indicators()

        macro_dict = self.macro_service.fetch_latest_macro_data()
        macro_dir = os.path.join(os.getenv("LOCAL_STORAGE_PATH", "./data"), "real_estate", "macro")
        os.makedirs(macro_dir, exist_ok=True)
        today = datetime.now().strftime("%Y-%m-%d")
        macro_path = os.path.join(macro_dir, f"{today}_macro.json")
        with open(macro_path, "w", encoding="utf-8") as f:
            json.dump(macro_dict, f, ensure_ascii=False, indent=2)

        logger.info(f"[Job3] Saved macro backup: {macro_path}")
        return {"macro": macro_dict, "collect_result": result}

    def build_apartment_master(self) -> Dict[str, Any]:
        """Job 0: 수도권 아파트 마스터 DB 전수 구축.

        config.yaml의 71개 districts를 순회하여 공동주택 공공 API로 세대수·동수·건설사·사용승인일을 수집,
        SQLite에 저장한다. 이미 저장된 단지는 스킵한다.
        """
        import time as _time
        logger.info("[Job0] 아파트 마스터 DB 전수 구축 시작")
        start = _time.time()
        districts = self.config.get("districts", [])
        stats = self.apt_master_service.build_initial(districts)
        elapsed = round(_time.time() - start, 1)
        logger.info(f"[Job0] 완료: {stats}, elapsed={elapsed}s")
        return {**stats, "elapsed_seconds": elapsed}

    def generate_report(self, district_code: Optional[str] = None, target_date: Optional[date] = None) -> Dict[str, Any]:
        """Job 4: SQLite tx_repo 기반 인사이트 리포트 생성."""
        from dataclasses import asdict
        if target_date is None:
            target_date = date.today()
        logger.info(f"[Job4] Generating report for {target_date}, district_code={district_code}")

        # 1. 뉴스/거시경제 로드
        news_text = self._load_stored_news(target_date)
        macro_data = self._load_stored_macro(target_date) or {}

        # 2. 주담대금리 추출 → 예산 계산
        policy_context = fetch_latest_financial_policies()
        persona_data = self._load_persona()

        mortgage_rate = None
        loan_entry = macro_data.get("loan_rate", {})
        if loan_entry and loan_entry.get("value") is not None:
            mortgage_rate = float(loan_entry["value"]) / 100.0
            logger.info(f"[Job4] 주담대금리 {loan_entry['value']}% 적용")

        budget_plan = self.calculator.calculate_budget(persona_data, policy_context, mortgage_rate=mortgage_rate)
        budget_ceiling = budget_plan.final_max_price

        # 3. 관심 지역 코드 목록
        target_codes = self._resolve_interest_districts(persona_data, district_code)
        logger.info(f"[Job4] districts: {target_codes}")

        # 4. SQLite tx_repo에서 실거래가 조회
        recent_days = self.config.get("report", {}).get("recent_days", 7)
        cutoff = (target_date - timedelta(days=recent_days)).isoformat()
        all_txs: List[Dict[str, Any]] = []
        for code in target_codes:
            try:
                rows = self.tx_repo.get_by_district(code, limit=200, date_from=cutoff)
                all_txs.extend(asdict(tx) for tx in rows)
            except Exception as e:
                logger.error(f"[Job4] tx_repo 조회 실패 {code}: {e}")

        # 5. 중복 제거
        seen_keys: set[str] = set()
        deduped_txs = []
        for tx in all_txs:
            key = _make_dedup_key(tx)
            if key not in seen_keys:
                seen_keys.add(key)
                deduped_txs.append(tx)

        # 6. 가격 ±band 필터 (예산과 관련성 높은 매물만)
        band = self.config.get("report", {}).get("budget_band_ratio", 0.1)
        lo, hi = budget_ceiling * (1 - band), budget_ceiling * (1 + band)
        candidates = [tx for tx in deduped_txs if lo <= tx.get("price", 0) <= hi]
        logger.info(f"[Job4] 예산 {budget_ceiling/1e8:.1f}억 ±{band*100:.0f}% → {len(candidates)}건 (전체 {len(deduped_txs)}건)")

        # 7. area_intel enrich
        area_intel = self._load_area_intel()
        workplace_station = persona_data.get("commute", {}).get("workplace_station", "")
        candidates = self._enrich_transactions(candidates, area_intel, workplace_station)

        # 8. Python 데이터 준비
        interest_areas = persona_data.get("user", {}).get("interest_areas", [])
        news_str = news_text
        horea_data = self._extract_horea_data(news_str, interest_areas) if news_str.strip() else {}
        macro_summary = self._format_macro_summary(macro_data)
        horea_text = self._horea_data_to_text(horea_data)

        # 9. 오케스트레이터에 위임
        preference_rules = PreferenceRulesManager().get()
        report_json = self.insight_orchestrator.generate_strategy(
            target_date=target_date,
            candidates=candidates,
            budget_plan=budget_plan,
            persona_data=persona_data,
            preference_rules=preference_rules,
            scoring_config=self.config.get("scoring", {}),
            report_config=self.config.get("report", {}),
            horea_data=horea_data,
            macro_summary=macro_summary,
            horea_text=horea_text,
        )

        self._save_report(report_json, target_date, len(candidates))
        return {"success": True, "tx_count": len(candidates), "date": target_date.isoformat()}

    def _job1_done_flag(self, target_date: date) -> str:
        """Job1 완료 마커 파일 경로."""
        data_root = os.getenv("LOCAL_STORAGE_PATH", "./data")
        return os.path.join(data_root, "real_estate", f"job1_{target_date.isoformat()}.done")

    def _pipeline_lock_path(self) -> str:
        """파이프라인 중복 실행 방지용 락 파일 경로."""
        data_root = os.getenv("LOCAL_STORAGE_PATH", "./data")
        return os.path.join(data_root, "real_estate", "pipeline_running.lock")

    def run_insight_pipeline(self, district_code: Optional[str] = None, target_date: Optional[date] = None, send_slack: bool = True) -> Dict[str, Any]:
        """Pipeline: Job1 → Job2 → Job3 → Job4 → Slack.

        당일 이미 수행된 Job은 스킵한다 (중복 방지):
          - Job1: data/real_estate/job1_{date}.done 파일 존재 시 스킵
          - Job2: data/real_estate/news/{date}_News.md 존재 시 스킵
          - Job3: data/real_estate/macro/{date}_macro.json 존재 시 스킵
        district_code=None → persona.interest_areas 기반 4개 구 동시 수집
        """
        lock_path = self._pipeline_lock_path()
        if os.path.exists(lock_path):
            logger.warning(f"[Pipeline] Already running — lock file exists: {lock_path}. Aborting.")
            return {"skipped": True, "reason": "pipeline_already_running"}

        if target_date is None:
            target_date = date.today()
        year_month = target_date.strftime("%Y%m")
        data_root = os.getenv("LOCAL_STORAGE_PATH", "./data")

        os.makedirs(os.path.dirname(lock_path), exist_ok=True)
        try:
            with open(lock_path, "w") as f:
                f.write(datetime.now().isoformat())

            results = self._run_pipeline_jobs(district_code, target_date, year_month, data_root, send_slack)
        finally:
            if os.path.exists(lock_path):
                os.remove(lock_path)

        return results

    def _run_pipeline_jobs(self, district_code, target_date, year_month, data_root, send_slack) -> Dict[str, Any]:
        """파이프라인 내부 실행 로직 (lock 내부에서 호출)."""
        results = {}

        # ── Job 1: 실거래가 수집 ──────────────────────────────────────
        job1_flag = self._job1_done_flag(target_date)
        if os.path.exists(job1_flag):
            logger.info(f"[Pipeline] Job1 스킵 — 당일 완료 마커 존재: {job1_flag}")
            results["job1"] = {"skipped": True, "reason": "already_done_today"}
        else:
            results["job1"] = self.fetch_transactions(district_code, year_month)
            # 완료 마커 생성
            os.makedirs(os.path.dirname(job1_flag), exist_ok=True)
            with open(job1_flag, "w") as f:
                f.write(datetime.now().isoformat())

        # ── Job 2: 뉴스 수집 ─────────────────────────────────────────
        news_file = os.path.join(data_root, "real_estate", "news", f"{target_date.isoformat()}_News.md")
        if os.path.exists(news_file):
            logger.info(f"[Pipeline] Job2 스킵 — 당일 뉴스 파일 존재: {news_file}")
            results["job2"] = {"skipped": True, "reason": "already_done_today"}
        else:
            results["job2"] = self.fetch_news()

        # ── Job 3: 거시경제 수집 ─────────────────────────────────────
        macro_file = os.path.join(data_root, "real_estate", "macro", f"{target_date.isoformat()}_macro.json")
        if os.path.exists(macro_file):
            logger.info(f"[Pipeline] Job3 스킵 — 당일 매크로 파일 존재: {macro_file}")
            results["job3"] = {"skipped": True, "reason": "already_done_today"}
        else:
            results["job3"] = self.fetch_macro_data()

        # ── Job 4: 리포트 생성 (항상 실행) ───────────────────────────
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

    def _compute_district_average(self, dist_intel: Dict[str, Any]) -> Dict[str, Any]:
        """구 내 모든 동의 데이터를 평균/집계하여 fallback 데이터 생성."""
        dongs = list(dist_intel.get("dongs", {}).values())
        if not dongs:
            return {}

        commutes = [d["commute_minutes"] for d in dongs if d.get("commute_minutes")]
        avg_commute = int(sum(commutes) / len(commutes)) if commutes else dist_intel.get("default_commute_minutes", 99)

        seen, all_stations = set(), []
        for d in dongs:
            for s in d.get("nearest_stations", []):
                if s["name"] not in seen:
                    all_stations.append(s)
                    seen.add(s["name"])

        school_notes = [d.get("school_zone_notes", "") for d in dongs if d.get("school_zone_notes")]

        return {
            "commute_minutes": avg_commute,
            "nearest_stations": all_stations[:4],
            "school_zone_notes": school_notes[0] if school_notes else f"{dist_intel.get('name', '')} 구 평균 데이터",
            "elementary_schools": [],
            "_is_district_average": True,
        }

    def _enrich_transactions(
        self,
        txs: List[Dict[str, Any]],
        area_intel: Dict[str, Any],
        workplace_station: str = "",
    ) -> List[Dict[str, Any]]:
        """각 거래 dict에 commute_minutes, nearest_stations, school_zone, reconstruction,
        아파트 마스터(세대수·건설사·준공연도) 정보를 부착한다.

        - area_intel.json에서 일괄 조회 (per-apt ChromaDB 호출 없음)
        - 아파트 마스터 DB 조회는 area_intel 유무와 무관하게 항상 실행
        - 매칭: apt_name → notable_complexes → 구 평균 fallback
        """
        districts_intel = area_intel.get("districts", {}) if area_intel else {}
        apt_overrides = area_intel.get("apartment_overrides", {}) if area_intel else {}
        reference_workplace = area_intel.get("reference_workplace", "") if area_intel else ""

        # 직장역이 reference_workplace와 다를 경우 경고
        if workplace_station and reference_workplace and workplace_station != reference_workplace:
            logger.warning(
                f"[Job4] persona 직장역({workplace_station})과 area_intel 기준역({reference_workplace})이 다름 "
                f"— 출퇴근 시간은 {reference_workplace} 기준으로 표시됩니다."
            )

        enriched = []
        for tx in txs:
            tx = dict(tx)
            apt_name = tx.get("apt_name", "")
            district_code = str(tx.get("district_code", ""))

            # ── 아파트 마스터 정보 enrich (세대수, 동수, 건설사, 사용승인일) ──
            # area_intel 유무와 무관하게 항상 실행
            try:
                detail = self._lookup_apt_details(apt_name, district_code)
                if detail:
                    tx["household_count"] = detail.household_count
                    tx["building_count"] = detail.building_count
                    tx["constructor"] = detail.constructor
                    tx["approved_date"] = detail.approved_date
            except Exception as e:
                logger.warning(f"[Enrich] apt_details 조회 실패 {apt_name}: {e}")

            if not area_intel:
                enriched.append(tx)
                continue

            # ── 재건축 정보: apartment_overrides (area_intel.json 기반) ──
            for override_key, override_val in apt_overrides.items():
                if override_key in apt_name or apt_name in override_key:
                    tx["reconstruction_status"] = override_val.get("reconstruction_status", "")
                    tx["reconstruction_potential"] = override_val.get("reconstruction_potential", "UNKNOWN")
                    tx["gtx_benefit"] = override_val.get("gtx_benefit", False)
                    tx["apt_notes"] = override_val.get("notes", "")
                    break

            # ── 역세권/출퇴근/학군: district → dong 매칭 ──
            dist_intel = districts_intel.get(district_code, {})
            tx["district_name"] = dist_intel.get("name", "")

            if not dist_intel:
                enriched.append(tx)
                continue

            # dong 매칭: notable_complexes 기준
            matched_dong = None
            for dong_data in dist_intel.get("dongs", {}).values():
                notable = dong_data.get("notable_complexes", [])
                if any(nc in apt_name or apt_name in nc for nc in notable):
                    matched_dong = dong_data
                    break

            # fallback: 구 평균
            if not matched_dong:
                matched_dong = self._compute_district_average(dist_intel)

            if matched_dong:
                tx["commute_minutes"] = matched_dong.get(
                    "commute_minutes", dist_intel.get("default_commute_minutes", 99)
                )
                tx["nearest_stations"] = matched_dong.get("nearest_stations", [])
                tx["school_zone_notes"] = matched_dong.get("school_zone_notes", "")
                tx["elementary_schools"] = matched_dong.get("elementary_schools", [])
            else:
                tx["commute_minutes"] = dist_intel.get("default_commute_minutes", 99)

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
            except Exception as e:
                logger.warning(f"[Job4] Failed to parse macro JSON {filename}: {e}")
        return None

    def _load_persona(self) -> Dict[str, Any]:
        return PersonaManager().load()

    def _lookup_apt_details(self, apt_name: str, district_code: str) -> Optional[ApartmentMaster]:
        """apt_master_repo + apt_repo 2-step lookup to return ApartmentMaster.

        1) apt_master_repo → complex_code
        2) complex_code → apt_repo.get() (exact)
        3) Fallback: apt_repo.search() (partial match by apt_name + district_code)
        """
        apt_name = _normalize_name(apt_name)
        entry = self.apt_master_repo.get_by_name_district(apt_name, district_code)
        if entry and entry.complex_code:
            detail = self.apt_repo.get(entry.complex_code)
            if detail:
                return detail
        results = self.apt_repo.search(apt_name=apt_name, district_code=district_code, limit=1)
        return results[0] if results else None

    def _format_macro_summary(self, macro_data: Optional[Dict[str, Any]]) -> str:
        if not macro_data:
            return ""
        lines = []
        entry = macro_data.get("base_rate")
        if entry and entry.get("value") is not None:
            lines.append(f"- 기준금리: {entry['value']}% ({entry.get('date', '')})")
        entry = macro_data.get("loan_rate")
        if entry and entry.get("value") is not None:
            lines.append(f"- 주담대금리(주택담보대출): {entry['value']}% ({entry.get('date', '')})")
        entry = macro_data.get("m2_growth")
        if entry and entry.get("value") is not None:
            lines.append(f"- M2 통화량: {entry['value']:,}{entry.get('unit', '')} ({entry.get('date', '')})")
        return "\n".join(lines)

    def _extract_horea_data(self, news_text: str, interest_areas: List[str]) -> Dict[str, Any]:
        GTX_KW = ["GTX", "광역급행철도"]
        HOREA_KW = ["재건축", "재개발", "정비사업", "지구지정", "개발사업", "신도시", "택지지구",
                    "학군", "학교신설", "착공", "개통", "노선"]
        result: Dict[str, Any] = {}
        sentences = [s.strip() for s in news_text.replace("\n", ".").split(".") if s.strip()]
        for area in interest_areas:
            items, has_gtx = [], False
            for idx, sent in enumerate(sentences):
                context = " ".join(sentences[max(0, idx - 1):idx + 2])
                if not _area_matches(area, sent) and not _area_matches(area, context):
                    continue
                if any(kw in context for kw in GTX_KW):
                    has_gtx = True
                    items.append(sent)
                elif any(kw in context for kw in HOREA_KW):
                    items.append(sent)
            if items:
                result[area] = {"gtx": has_gtx, "items": items[:5]}
        return result

    def _horea_data_to_text(self, horea_data: Dict[str, Any]) -> str:
        if not horea_data:
            return "호재 정보 없음"
        lines = []
        for area, info in horea_data.items():
            gtx_tag = " [GTX 수혜]" if info.get("gtx") else ""
            for item in info.get("items", []):
                lines.append(f"- {area}{gtx_tag}: {item}")
        return "\n".join(lines) if lines else "호재 정보 없음"

    def get_persona(self) -> Dict[str, Any]:
        """현재 persona.yaml을 dict로 반환."""
        return PersonaManager().load()

    def update_persona(self, updates: Dict[str, Any]) -> Dict[str, Any]:
        """persona.yaml을 부분 업데이트하고 이력을 백업한다."""
        return PersonaManager().update(updates)

    def get_preference_rules(self) -> List[Dict[str, Any]]:
        """preference_rules.yaml의 rules 목록을 반환."""
        return PreferenceRulesManager().get()

    def update_preference_rules(self, rules: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """preference_rules.yaml의 rules 목록을 교체 저장."""
        return PreferenceRulesManager().update(rules)
