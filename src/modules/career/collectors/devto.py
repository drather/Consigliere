import aiohttp
import asyncio
from typing import List

from modules.career.collectors.base import BaseCollector
from modules.career.models import DevToArticle


class DevToCollector(BaseCollector):
    """
    dev.to 공개 REST API로 태그별 인기 아티클을 수집한다.
    """
    def __init__(self, api_url: str, tags: List[str], per_page: int):
        super().__init__()
        self.api_url = api_url
        self.tags = tags
        self.per_page = per_page

    async def collect(self) -> List[DevToArticle]:
        semaphore = asyncio.Semaphore(3)
        async with aiohttp.ClientSession() as session:
            tasks = [self._fetch_tag(session, semaphore, tag) for tag in self.tags]
            results = await asyncio.gather(*tasks)

        seen_ids = set()
        articles = []
        for sublist in results:
            for article in sublist:
                if article.id not in seen_ids:
                    seen_ids.add(article.id)
                    articles.append(article)

        self.logger.info(f"Dev.to 수집 완료: {len(articles)}개 ({len(self.tags)}개 태그)")
        return articles

    async def _fetch_tag(
        self, session: aiohttp.ClientSession, semaphore: asyncio.Semaphore, tag: str
    ) -> List[DevToArticle]:
        params = {"tag": tag, "per_page": self.per_page, "top": 1}
        async with semaphore:
            try:
                async with session.get(
                    self.api_url,
                    params=params,
                    timeout=aiohttp.ClientTimeout(total=15),
                ) as resp:
                    if resp.status != 200:
                        self.logger.warning(f"Dev.to tag={tag} HTTP {resp.status}")
                        return []
                    data = await resp.json()
            except Exception as e:
                self.logger.error(f"Dev.to tag={tag} 실패: {e}")
                return []

        articles = []
        for item in data:
            try:
                articles.append(DevToArticle(
                    id=item["id"],
                    title=item["title"],
                    url=item["url"],
                    tags=item.get("tag_list", []),
                    reactions=item.get("positive_reactions_count", 0),
                ))
            except Exception as e:
                self.logger.debug(f"Dev.to 아티클 파싱 실패: {e}")
        return articles
