from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime, date

class RealEstateTransaction(BaseModel):
    """
    Represents a single apartment transaction record from the government API.
    """
    deal_date: date = Field(..., description="Transaction date (contract date)")
    district_code: str = Field(..., description="District code (Legal dong code)")
    apt_name: str = Field(..., description="Name of the apartment")
    exclusive_area: float = Field(..., description="Exclusive area in m2")
    floor: int = Field(..., description="Floor number")
    price: int = Field(..., description="Transaction price in KRW (converted from 10k units)")
    build_year: int = Field(..., description="Year the apartment was built")
    road_name: Optional[str] = Field(None, description="Road name address")
    cancel_deal_date: Optional[date] = Field(None, description="Date the deal was cancelled (if applicable)")

    def to_chroma_format(self) -> Dict[str, Any]:
        """
        Converts transaction to ChromaDB compatible format.
        ID: Unique composite key.
        Document: Natural language summary for search.
        Metadata: Structured fields.
        """
        txn_id = f"txn_{self.deal_date}_{self.apt_name}_{self.floor}_{self.price}"
        
        doc_text = (
            f"{self.deal_date} 거래. "
            f"{self.apt_name} {self.floor}층. "
            f"전용 {self.exclusive_area}m². "
            f"거래금액 {self.price // 10000}만원."
        )
        
        # Pydantic date/datetime needs to be string for Chroma metadata
        metadata = self.model_dump()
        metadata["deal_date"] = str(self.deal_date)
        if self.cancel_deal_date:
            metadata["cancel_deal_date"] = str(self.cancel_deal_date)
            
        return {
            "id": txn_id,
            "document": doc_text,
            "metadata": metadata
        }

    model_config = {"extra": "allow"}

class NewsArticle(BaseModel):
    """
    Represents a single news article fetched from Naver.
    """
    title: str
    origin_link: str = Field(..., alias="link")
    description: str
    pub_date: str  # Kept as string for simplicity, can be parsed if needed

class NewsAnalysisReport(BaseModel):
    """
    Daily AI-generated report summarizing news and trends.
    """
    date: str = Field(..., description="Report Date (YYYY-MM-DD)")
    keywords: List[str] = Field(..., description="Top 5 keywords of the day")
    summary: str = Field(..., description="3-sentence summary of major news")
    trend_analysis: str = Field(..., description="Comparison with previous trends (RAG result)")
    references: List[NewsArticle] = Field(default_factory=list, description="List of source articles")
    
    def to_markdown(self) -> str:
        keywords_str = ", ".join([f"`{k}`" for k in self.keywords])
        
        # Format references
        ref_section = "## 🔗 References\n"
        for i, article in enumerate(self.references[:10], 1): # Top 10 only to keep it clean
            ref_section += f"{i}. [{article.title}]({article.origin_link})\n"

        return (
            f"# 📰 Real Estate News Report ({self.date})\n\n"
            f"## 🔑 Key Topics\n{keywords_str}\n\n"
            f"## 📝 Daily Summary\n{self.summary}\n\n"
            f"## 📉 Trend Insight\n{self.trend_analysis}\n\n"
            f"{ref_section}"
        )

class RealEstateMetadata(BaseModel):
    """
    Structured metadata for filtering and fast searching in Vector DB.
    """
    complex_name: str = Field(..., description="Name of the apartment complex")
    price: Optional[int] = Field(None, description="Actual transaction price in KRW")
    has_elementary_school: bool = Field(False, description="Whether there is an elementary school inside or very close")
    pros: List[str] = Field(default_factory=list, description="List of advantages")
    cons: List[str] = Field(default_factory=list, description="List of disadvantages")
    region: Optional[str] = Field(None, description="Geographical region or station name")
    
    # Allow extra fields for flexibility (NoSQL style)
    model_config = {"extra": "allow"}

class RealEstateReport(BaseModel):
    """
    The full report object containing both structured metadata and raw content.
    """
    report_id: str = Field(..., description="Unique ID, usually the complex name")
    metadata: RealEstateMetadata
    content: str = Field(..., description="Full unstructured text of the tour report")
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)

    def to_chroma_format(self) -> Dict[str, Any]:
        """
        Converts the model into a format suitable for ChromaDB.
        """
        return {
            "id": self.report_id,
            "document": self.content,
            "metadata": self.metadata.model_dump()
        }
