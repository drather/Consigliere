import json
from typing import List, Dict, Any
from core.llm import LLMClient
from core.prompt_loader import PromptLoader
from core.logger import get_logger
from modules.career.models import TrendingRepo, HNStory, DevToArticle, TrendAnalysis

logger = get_logger(__name__)


class TrendAnalyzer:
    def __init__(self, llm: LLMClient, prompt_loader: PromptLoader):
        self.llm = llm
        self.prompt_loader = prompt_loader

    def analyze(
        self,
        repos: List[TrendingRepo],
        stories: List[HNStory],
        articles: List[DevToArticle],
        github_languages: List[str],
    ) -> TrendAnalysis:
        try:
            _, prompt = self.prompt_loader.load("career/trend_analyst", variables={
                "github_repos": json.dumps(
                    [r.model_dump() for r in repos], ensure_ascii=False
                ),
                "hn_stories": json.dumps(
                    [s.model_dump() for s in stories], ensure_ascii=False
                ),
                "devto_articles": json.dumps(
                    [a.model_dump() for a in articles], ensure_ascii=False
                ),
                "github_languages": json.dumps(github_languages, ensure_ascii=False),
            })
            data = self.llm.generate_json(prompt)
            return TrendAnalysis(**data)
        except Exception as e:
            logger.error(f"TrendAnalyzer 실패, 기본값 반환: {e}")
            return TrendAnalysis()
