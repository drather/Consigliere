import json
from typing import List
from modules.career.processors.base import BaseAnalyzer
from modules.career.models import TrendingRepo, HNStory, DevToArticle, TrendAnalysis


class TrendAnalyzer(BaseAnalyzer):
    def analyze(
        self,
        repos: List[TrendingRepo],
        stories: List[HNStory],
        articles: List[DevToArticle],
        github_languages: List[str],
    ) -> TrendAnalysis:
        try:
            return self._call_llm("career/trend_analyst", {
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
            }, TrendAnalysis)
        except Exception as e:
            self.logger.error(f"TrendAnalyzer 실패, 기본값 반환: {e}")
            return TrendAnalysis()
