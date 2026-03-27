from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any


class JobPosting(BaseModel):
    id: str
    company: str
    position: str
    skills: List[str] = Field(default_factory=list)
    salary_min: Optional[int] = None
    salary_max: Optional[int] = None
    experience_min: Optional[int] = None
    url: str
    source: str  # "wanted" | "jumpit"


class TrendingRepo(BaseModel):
    name: str
    description: str
    language: str
    stars_today: int
    url: str


class HNStory(BaseModel):
    id: int
    title: str
    url: Optional[str] = None
    score: int


class DevToArticle(BaseModel):
    id: int
    title: str
    url: str
    tags: List[str] = Field(default_factory=list)
    reactions: int


class JobAnalysis(BaseModel):
    top_skills: List[str] = Field(default_factory=list)
    skill_frequency: Dict[str, int] = Field(default_factory=dict)
    salary_range: Dict[str, Optional[int]] = Field(default_factory=dict)
    hiring_signal: str = ""
    notable_postings: List[Dict[str, Any]] = Field(default_factory=list)


class TrendAnalysis(BaseModel):
    hot_topics: List[str] = Field(default_factory=list)
    github_top: List[Dict[str, Any]] = Field(default_factory=list)
    hn_highlight: str = ""
    devto_picks: List[Dict[str, Any]] = Field(default_factory=list)
    backend_relevance_comment: str = ""


class SkillGapAnalysis(BaseModel):
    gap_score: int = Field(0, ge=0, le=100)
    missing_skills: List[Dict[str, Any]] = Field(default_factory=list)
    study_recommendations: List[Dict[str, Any]] = Field(default_factory=list)
    gap_trend: str = ""


class SkillGapSnapshot(BaseModel):
    date: str
    gap_score: int
    missing_skills: List[str] = Field(default_factory=list)
    study_recommendations: List[Dict[str, Any]] = Field(default_factory=list)
