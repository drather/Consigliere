import asyncio
from typing import List

import aiohttp

from core.logger import get_logger
from modules.career.collectors.base import BaseCollector
from modules.career.models import RedditPost

logger = get_logger(__name__)

_SELFTEXT_MAX = 500
_BASE_URL = "https://www.reddit.com"
# Reddit 공개 JSON API: 인증 없이 사용 가능, User-Agent만 필요
_HEADERS = {
    "User-Agent": "Consigliere Career Bot 1.0 (by /u/consigliere_bot)",
    "Accept": "application/json",
}


class RedditCollector(BaseCollector):
    """Reddit 공개 JSON API로 subreddit별 인기 게시물을 수집한다.

    인증 불필요 — /r/{subreddit}/top.json?t=day 엔드포인트 사용.
    Rate limit: 비인증 60req/min (일 1회 수집 기준 충분).
    """

    def __init__(
        self,
        subreddits: List[str],
        limit: int,
        min_score: int,
        user_agent: str = "Consigliere Career Bot 1.0",
        timeout: int = 20,
    ):
        super().__init__()
        self.subreddits = subreddits
        self.limit = limit
        self.min_score = min_score
        self.headers = {**_HEADERS, "User-Agent": user_agent}
        self.timeout = timeout

    async def collect(self) -> List[RedditPost]:
        semaphore = asyncio.Semaphore(3)
        async with aiohttp.ClientSession(headers=self.headers, connector=self.make_connector()) as session:
            tasks = [
                self._fetch_subreddit(session, semaphore, name)
                for name in self.subreddits
            ]
            results = await asyncio.gather(*tasks)

        posts = [p for sub in results for p in sub]
        logger.info(f"Reddit 수집 완료: {len(posts)}개 (subreddits={self.subreddits})")
        return posts

    async def _fetch_subreddit(
        self,
        session: aiohttp.ClientSession,
        semaphore: asyncio.Semaphore,
        name: str,
    ) -> List[RedditPost]:
        url = f"{_BASE_URL}/r/{name}/top.json"
        params = {"t": "day", "limit": self.limit}
        async with semaphore:
            try:
                async with session.get(
                    url,
                    params=params,
                    timeout=aiohttp.ClientTimeout(total=self.timeout),
                ) as resp:
                    if resp.status == 429:
                        logger.warning(f"r/{name} rate limited (429)")
                        return []
                    if resp.status != 200:
                        logger.warning(f"r/{name} HTTP {resp.status}")
                        return []
                    data = await resp.json()

                posts = self._parse(data, name)
                logger.debug(f"r/{name}: {len(posts)}개 수집")
                return posts
            except aiohttp.ClientError as e:
                logger.error(f"r/{name} 연결 실패: {e}")
                return []
            except Exception as e:
                logger.error(f"r/{name} 수집 실패: {e}")
                return []

    def _parse(self, data: dict, subreddit_name: str) -> List[RedditPost]:
        posts = []
        try:
            children = data.get("data", {}).get("children", [])
        except AttributeError:
            return []

        for child in children:
            try:
                post_data = child.get("data", {})
                if post_data.get("stickied"):
                    continue
                score = int(post_data.get("score", 0))
                if score < self.min_score:
                    continue
                selftext = (post_data.get("selftext") or "")[:_SELFTEXT_MAX]
                posts.append(RedditPost(
                    id=str(post_data.get("id", "")),
                    title=str(post_data.get("title", "")),
                    subreddit=subreddit_name,
                    score=score,
                    url=str(post_data.get("url", "")),
                    num_comments=int(post_data.get("num_comments", 0)),
                    selftext=selftext,
                ))
            except Exception as e:
                logger.debug(f"r/{subreddit_name} 게시물 파싱 실패: {e}")

        return posts
