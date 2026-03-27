import aiohttp
import asyncio
from typing import List

from modules.career.collectors.base import BaseCollector
from modules.career.models import HNStory


class HackerNewsCollector(BaseCollector):
    """
    Hacker News Firebase REST API로 top stories를 수집한다.
    min_score 이상인 스토리만 반환.
    """
    def __init__(self, top_stories_url: str, item_url_template: str, min_score: int, stories_limit: int):
        super().__init__()
        self.top_stories_url = top_stories_url
        self.item_url_template = item_url_template
        self.min_score = min_score
        self.stories_limit = stories_limit

    async def collect(self) -> List[HNStory]:
        async with aiohttp.ClientSession() as session:
            ids = await self._fetch_ids(session)
            ids = ids[: self.stories_limit]

            semaphore = asyncio.Semaphore(5)
            tasks = [self._fetch_item(session, semaphore, id_) for id_ in ids]
            items = await asyncio.gather(*tasks)

        stories = [s for s in items if s is not None and s.score >= self.min_score]
        self.logger.info(f"HN 수집 완료: {len(stories)}개 (min_score={self.min_score})")
        return stories

    async def _fetch_ids(self, session: aiohttp.ClientSession) -> List[int]:
        try:
            async with session.get(self.top_stories_url, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                return await resp.json()
        except Exception as e:
            self.logger.error(f"HN top stories 수집 실패: {e}")
            return []

    async def _fetch_item(
        self, session: aiohttp.ClientSession, semaphore: asyncio.Semaphore, id_: int
    ):
        url = self.item_url_template.format(id=id_)
        async with semaphore:
            try:
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                    data = await resp.json()
                    if not data or data.get("type") != "story":
                        return None
                    return HNStory(
                        id=data["id"],
                        title=data.get("title", ""),
                        url=data.get("url"),
                        score=data.get("score", 0),
                    )
            except Exception as e:
                self.logger.debug(f"HN item {id_} 실패: {e}")
                return None
