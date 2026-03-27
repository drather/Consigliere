from modules.career.service import CareerAgent
from modules.finance.service import FinanceAgent
from modules.real_estate.service import RealEstateAgent
from modules.real_estate.monitor.service import TransactionMonitorService
from modules.real_estate.news.service import NewsService
from modules.real_estate.repository import ChromaRealEstateRepository
from modules.automation.service import AutomationService
from core.notify.slack import SlackSender

# Basic global instances for DI
_career_agent = CareerAgent()
_finance_agent = FinanceAgent(storage_mode="local")
_real_estate_agent = RealEstateAgent(storage_mode="local")
_monitor_service = TransactionMonitorService()
_news_service = NewsService(storage_mode="local")
_chroma_repo = ChromaRealEstateRepository()
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

def get_automation_service() -> AutomationService:
    return _automation_service

def get_slack_sender() -> SlackSender:
    return _slack_sender
