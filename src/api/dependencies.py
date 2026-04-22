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
from modules.real_estate.commute.tmap_client import TmapClient
from modules.real_estate.geocoder import GeocoderService

_commute_cfg = _re_config.get("commute", {
    "destination": "삼성역",
    "destination_lat": 37.5088,
    "destination_lng": 127.0633,
    "cache_ttl_days": 90,
})
_commute_db_path = _re_config.get("commute_cache_db_path", "data/commute_cache.db")

_commute_service = CommuteService(
    repo=CommuteRepository(db_path=_commute_db_path, ttl_days=int(_commute_cfg.get("cache_ttl_days", 90))),
    tmap_client=TmapClient(api_key=os.getenv("TMAP_API_KEY", "")),
    geocoder=GeocoderService(api_key=os.getenv("KAKAO_API_KEY", "")),
    config=_commute_cfg,
)


def get_commute_service() -> CommuteService:
    return _commute_service
