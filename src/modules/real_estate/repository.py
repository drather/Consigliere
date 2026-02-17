import chromadb
from chromadb.config import Settings
from typing import List, Optional, Dict, Any
from datetime import datetime
import os

from .models import RealEstateReport, RealEstateMetadata, RealEstateTransaction

class ChromaRealEstateRepository:
    """
    Repository for Real Estate reports using ChromaDB.
    Supports semantic search and metadata filtering.
    """

    def __init__(self, host: str = None, port: int = None):
        # Allow override via args, otherwise env vars, otherwise default local
        self.host = host or os.getenv("CHROMA_DB_HOST", "localhost")
        self.port = port or int(os.getenv("CHROMA_DB_PORT", 8001))
        
        # Initialize ChromaDB Client
        print(f"🔌 [{datetime.now().strftime('%H:%M:%S')}] [ChromaDB] Connecting to {self.host}:{self.port}...")
        self.client = chromadb.HttpClient(host=self.host, port=self.port)
        
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

    def save_transaction(self, transaction: "RealEstateTransaction") -> None:
        """
        Saves a transaction record into ChromaDB.
        Uses the model's logic to format data.
        """
        data = transaction.to_chroma_format()
        
        print(f"💾 [{datetime.now().strftime('%H:%M:%S')}] [ChromaDB] Upserting transaction: {data['id']}")
        
        # Upsert
        self.collection.upsert(
            ids=[data["id"]],
            documents=[data["document"]],
            metadatas=[data["metadata"]]
        )
        print(f"✅ [{datetime.now().strftime('%H:%M:%S')}] [ChromaDB] Saved txn: {transaction.apt_name}")

    def delete(self, report_id: str) -> None:
        """Deletes a report by ID."""
        self.collection.delete(ids=[report_id])
        print(f"🗑️ [ChromaDB] Deleted report: {report_id}")

    def get_transactions(self, limit: int = 100, where: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """
        Fetches raw transaction data (metadata) from ChromaDB.
        Useful for tabular display in dashboards.
        """
        try:
            results = self.collection.get(
                limit=limit,
                where=where,
                include=["metadatas"]
            )
            
            if not results or not results["metadatas"]:
                return []
                
            return results["metadatas"]
        except Exception as e:
            print(f"⚠️ [ChromaDB] Error fetching transactions: {e}")
            return []
