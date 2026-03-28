import json
from typing import Dict, List

from core.llm import LLMClient
from core.logger import get_logger
from core.prompt_loader import PromptLoader
from modules.career.models import (
    CommunityTrendAnalysis,
    KoreanPost,
    NitterTweet,
    RedditPost,
)

logger = get_logger(__name__)


class CommunityAnalyzer:
    """Reddit, Nitter, 국내 커뮤니티 데이터를 LLM으로 분석해 트렌드와 의견을 추출한다."""

    def __init__(self, llm: LLMClient, prompt_loader: PromptLoader):
        self.llm = llm
        self.prompt_loader = prompt_loader

    def analyze(
        self,
        reddit_posts: List[RedditPost],
        nitter_tweets: List[NitterTweet],
        korean_posts: List[KoreanPost],
        collection_status: Dict[str, str],
    ) -> CommunityTrendAnalysis:
        try:
            _, prompt = self.prompt_loader.load(
                "career/community_analyst",
                variables={
                    "reddit_posts": json.dumps(
                        [p.model_dump() for p in reddit_posts], ensure_ascii=False
                    ),
                    "nitter_tweets": json.dumps(
                        [t.model_dump() for t in nitter_tweets], ensure_ascii=False
                    ),
                    "korean_posts": json.dumps(
                        [k.model_dump() for k in korean_posts], ensure_ascii=False
                    ),
                    "collection_status": json.dumps(collection_status, ensure_ascii=False),
                },
            )
            data = self.llm.generate_json(prompt)
            result = CommunityTrendAnalysis(**data)
        except Exception as e:
            logger.error(f"CommunityAnalyzer LLM 실패, 기본값 반환: {e}")
            result = CommunityTrendAnalysis()

        # 실제 수집 상태를 항상 우선 (LLM 반환값 override)
        result.collection_status = collection_status
        return result
