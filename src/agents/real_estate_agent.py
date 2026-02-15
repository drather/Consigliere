import json
from datetime import datetime
from typing import Dict, Any, List

from core.storage import get_storage_provider, StorageProvider
from core.prompt_loader import PromptLoader
from core.llm import LLMClient
from core.domain.real_estate import RealEstateReport, RealEstateMetadata
from core.repositories.chroma_repository import ChromaRealEstateRepository

class RealEstateAgent:
    def __init__(self, storage_mode: str = "local"):
        self.storage: StorageProvider = get_storage_provider(storage_mode)
        # Always use local project root for prompts
        root_storage = get_storage_provider("local", root_path=".")
        self.prompt_loader = PromptLoader(root_storage)
        
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
            "real_estate/parser",
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
            "real_estate/searcher",
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
