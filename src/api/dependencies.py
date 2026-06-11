from modules.career.service import CareerAgent
from modules.finance.service import FinanceAgent
from modules.real_estate.service import RealEstateAgent
from modules.real_estate.monitor.service import TransactionMonitorService
from modules.real_estate.news.service import NewsService
from modules.real_estate.repository import ChromaRealEstateRepository
from modules.real_estate.transaction_repository import TransactionRepository
from modules.real_estate.apartment_repository import ApartmentRepository
from modules.real_estate.apt_master_repository import AptMasterRepository
from modules.real_estate.config import RealEstateConfig
from modules.real_estate.building_master.building_register_client import BuildingRegisterClient
from modules.real_estate.building_master.building_master_repository import BuildingMasterRepository
from modules.real_estate.building_master.building_master_service import BuildingMasterService
from modules.automation.service import AutomationService
from core.notify.slack import SlackSender

# Basic global instances for DI
_career_agent = CareerAgent()
_finance_agent = FinanceAgent(storage_mode="local")
_real_estate_agent = RealEstateAgent(storage_mode="local")
_monitor_service = TransactionMonitorService()
_news_service = NewsService(storage_mode="local")
_chroma_repo = ChromaRealEstateRepository()
_re_config = RealEstateConfig()
_re_db_path = _re_config.get("real_estate_db_path", "data/real_estate.db")
_tx_repo = TransactionRepository(db_path=_re_db_path)
_apt_repo = ApartmentRepository(db_path=_re_db_path)
_apt_master_repo = AptMasterRepository(db_path=_re_db_path)
_bm_repo = BuildingMasterRepository(db_path=_re_db_path)
_bm_service = BuildingMasterService(
    client=BuildingRegisterClient(),
    bm_repo=_bm_repo,
    apt_master_repo=_apt_master_repo,
)
_automation_service = AutomationService()
_slack_sender = SlackSender()

def get_career_agent() -> CareerAgent:
    return _career_agent

def get_finance_agent() -> FinanceAgent:
    return _finance_agent

def get_real_estate_agent() -> RealEstateAgent:
    return _real_estate_agent

def get_monitor_service() -> TransactionMonitorService:
    return _monitor_service

def get_news_service() -> NewsService:
    return _news_service

def get_chroma_repo() -> ChromaRealEstateRepository:
    return _chroma_repo

def get_tx_repo() -> TransactionRepository:
    return _tx_repo

def get_apt_repo() -> ApartmentRepository:
    return _apt_repo

def get_apt_master_repo() -> AptMasterRepository:
    return _apt_master_repo

def get_building_master_service() -> BuildingMasterService:
    return _bm_service

def get_bm_repo() -> BuildingMasterRepository:
    return _bm_repo

def get_automation_service() -> AutomationService:
    return _automation_service

def get_slack_sender() -> SlackSender:
    return _slack_sender


from modules.macro.service import MacroCollectionService

_macro_db_path = _re_config.get("macro_db_path", "data/macro.db")
_macro_service = MacroCollectionService(db_path=_macro_db_path)


def get_macro_service() -> MacroCollectionService:
    return _macro_service


import os
from modules.real_estate.commute.commute_service import CommuteService
from modules.real_estate.commute.commute_repository import CommuteRepository
from modules.real_estate.commute.odsay_client import OdsayClient
from modules.real_estate.commute.tmap_client import TmapClient
from modules.real_estate.commute.hybrid_commute_client import HybridCommuteClient
from modules.real_estate.geocoder import GeocoderService

_commute_cfg = _re_config.get("commute", {
    "destination": "삼성역",
    "destination_lat": 37.5088,
    "destination_lng": 127.0633,
    "cache_ttl_days": 90,
})
_commute_db_path = _re_config.get("commute_cache_db_path", "data/commute_cache.db")

_commute_repo = CommuteRepository(db_path=_commute_db_path, ttl_days=int(_commute_cfg.get("cache_ttl_days", 90)))
_commute_service = CommuteService(
    repo=_commute_repo,
    tmap_client=HybridCommuteClient(
        odsay=OdsayClient(api_key=os.getenv("ODSAY_API_KEY", "")),
        tmap=TmapClient(api_key=os.getenv("TMAP_API_KEY", "")),
    ),
    geocoder=GeocoderService(api_key=os.getenv("KAKAO_API_KEY", "")),
    config=_commute_cfg,
)


def get_commute_service() -> CommuteService:
    return _commute_service


def get_commute_repo() -> CommuteRepository:
    return _commute_repo


from modules.real_estate.school.school_info_client import SchoolInfoClient
from modules.real_estate.school.school_repository import SchoolRepository as SchoolRepo
from modules.real_estate.school.school_service import SchoolService

_school_cfg = _re_config.get("school", {})
_school_repo = SchoolRepo(db_path=_re_db_path)
_school_service = SchoolService(
    client=SchoolInfoClient(),
    repo=_school_repo,
    geocoder=GeocoderService(api_key=os.getenv("KAKAO_API_KEY", "")),
    config=_school_cfg,
)


def get_school_service() -> SchoolService:
    return _school_service


from modules.real_estate.jeonse.repository import JeonseRepository
from modules.real_estate.jeonse.client import JeonseClient

_jeonse_repo = JeonseRepository(db_path=_re_db_path)
_jeonse_client = JeonseClient()


def get_jeonse_repo() -> JeonseRepository:
    return _jeonse_repo


def get_jeonse_client() -> JeonseClient:
    return _jeonse_client


from modules.real_estate.supply.repository import SupplyRepository
from modules.real_estate.supply.client import SupplyClient

_supply_repo = SupplyRepository(db_path=_re_db_path)
_supply_client = SupplyClient()


def get_supply_repo() -> SupplyRepository:
    return _supply_repo


def get_supply_client() -> SupplyClient:
    return _supply_client


# ── Location Service ──────────────────────────────────────────────────────────
from modules.real_estate.location.location_repository import LocationRepository as _LocRepo
from modules.real_estate.location.location_scorer import LocationScorer
from modules.real_estate.location.location_service import LocationService
from modules.real_estate.poi_collector import PoiCollector

_loc_repo = _LocRepo(db_path=_re_db_path)
_poi_collector = PoiCollector(api_key=os.getenv("KAKAO_API_KEY", ""), db_path=_re_db_path)
_location_service = LocationService(
    loc_repo=_loc_repo,
    poi_collector=_poi_collector,
    scorer=LocationScorer(config=_re_config.get("scoring", {})),
)


def get_location_service() -> LocationService:
    return _location_service


# ── Apt Analysis ──────────────────────────────────────────────────────────────
from modules.real_estate.apt_analysis.orchestrator import AptAnalysisOrchestrator
from modules.real_estate.apt_analysis.repository import AptAnalysisRepository
from modules.real_estate.macro.service import MacroService as _MacroSvc
from core.llm import LLMFactory

_apt_macro_svc = _MacroSvc()
_apt_analysis_repo = AptAnalysisRepository(db_path=_re_db_path)
_apt_orchestrator = AptAnalysisOrchestrator(
    apt_master_repo=_apt_master_repo,
    apt_details_repo=_apt_repo,
    tx_repo=_tx_repo,
    jeonse_repo=_jeonse_repo,
    supply_repo=_supply_repo,
    location_service=_location_service,
    macro_svc=_apt_macro_svc,
    commute_repo=_commute_repo,
    llm=LLMFactory.create(),
)


def get_apt_analysis_repo() -> AptAnalysisRepository:
    return _apt_analysis_repo


def get_apt_orchestrator() -> AptAnalysisOrchestrator:
    return _apt_orchestrator


# ── Report Repository ─────────────────────────────────────────────────────────
from modules.real_estate.report_repository import ReportRepository as _ReportRepo

_report_storage_path = _re_config.get("report", {}).get("report_storage_path", "data/real_estate_reports")
_report_repo = _ReportRepo(storage_path=_report_storage_path)


def get_report_repo() -> _ReportRepo:
    return _report_repo


# ── Geocoder Service ──────────────────────────────────────────────────────────
_geocoder_service = GeocoderService(
    api_key=os.getenv("KAKAO_API_KEY", ""),
    cache_path=_re_config.get("geocode_cache_path", "data/geocode_cache.db"),
)


def get_geocoder_service() -> GeocoderService:
    return _geocoder_service


# ── Apt Search Config ─────────────────────────────────────────────────────────
_apt_search_tx_limit = int(_re_config.get("apt_search_tx_limit", 50))
_apt_search_map_limit = int(_re_config.get("apt_search_map_limit", 100))


def get_apt_search_tx_limit() -> int:
    return _apt_search_tx_limit


def get_apt_search_map_limit() -> int:
    return _apt_search_map_limit


# ── Daily Report Orchestrator ─────────────────────────────────────────────────
from core.llm_pipeline import build_llm_pipeline
from core.prompt_loader import PromptLoader
from core.storage import get_storage_provider
from modules.real_estate.trend_analyzer import TrendAnalyzer
from modules.real_estate.comparative.analyzer import ComparativeAnalyzer
from modules.real_estate.yield_analysis.calculator import YieldCalculator
from modules.real_estate.supply.risk_analyzer import SupplyRiskAnalyzer
from modules.real_estate.daily_report.transaction_aggregator import TransactionAggregator
from modules.real_estate.daily_report.daily_report_repository import DailyReportRepository
from modules.real_estate.daily_report.daily_report_orchestrator import DailyReportOrchestrator

_daily_cfg = _re_config.get("daily_report", {})
_daily_storage_path = _daily_cfg.get("storage_path", "data/daily_reports")
_daily_report_repo = DailyReportRepository(storage_path=_daily_storage_path)
_daily_llm = build_llm_pipeline()
_root_storage = get_storage_provider("local", root_path=".")
_prompt_loader = PromptLoader(_root_storage, base_dir="src/modules/real_estate/prompts")
_yield_cfg = _re_config.get("yield_analysis", {})
_daily_report_orchestrator = DailyReportOrchestrator(
    llm=_daily_llm,
    prompt_loader=_prompt_loader,
    aggregator=TransactionAggregator(db_path=_re_db_path),
    report_repo=_daily_report_repo,
    db_path=_re_db_path,
    poi_collector=_poi_collector,
    trend_analyzer=TrendAnalyzer(db_path=_re_db_path),
    commute_svc=_commute_service,
    geocoder=_geocoder_service,
    max_new_commute_api_calls=int(_daily_cfg.get("max_new_commute_api_calls", 5)),
    comp_analyzer=ComparativeAnalyzer(tx_repo=_tx_repo),
    yield_calculator=YieldCalculator(
        jeonse_repo=_jeonse_repo,
        mortgage_rate=float(_yield_cfg.get("mortgage_rate", 0.035)),
    ),
    supply_analyzer=SupplyRiskAnalyzer(
        supply_repo=_supply_repo,
        news_service=_news_service,
        llm=_daily_llm,
        prompt_loader=_prompt_loader,
    ),
    loc_repo=_loc_repo,
)


def get_daily_report_repo() -> DailyReportRepository:
    return _daily_report_repo


def get_daily_report_orchestrator() -> DailyReportOrchestrator:
    return _daily_report_orchestrator
