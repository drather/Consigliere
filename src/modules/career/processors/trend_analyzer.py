import json
from typing import List
from modules.career.processors.base import BaseAnalyzer
from modules.career.models import TrendingRepo, HNStory, DevToArticle, TrendAnalysis
from core.prompt_optimizer import PromptTokenOptimizer as PTO

_MAX_PER_SOURCE = 20
_REPO_DESC_MAX = 200


class TrendAnalyzer(BaseAnalyzer):
    def analyze(
        self,
        repos: List[TrendingRepo],
        stories: List[HNStory],
        articles: List[DevToArticle],
        github_languages: List[str],
    ) -> TrendAnalysis:
        try:
            # 입력 압축: 소스별 20개 제한 + repo description 트런케이션
            slim_repos = []
            for r in repos[:_MAX_PER_SOURCE]:
                d = r.model_dump()
                if d.get("description"):
                    d["description"] = PTO.truncate(d["description"], _REPO_DESC_MAX)
                slim_repos.append(d)

            slim_stories = [s.model_dump() for s in stories[:_MAX_PER_SOURCE]]
            slim_articles = [a.model_dump() for a in articles[:_MAX_PER_SOURCE]]

            return self._call_llm("career/trend_analyst", {
                "github_repos": json.dumps(slim_repos, ensure_ascii=False),
                "hn_stories": json.dumps(slim_stories, ensure_ascii=False),
                "devto_articles": json.dumps(slim_articles, ensure_ascii=False),
                "github_languages": json.dumps(github_languages, ensure_ascii=False),
            }, TrendAnalysis)
        except Exception as e:
            self.logger.error(f"TrendAnalyzer 실패, 기본값 반환: {e}")
            return TrendAnalysis()
