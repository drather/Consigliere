from typing import List

import aiohttp

from core.logger import get_logger
from modules.career.collectors.base import BaseCollector
from modules.career.models import NitterTweet

logger = get_logger(__name__)

_SEARCH_URL = "https://api.twitter.com/2/tweets/search/recent"


class TwitterCollector(BaseCollector):
    """Twitter API v2 Recent Search를 이용해 기술 트렌드 트윗을 수집한다.

    Bearer Token 인증 (OAuth 2.0 App-Only).
    각 키워드별 최대 max_results_per_keyword개 수집 후 중복 제거.
    """

    def __init__(
        self,
        bearer_token: str,
        keywords: List[str],
        max_results_per_keyword: int = 10,
        timeout: int = 15,
    ):
        super().__init__()
        self.bearer_token = bearer_token
        self.keywords = keywords
        self.max_results_per_keyword = min(max_results_per_keyword, 100)
        self.timeout = timeout

    async def collect(self) -> List[NitterTweet]:
        headers = {"Authorization": f"Bearer {self.bearer_token}"}
        all_tweets: List[NitterTweet] = []
        seen_ids: set = set()
        async with aiohttp.ClientSession(headers=headers, connector=self.make_connector()) as session:
            for keyword in self.keywords:
                tweets = await self._search(session, keyword)
                for tweet in tweets:
                    if tweet.id not in seen_ids:
                        seen_ids.add(tweet.id)
                        all_tweets.append(tweet)

        logger.info(f"Twitter API 수집 완료: {len(all_tweets)}개 트윗")
        return all_tweets

    async def _search(self, session: aiohttp.ClientSession, keyword: str) -> List[NitterTweet]:
        params = {
            "query": f"{keyword} -is:retweet lang:en",
            "max_results": self.max_results_per_keyword,
            "tweet.fields": "created_at,author_id",
            "expansions": "author_id",
            "user.fields": "username",
        }
        try:
            async with session.get(
                _SEARCH_URL,
                params=params,
                timeout=aiohttp.ClientTimeout(total=self.timeout),
            ) as resp:
                if resp.status != 200:
                    body = await resp.text()
                    logger.warning(f"Twitter API HTTP {resp.status} (keyword={keyword}): {body[:200]}")
                    return []
                data = await resp.json()
                return self._parse(data)
        except aiohttp.ClientError as e:
            logger.warning(f"Twitter API 연결 실패 (keyword={keyword}): {e}")
            return []
        except Exception as e:
            logger.warning(f"Twitter API 예외 (keyword={keyword}): {e}")
            return []

    def _parse(self, data: dict) -> List[NitterTweet]:
        users = {
            u["id"]: u.get("username", "")
            for u in data.get("includes", {}).get("users", [])
        }
        tweets = []
        for t in data.get("data", []):
            tweet_id = t.get("id", "")
            tweets.append(NitterTweet(
                id=tweet_id,
                text=t.get("text", ""),
                username=users.get(t.get("author_id", ""), ""),
                date=t.get("created_at", ""),
                url=f"https://x.com/i/web/status/{tweet_id}" if tweet_id else "",
            ))
        return tweets
