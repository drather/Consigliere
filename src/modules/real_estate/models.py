from dataclasses import dataclass, field
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime, date


@dataclass
class ApartmentMaster:
    """아파트 단지 마스터 정보 (공동주택 기본정보 API getAphusBassInfoV4 수집)."""
    apt_name: str
    district_code: str           # 5자리 sigunguCd
    complex_code: str            # kaptCode
    # 기본 정보
    household_count: int         # hoCnt (세대수)
    building_count: int          # kaptDongCnt (동수)
    parking_count: int           # 주차대수 (API 미제공)
    constructor: str             # kaptBcompany (시공사)
    approved_date: str           # kaptUsedate (사용승인일 YYYYMMDD)
    # 주소
    road_address: str = ""       # doroJuso (도로명주소)
    legal_address: str = ""      # kaptAddr (법정동주소)
    # 건물 구조
    top_floor: int = 0           # kaptTopFloor (최고층수)
    base_floor: int = 0          # kaptBaseFloor (지하층수)
    total_area: float = 0.0      # kaptTarea (연면적 ㎡)
    # 단지 특성
    heat_type: str = ""          # codeHeatNm (난방방식)
    developer: str = ""          # kaptAcompany (시행사)
    elevator_count: int = 0      # kaptdEcntp (승객용 승강기대수)
    # 전용면적별 세대수
    units_60: int = 0            # kaptMparea60 (60㎡ 이하)
    units_85: int = 0            # kaptMparea85 (60~85㎡)
    units_135: int = 0           # kaptMparea135 (85~135㎡)
    units_136_plus: int = 0      # kaptMparea136 (135㎡ 초과)
    # 행정구역 (API 1: getTotalAptList3 — 시도/시군구/읍면동 필터링용)
    sido: str = ""               # as1 (시도, 예: 서울특별시)
    sigungu: str = ""            # as2 (시군구, 예: 서초구)
    eupmyeondong: str = ""       # as3 (읍면동, 예: 반포동)
    ri: str = ""                 # as4 (리, 도심지역은 보통 빈값)
    fetched_at: str = ""

@dataclass
class AptMasterEntry:
    """apt_master 테이블 레코드 — 실거래가 기반 단지 마스터.

    Transaction-First 아키텍처의 핵심 엔티티.
    실거래가에 등장한 모든 단지가 존재하며, apt_details(공동주택 기본정보)는 optional 조인.
    """
    apt_name: str
    district_code: str
    sido: str = ""
    sigungu: str = ""
    complex_code: Optional[str] = None      # FK → apartments/apt_details (nullable)
    tx_count: int = 0                        # 보유 거래 건수 (캐싱)
    first_traded: Optional[str] = None      # 최초 거래일 YYYY-MM-DD
    last_traded: Optional[str] = None       # 최근 거래일 YYYY-MM-DD
    created_at: str = ""
    id: Optional[int] = None                # auto-increment PK (신규 삽입 시 None)
    pnu: Optional[str] = None               # FK → building_master.mgm_pk (NULLABLE)
    mapping_score: Optional[float] = None   # 매핑 신뢰도 0.0~1.0
    # apartments JOIN으로 채워지는 선택 필드
    household_count: Optional[int] = None
    road_address: Optional[str] = None
    approved_date: Optional[str] = None


@dataclass
class RealEstateTransaction:
    """아파트 실거래가 레코드 (국토부 실거래가 API 수집)."""
    apt_name: str
    district_code: str          # 5자리 시군구 코드
    deal_date: str              # YYYY-MM-DD
    price: int                  # 원 단위
    floor: int = 0
    exclusive_area: float = 0.0
    build_year: int = 0
    road_name: str = ""
    complex_code: Optional[str] = None   # FK → apartments.complex_code (수집 시 자동 해소)
    apt_master_id: Optional[int] = None  # FK → apt_master.id (Transaction-First 아키텍처)

    def dedup_key(self) -> str:
        """중복 제거용 복합 키."""
        return f"{self.district_code}__{self.apt_name}__{self.deal_date}__{self.floor}__{self.price}"

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
