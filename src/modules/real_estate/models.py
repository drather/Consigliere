from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime

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
