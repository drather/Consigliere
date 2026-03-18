import chromadb
from chromadb.config import Settings
from typing import List, Optional, Dict, Any
from datetime import datetime
import os

from .models import RealEstateReport, RealEstateMetadata, RealEstateTransaction
from core.logger import get_logger

logger = get_logger(__name__)


class ChromaRealEstateRepository:
    """
    Repository for Real Estate reports using ChromaDB.
    Supports semantic search and metadata filtering.
    """

    def __init__(self, host: str = None, port: int = None):
        # Allow override via args, otherwise env vars, otherwise default local
        self.host = host or os.getenv("CHROMA_DB_HOST", "127.0.0.1")
        self.port = port or int(os.getenv("CHROMA_DB_PORT", 8001))
        
        # Initialize ChromaDB Client
        logger.info(f"🔌 [{datetime.now().strftime('%H:%M:%S')}] [ChromaDB] Connecting to {self.host}:{self.port}...")
        self.client = chromadb.HttpClient(host=self.host, port=self.port)
        
        # Got or Create a collection for Reports/Transactions
        logger.info(f"📂 [{datetime.now().strftime('%H:%M:%S')}] [ChromaDB] Getting/Creating collection 'real_estate_reports'...")
        self.collection = self.client.get_or_create_collection(
            name="real_estate_reports",
            metadata={"hnsw:space": "cosine"}
        )
        
        # [Phase 2] Collection for Policy & Development Knowledge
        logger.info(f"📂 [{datetime.now().strftime('%H:%M:%S')}] [ChromaDB] Getting/Creating collection 'policy_knowledge'...")
        self.policy_collection = self.client.get_or_create_collection(
            name="policy_knowledge",
            metadata={"hnsw:space": "cosine"}
        )
        logger.info(f"✅ [{datetime.now().strftime('%H:%M:%S')}] [ChromaDB] Connected and collections ready.")

    def save(self, report: RealEstateReport) -> None:
        """
        Upserts a report into ChromaDB.
        """
        logger.info(f"💾 [{datetime.now().strftime('%H:%M:%S')}] [ChromaDB] Upserting report: {report.report_id}")
        data = report.to_chroma_format()
        
        self.collection.upsert(
            ids=[data["id"]],
            documents=[data["document"]],
            metadatas=[data["metadata"]]
        )
        logger.info(f"✅ [{datetime.now().strftime('%H:%M:%S')}] [ChromaDB] Saved report for: {report.report_id}")

    def search(self, query_text: str, n_results: int = 5, where: Optional[Dict[str, Any]] = None) -> List[RealEstateReport]:
        """
        Searches reports based on semantic similarity and optional metadata filters.
        
        Args:
            query_text: Natural language query (e.g., "elementary school")
            n_results: Max results to return
            where: Metadata filter (e.g., {"price": {"$lte": 1000000000}})
        """
        logger.info(f"🔎 [{datetime.now().strftime('%H:%M:%S')}] [ChromaDB] Querying collection. Text: '{query_text}', Where: {where}")
        results = self.collection.query(
            query_texts=[query_text],
            n_results=n_results,
            where=where
        )
        logger.info(f"✅ [{datetime.now().strftime('%H:%M:%S')}] [ChromaDB] Query complete. Found {len(results['ids'][0])} matches.")

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
        
        logger.info(f"💾 [{datetime.now().strftime('%H:%M:%S')}] [ChromaDB] Upserting transaction: {data['id']}")
        
        # Upsert
        self.collection.upsert(
            ids=[data["id"]],
            documents=[data["document"]],
            metadatas=[data["metadata"]]
        )
        logger.info(f"✅ [{datetime.now().strftime('%H:%M:%S')}] [ChromaDB] Saved txn: {transaction.apt_name}")

    def delete(self, report_id: str) -> None:
        """Deletes a report by ID."""
        self.collection.delete(ids=[report_id])
        logger.info(f"🗑️ [ChromaDB] Deleted report: {report_id}")

    def get_transactions(
        self,
        limit: int = 50,
        where: Optional[Dict[str, Any]] = None,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Fetches raw transaction data (metadata) from ChromaDB.
        - ChromaDB .get()은 $eq 필터만 지원하므로 district_code 필터만 DB 레벨에서 처리
        - date_from / date_to 범위 필터는 Python 레벨에서 후처리
        """
        try:
            # ChromaDB .get()은 $eq 호환 필터만 지원
            fetch_limit = min(limit * 10, 500)  # 후처리 여유분 확보
            results = self.collection.get(
                limit=fetch_limit,
                where=where,
                include=["metadatas"]
            )

            if not results or not results["metadatas"]:
                return []

            metadatas = results["metadatas"]

            # Python 레벨 날짜 범위 필터
            if date_from:
                metadatas = [m for m in metadatas if str(m.get("deal_date", "")) >= date_from]
            if date_to:
                metadatas = [m for m in metadatas if str(m.get("deal_date", "")) <= date_to]

            # 최신 거래일 순 정렬 후 limit 적용
            metadatas.sort(key=lambda x: str(x.get("deal_date", "")), reverse=True)
            return metadatas[:limit]
        except Exception as e:
            logger.error(f"⚠️ [ChromaDB] Error fetching transactions: {e}")
            return []
    def save_policy(self, policy_id: str, content: str, metadata: Dict[str, Any]) -> None:
        """Saves a policy or development fact to ChromaDB."""
        logger.info(f"💾 [ChromaDB] Saving policy: {policy_id}")
        self.policy_collection.upsert(
            ids=[policy_id],
            documents=[content],
            metadatas=[metadata]
        )

    def search_policy(self, query: str, n_results: int = 5) -> List[Dict[str, Any]]:
        """Searches for relevant policy/development facts."""
        logger.info(f"🔎 [ChromaDB] Searching policy for: '{query}'")
        results = self.policy_collection.query(
            query_texts=[query],
            n_results=n_results
        )
        
        items = []
        if results["ids"]:
            for i in range(len(results["ids"][0])):
                items.append({
                    "id": results["ids"][0][i],
                    "content": results["documents"][0][i],
                    "metadata": results["metadatas"][0][i]
                })
        return items
