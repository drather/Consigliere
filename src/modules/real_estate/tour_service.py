from datetime import datetime
from typing import Dict, Any, List
from core.logger import get_logger
from core.llm import LLMClient
from core.prompt_loader import PromptLoader
from .models import RealEstateReport, RealEstateMetadata
from .repository import ChromaRealEstateRepository

logger = get_logger(__name__)

class TourService:
    """
    Service for logging and searching real estate tour notes.
    """
    def __init__(self, llm: LLMClient, prompt_loader: PromptLoader, repository: ChromaRealEstateRepository):
        self.llm = llm
        self.prompt_loader = prompt_loader
        self.repository = repository

    def log_tour(self, user_text: str) -> str:
        start_time = datetime.now()
        logger.info(f"⏱️ [TourService] Starting log_tour...")

        _, prompt_str = self.prompt_loader.load("parser", variables={"input_text": user_text})
        extraction = self.llm.generate_json(prompt_str)
        
        if "error" in extraction:
            return f"❌ Failed to parse tour note: {extraction['error']}"

        metadata = RealEstateMetadata(**extraction)
        report = RealEstateReport(
            report_id=metadata.complex_name,
            metadata=metadata,
            content=user_text
        )

        self.repository.save(report)
        elapsed = (datetime.now() - start_time).total_seconds()
        
        return (
            f"✅ Real Estate Tour Logged (took {elapsed:.2f}s).\n"
            f"- Complex: {metadata.complex_name}\n"
            f"- Price: {f'{metadata.price:,} KRW' if metadata.price else 'N/A'}"
        )

    def search_tours(self, user_query: str) -> str:
        start_time = datetime.now()
        logger.info(f"⏱️ [TourService] Starting search_tours...")

        _, prompt_str = self.prompt_loader.load("searcher", variables={"input_text": user_query})
        query_config = self.llm.generate_json(prompt_str)
        
        if "error" in query_config:
            return f"❌ Failed to build search query: {query_config['error']}"

        results = self.repository.search(
            query_text=query_config.get("query_text", ""),
            where=query_config.get("where"),
            n_results=3
        )

        if not results:
            return "🔍 No matching complexes found."

        response = f"🔍 Found {len(results)} matching complexes (took {(datetime.now() - start_time).total_seconds():.2f}s):\n\n"
        for i, report in enumerate(results, 1):
            m = report.metadata
            response += f"{i}. **{m.complex_name}**\n   - Price: {f'{m.price:,} KRW' if m.price else 'N/A'}\n   - Note: {report.content[:100]}...\n\n"
        
        return response
