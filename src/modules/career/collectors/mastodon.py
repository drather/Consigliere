from typing import List

import aiohttp
from bs4 import BeautifulSoup

from core.logger import get_logger
from modules.career.collectors.base import BaseCollector
from modules.career.models import NitterTweet

logger = get_logger(__name__)


class MastodonCollector(BaseCollector):
    """Mastodon 공개 해시태그 타임라인 API로 기술 트렌드 게시물을 수집한다.

    인증 불필요 — /api/v1/timelines/tag/{hashtag} 공개 엔드포인트 사용.
    여러 인스턴스를 순차 시도해 첫 응답을 사용하고, 전체 실패 시 빈 리스트 반환.
    """

    def __init__(
        self,
        instances: List[str],
        hashtags: List[str],
        limit_per_hashtag: int = 10,
        timeout: int = 15,
    ):
        super().__init__()
        self.instances = instances
        self.hashtags = hashtags
        self.limit_per_hashtag = limit_per_hashtag
        self.timeout = timeout

    async def collect(self) -> List[NitterTweet]:
        headers = {"User-Agent": "Consigliere Career Bot 1.0"}
        all_posts: List[NitterTweet] = []
        seen_ids: set = set()

        async with aiohttp.ClientSession(headers=headers, connector=self.make_connector()) as session:
            for hashtag in self.hashtags:
                posts = await self._fetch_hashtag(session, hashtag)
                for post in posts:
                    if post.id not in seen_ids:
                        seen_ids.add(post.id)
                        all_posts.append(post)

        logger.info(f"Mastodon 수집 완료: {len(all_posts)}개 게시물 (hashtags={self.hashtags})")
        return all_posts

    async def _fetch_hashtag(
        self, session: aiohttp.ClientSession, hashtag: str
    ) -> List[NitterTweet]:
        for instance in self.instances:
            url = f"https://{instance}/api/v1/timelines/tag/{hashtag}"
            params = {"limit": self.limit_per_hashtag}
            try:
                async with session.get(
                    url, params=params, timeout=aiohttp.ClientTimeout(total=self.timeout)
                ) as resp:
                    if resp.status != 200:
                        logger.warning(f"Mastodon {instance} HTTP {resp.status} (#{hashtag})")
                        continue
                    data = await resp.json()
                    posts = self._parse(data)
                    if posts:
                        return posts
                    logger.warning(f"Mastodon {instance} 응답 왔으나 게시물 없음 (#{hashtag})")
            except aiohttp.ClientError as e:
                logger.warning(f"Mastodon {instance} 연결 실패 (#{hashtag}): {e}")
            except Exception as e:
                logger.warning(f"Mastodon {instance} 예외 (#{hashtag}): {e}")

        logger.error(f"모든 Mastodon 인스턴스 실패 (#{hashtag})")
        return []

    def _parse(self, data: list) -> List[NitterTweet]:
        posts = []
        for item in data:
            try:
                post = self._parse_item(item)
                if post:
                    posts.append(post)
            except Exception as e:
                logger.debug(f"Mastodon 게시물 파싱 실패: {e}")
        return posts

    def _parse_item(self, item: dict):
        post_id = str(item.get("id", ""))
        if not post_id:
            return None

        raw_content = item.get("content", "")
        text = BeautifulSoup(raw_content, "html.parser").get_text(separator=" ", strip=True)
        if not text:
            return None

        account = item.get("account", {})
        username = account.get("acct") or account.get("username", "")
        created_at = item.get("created_at", "")
        url = item.get("url", "")

        return NitterTweet(
            id=post_id,
            text=text,
            username=username,
            date=created_at,
            url=url,
        )
