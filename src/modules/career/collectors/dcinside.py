import re
from typing import List, Optional

import aiohttp
from bs4 import BeautifulSoup

from core.logger import get_logger
from modules.career.collectors.base import BaseCollector
from modules.career.models import KoreanPost

logger = get_logger(__name__)

_BASE_URL = "https://gall.dcinside.com"
_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "ko-KR,ko;q=0.9,en;q=0.8",
    "Referer": "https://gall.dcinside.com/",
}


class DCInsideCollector(BaseCollector):
    """디씨인사이드 갤러리를 스크래핑해 최신 게시물을 수집한다.

    anti-bot 정책으로 403 응답이 간헐적으로 발생할 수 있으며,
    이 경우 빈 리스트를 반환하고 collection_status를 "failed"로 기록한다.
    """

    def __init__(self, gallery_id: str, list_url: str, limit: int = 20):
        super().__init__()
        self.gallery_id = gallery_id
        self.list_url = list_url
        self.limit = limit

    async def collect(self) -> List[KoreanPost]:
        async with aiohttp.ClientSession(headers=_HEADERS, connector=self.make_connector()) as session:
            async with session.get(
                self.list_url,
                timeout=aiohttp.ClientTimeout(total=20),
            ) as resp:
                if resp.status == 403:
                    logger.warning(f"디씨인사이드 403 (anti-bot) — gallery={self.gallery_id}")
                    return []
                if resp.status != 200:
                    logger.warning(f"디씨인사이드 HTTP {resp.status}")
                    return []
                html = await resp.text()

        posts = self._parse(html)
        logger.info(f"디씨인사이드 수집 완료: {len(posts)}개 (gallery={self.gallery_id})")
        return posts[: self.limit]

    def _parse(self, html: str) -> List[KoreanPost]:
        soup = BeautifulSoup(html, "html.parser")
        posts: List[KoreanPost] = []

        for row in soup.select("tr.ub-content"):
            try:
                post = self._parse_row(row)
                if post:
                    posts.append(post)
            except Exception as e:
                logger.debug(f"디씨 행 파싱 실패: {e}")

        return posts

    def _parse_row(self, row) -> Optional[KoreanPost]:
        # 공지 행 필터링
        num_td = row.select_one("td.gall_num")
        if not num_td:
            return None
        num_text = num_td.get_text(strip=True)
        if not num_text.isdigit():
            return None  # "공지", "설문" 등 제거

        post_id = num_text

        # 제목 & URL
        title_td = row.select_one("td.gall_tit")
        if not title_td:
            return None

        link_tag = title_td.select_one("a:first-child")
        if not link_tag:
            return None

        # 제목에서 [답글 수] 제거
        for span in title_td.select("span.reply_num, em.reply_num"):
            span.decompose()
        title = link_tag.get_text(strip=True)
        if not title:
            return None

        href = link_tag.get("href", "")
        url = href if href.startswith("http") else f"{_BASE_URL}{href}"

        # 날짜
        date_td = row.select_one("td.gall_date")
        date_str = ""
        if date_td:
            date_str = date_td.get("title", date_td.get_text(strip=True))

        # 조회수
        count_td = row.select_one("td.gall_count")
        views = 0
        if count_td:
            m = re.search(r"\d+", count_td.get_text().replace(",", ""))
            views = int(m.group()) if m else 0

        # 추천 (댓글 수 대용)
        rec_td = row.select_one("td.gall_recommend")
        comments = 0
        if rec_td:
            m = re.search(r"\d+", rec_td.get_text())
            comments = int(m.group()) if m else 0

        return KoreanPost(
            id=post_id,
            title=title,
            source="dcinside",
            url=url,
            views=views,
            comments=comments,
            date=date_str,
        )
