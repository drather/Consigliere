import chromadb
from chromadb.config import Settings
from typing import List, Optional, Dict, Any
from datetime import datetime
import os

from ..domain.real_estate import RealEstateReport, RealEstateMetadata

class ChromaRealEstateRepository:
    """
    Repository for Real Estate reports using ChromaDB.
    Supports semantic search and metadata filtering.
    """

    def __init__(self, host: str = "localhost", port: int = 8001):
        # Initialize ChromaDB Client
        print(f"🔌 [{datetime.now().strftime('%H:%M:%S')}] [ChromaDB] Connecting to {host}:{port}...")
        self.client = chromadb.HttpClient(host=host, port=port)
        
        # Get or Create a collection
        print(f"📂 [{datetime.now().strftime('%H:%M:%S')}] [ChromaDB] Getting/Creating collection 'real_estate_reports'...")
        self.collection = self.client.get_or_create_collection(
            name="real_estate_reports",
            metadata={"hnsw:space": "cosine"} # Use cosine similarity
        )
        print(f"✅ [{datetime.now().strftime('%H:%M:%S')}] [ChromaDB] Connected and collection ready.")

    def save(self, report: RealEstateReport) -> None:
        """
        Upserts a report into ChromaDB.
        """
        print(f"💾 [{datetime.now().strftime('%H:%M:%S')}] [ChromaDB] Upserting report: {report.report_id}")
        data = report.to_chroma_format()
        
        self.collection.upsert(
            ids=[data["id"]],
            documents=[data["document"]],
            metadatas=[data["metadata"]]
        )
        print(f"✅ [{datetime.now().strftime('%H:%M:%S')}] [ChromaDB] Saved report for: {report.report_id}")

    def search(self, query_text: str, n_results: int = 5, where: Optional[Dict[str, Any]] = None) -> List[RealEstateReport]:
        """
        Searches reports based on semantic similarity and optional metadata filters.
        
        Args:
            query_text: Natural language query (e.g., "elementary school")
            n_results: Max results to return
            where: Metadata filter (e.g., {"price": {"$lte": 1000000000}})
        """
        print(f"🔎 [{datetime.now().strftime('%H:%M:%S')}] [ChromaDB] Querying collection. Text: '{query_text}', Where: {where}")
        results = self.collection.query(
            query_texts=[query_text],
            n_results=n_results,
            where=where
        )
        print(f"✅ [{datetime.now().strftime('%H:%M:%S')}] [ChromaDB] Query complete. Found {len(results['ids'][0])} matches.")

        reports = []
        for i in range(len(results["ids"][0])):
            # Convert back to domain model
            metadata = RealEstateMetadata(**results["metadatas"][0][i])
            reports.append(RealEstateReport(
                report_id=results["ids"][0][i],
                content=results["documents"][0][i],
                metadata=metadata
            ))
        return reports

    def delete(self, report_id: str) -> None:
        """Deletes a report by ID."""
        self.collection.delete(ids=[report_id])
        print(f"🗑️ [ChromaDB] Deleted report: {report_id}")
