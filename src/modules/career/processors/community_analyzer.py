import json
from typing import Dict, List

from modules.career.processors.base import BaseAnalyzer
from modules.career.models import (
    CommunityTrendAnalysis,
    KoreanPost,
    NitterTweet,
    RedditPost,
)
from core.prompt_optimizer import PromptTokenOptimizer as PTO

_MAX_POSTS = 25
_TEXT_MAX = 150


class CommunityAnalyzer(BaseAnalyzer):
    """Reddit, Mastodon, 국내 커뮤니티 데이터를 LLM으로 분석해 트렌드와 의견을 추출한다."""

    def analyze(
        self,
        reddit_posts: List[RedditPost],
        nitter_tweets: List[NitterTweet],
        korean_posts: List[KoreanPost],
        collection_status: Dict[str, str],
    ) -> CommunityTrendAnalysis:
        try:
            # 입력 압축: 소스당 25개 제한 + 텍스트 필드 트런케이션
            slim_reddit = []
            for p in reddit_posts[:_MAX_POSTS]:
                d = p.model_dump()
                if d.get("selftext"):
                    d["selftext"] = PTO.truncate(d["selftext"], _TEXT_MAX)
                slim_reddit.append(d)

            slim_tweets = []
            for t in nitter_tweets[:_MAX_POSTS]:
                d = t.model_dump()
                if d.get("text"):
                    d["text"] = PTO.truncate(d["text"], _TEXT_MAX)
                slim_tweets.append(d)

            slim_korean = [k.model_dump() for k in korean_posts[:_MAX_POSTS]]

            result = self._call_llm("career/community_analyst", {
                "reddit_posts": json.dumps(slim_reddit, ensure_ascii=False),
                "nitter_tweets": json.dumps(slim_tweets, ensure_ascii=False),
                "korean_posts": json.dumps(slim_korean, ensure_ascii=False),
                "collection_status": json.dumps(collection_status, ensure_ascii=False),
            }, CommunityTrendAnalysis)
        except Exception as e:
            self.logger.error(f"CommunityAnalyzer LLM 실패, 기본값 반환: {e}")
            result = CommunityTrendAnalysis()

        # 실제 수집 상태를 항상 우선 (LLM 반환값 override)
        result.collection_status = collection_status
        return result
