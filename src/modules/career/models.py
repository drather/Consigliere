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


# ── Community Trend Models ────────────────────────────────────────────────────

class RedditPost(BaseModel):
    id: str
    title: str
    subreddit: str
    score: int = 0
    url: str = ""
    num_comments: int = 0
    selftext: str = ""  # 500자 truncate


class NitterTweet(BaseModel):
    id: str
    text: str
    username: str
    date: str = ""
    url: str = ""


class KoreanPost(BaseModel):
    id: str
    title: str
    source: str  # "clien" | "dcinside"
    url: str = ""
    views: int = 0
    comments: int = 0
    date: str = ""


class CommunityTrendAnalysis(BaseModel):
    hot_topics: List[str] = Field(default_factory=list)
    key_opinions: List[str] = Field(default_factory=list)
    emerging_concerns: List[str] = Field(default_factory=list)
    community_summary: str = ""
    collection_status: Dict[str, str] = Field(default_factory=dict)
    # collection_status keys: "reddit" | "nitter" | "clien" | "dcinside"
    # values: "ok" | "failed" | "partial"
