import re
from typing import List, Optional

import aiohttp
from bs4 import BeautifulSoup

from core.logger import get_logger
from modules.career.collectors.base import BaseCollector
from modules.career.models import KoreanPost

logger = get_logger(__name__)

_BASE_URL = "https://www.clien.net"
_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
    "Accept-Language": "ko-KR,ko;q=0.9,en;q=0.8",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}


class ClienCollector(BaseCollector):
    """클리앙 게시판을 스크래핑해 최신 게시물을 수집한다."""

    def __init__(self, board_url: str, limit: int = 20):
        super().__init__()
        self.board_url = board_url
        self.limit = limit

    async def collect(self) -> List[KoreanPost]:
        async with aiohttp.ClientSession(headers=_HEADERS, connector=self.make_connector()) as session:
            async with session.get(
                self.board_url,
                timeout=aiohttp.ClientTimeout(total=20),
            ) as resp:
                if resp.status != 200:
                    logger.warning(f"클리앙 HTTP {resp.status}")
                    return []
                html = await resp.text()

        posts = self._parse(html)
        logger.info(f"클리앙 수집 완료: {len(posts)}개")
        return posts[: self.limit]

    def _parse(self, html: str) -> List[KoreanPost]:
        soup = BeautifulSoup(html, "html.parser")
        posts: List[KoreanPost] = []

        for row in soup.select("div.list_item.symph_row"):
            try:
                post = self._parse_row(row)
                if post:
                    posts.append(post)
            except Exception as e:
                logger.debug(f"클리앙 행 파싱 실패: {e}")

        return posts

    def _parse_row(self, row) -> Optional[KoreanPost]:
        # 제목 & URL
        link_tag = row.select_one("a.list_subject")
        if not link_tag:
            return None

        title_tag = link_tag.select_one("span.subject_fixed") or link_tag
        title = title_tag.get_text(strip=True)
        if not title:
            return None

        href = link_tag.get("href", "")
        url = href if href.startswith("http") else f"{_BASE_URL}{href}"

        # ID: URL 경로 마지막 세그먼트
        post_id = href.rstrip("/").split("/")[-1]

        # 댓글 수: [N] 형식
        reply_tag = row.select_one("span.list_reply")
        comments = 0
        if reply_tag:
            m = re.search(r"\d+", reply_tag.get_text())
            comments = int(m.group()) if m else 0

        # 조회수
        hit_tag = row.select_one("span.list_hit")
        views = 0
        if hit_tag:
            text = hit_tag.get_text(strip=True).replace(",", "")
            m = re.search(r"\d+", text)
            views = int(m.group()) if m else 0

        # 날짜
        time_tag = row.select_one("span.list_time, time")
        date_str = time_tag.get_text(strip=True) if time_tag else ""

        return KoreanPost(
            id=post_id,
            title=title,
            source="clien",
            url=url,
            views=views,
            comments=comments,
            date=date_str,
        )
