import re
from typing import List, Optional
from urllib.parse import quote_plus

import aiohttp
from bs4 import BeautifulSoup

from core.logger import get_logger
from modules.career.collectors.base import BaseCollector
from modules.career.models import NitterTweet

logger = get_logger(__name__)

_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
    "Accept-Language": "en-US,en;q=0.9",
}


class NitterCollector(BaseCollector):
    """Nitter 인스턴스를 순차 시도해 Twitter 트렌드를 스크래핑한다.

    인스턴스 불안정에 대비해:
    - 각 인스턴스 실패 시 다음으로 fallback
    - 전체 실패 시 빈 리스트 반환 (파이프라인 중단 없음)
    """

    def __init__(
        self,
        instances: List[str],
        keywords: List[str],
        timeout: int = 15,
        max_tweets_per_keyword: int = 10,
    ):
        super().__init__()
        self.instances = instances
        self.keywords = keywords
        self.timeout = timeout
        self.max_tweets_per_keyword = max_tweets_per_keyword

    async def collect(self) -> List[NitterTweet]:
        all_tweets: List[NitterTweet] = []
        seen_ids: set = set()

        async with aiohttp.ClientSession(headers=_HEADERS) as session:
            for keyword in self.keywords:
                tweets = await self._search_keyword(session, keyword)
                for tweet in tweets:
                    if tweet.id not in seen_ids:
                        seen_ids.add(tweet.id)
                        all_tweets.append(tweet)

        logger.info(f"Nitter 수집 완료: {len(all_tweets)}개 트윗 (keywords={self.keywords})")
        return all_tweets

    async def _search_keyword(
        self, session: aiohttp.ClientSession, keyword: str
    ) -> List[NitterTweet]:
        encoded = quote_plus(keyword)
        for instance in self.instances:
            url = f"{instance}/search?q={encoded}&f=tweets"
            try:
                async with session.get(
                    url, timeout=aiohttp.ClientTimeout(total=self.timeout)
                ) as resp:
                    if resp.status != 200:
                        logger.warning(f"Nitter {instance} HTTP {resp.status} (keyword={keyword})")
                        continue
                    html = await resp.text()
                tweets = self._parse(html, instance)
                if tweets:
                    return tweets[: self.max_tweets_per_keyword]
                logger.warning(f"Nitter {instance} 응답은 왔지만 트윗 없음 (keyword={keyword})")
            except aiohttp.ClientError as e:
                logger.warning(f"Nitter {instance} 연결 실패: {e}")
            except Exception as e:
                logger.warning(f"Nitter {instance} 예외: {e}")

        logger.error(f"모든 Nitter 인스턴스 실패 (keyword={keyword})")
        return []

    def _parse(self, html: str, base_url: str) -> List[NitterTweet]:
        soup = BeautifulSoup(html, "html.parser")
        tweets: List[NitterTweet] = []

        for item in soup.select("div.timeline-item"):
            try:
                tweet = self._parse_item(item, base_url)
                if tweet:
                    tweets.append(tweet)
            except Exception as e:
                logger.debug(f"트윗 파싱 실패: {e}")

        return tweets

    def _parse_item(self, item, base_url: str) -> Optional[NitterTweet]:
        # 사용자명
        username_tag = item.select_one("a.username")
        if not username_tag:
            return None
        username = username_tag.get_text(strip=True).lstrip("@")

        # 트윗 텍스트
        content_tag = item.select_one("div.tweet-content")
        if not content_tag:
            return None
        text = content_tag.get_text(strip=True)

        # 날짜 & ID (href="/username/status/ID")
        date_tag = item.select_one("span.tweet-date a")
        date_str = ""
        tweet_id = ""
        tweet_url = ""
        if date_tag:
            date_str = date_tag.get("title", "")
            href = date_tag.get("href", "")
            match = re.search(r"/status/(\d+)", href)
            if match:
                tweet_id = match.group(1)
                tweet_url = f"{base_url}{href}"

        if not tweet_id:
            tweet_id = re.sub(r"\W+", "", text)[:20]  # fallback ID

        return NitterTweet(
            id=tweet_id,
            text=text,
            username=username,
            date=date_str,
            url=tweet_url,
        )
