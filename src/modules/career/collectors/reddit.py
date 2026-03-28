import asyncio
from typing import List

import asyncpraw
import asyncpraw.exceptions

from core.logger import get_logger
from modules.career.collectors.base import BaseCollector
from modules.career.models import RedditPost

logger = get_logger(__name__)

_SELFTEXT_MAX = 500


class RedditCollector(BaseCollector):
    """Reddit 공식 API(asyncpraw)로 subreddit별 인기 게시물을 수집한다."""

    def __init__(
        self,
        subreddits: List[str],
        limit: int,
        min_score: int,
        client_id: str,
        client_secret: str,
        user_agent: str,
    ):
        super().__init__()
        self.subreddits = subreddits
        self.limit = limit
        self.min_score = min_score
        self.client_id = client_id
        self.client_secret = client_secret
        self.user_agent = user_agent

    async def collect(self) -> List[RedditPost]:
        posts: List[RedditPost] = []
        async with asyncpraw.Reddit(
            client_id=self.client_id,
            client_secret=self.client_secret,
            user_agent=self.user_agent,
            requestor_kwargs={"timeout": 30},
        ) as reddit:
            semaphore = asyncio.Semaphore(3)
            tasks = [
                self._fetch_subreddit(reddit, semaphore, name)
                for name in self.subreddits
            ]
            results = await asyncio.gather(*tasks)
        for sub_posts in results:
            posts.extend(sub_posts)
        logger.info(f"Reddit 수집 완료: {len(posts)}개 (subreddits={self.subreddits})")
        return posts

    async def _fetch_subreddit(
        self, reddit: asyncpraw.Reddit, semaphore: asyncio.Semaphore, name: str
    ) -> List[RedditPost]:
        async with semaphore:
            try:
                subreddit = await reddit.subreddit(name)
                posts = []
                async for submission in subreddit.top(time_filter="day", limit=self.limit):
                    if submission.stickied or submission.score < self.min_score:
                        continue
                    posts.append(self._map_post(submission, name))
                logger.debug(f"r/{name}: {len(posts)}개 수집")
                return posts
            except asyncpraw.exceptions.RedditAPIException as e:
                logger.error(f"r/{name} API 오류: {e}")
                return []
            except Exception as e:
                logger.error(f"r/{name} 수집 실패: {e}")
                return []

    def _map_post(self, submission, subreddit_name: str) -> RedditPost:
        selftext = getattr(submission, "selftext", "") or ""
        return RedditPost(
            id=str(submission.id),
            title=str(submission.title),
            subreddit=subreddit_name,
            score=int(submission.score),
            url=str(submission.url),
            num_comments=int(submission.num_comments),
            selftext=selftext[:_SELFTEXT_MAX],
        )
