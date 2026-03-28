import aiohttp
import asyncio
from typing import List
from bs4 import BeautifulSoup

from modules.career.collectors.base import BaseCollector
from modules.career.models import TrendingRepo


class GithubTrendingCollector(BaseCollector):
    """
    GitHub Trending 페이지를 BeautifulSoup으로 스크래핑한다.
    언어별로 수집 후 합산 반환.
    """
    def __init__(self, languages: List[str], trending_url_template: str):
        super().__init__()
        self.languages = languages
        self.trending_url_template = trending_url_template

    async def collect(self) -> List[TrendingRepo]:
        semaphore = asyncio.Semaphore(3)
        async with aiohttp.ClientSession(connector=self.make_connector()) as session:
            tasks = [
                self._fetch_language(session, semaphore, lang)
                for lang in self.languages
            ]
            results = await asyncio.gather(*tasks)
        repos = [repo for sublist in results for repo in sublist]
        self.logger.info(f"GitHub Trending 수집 완료: {len(repos)}개 ({len(self.languages)}개 언어)")
        return repos

    async def _fetch_language(
        self, session: aiohttp.ClientSession, semaphore: asyncio.Semaphore, language: str
    ) -> List[TrendingRepo]:
        url = self.trending_url_template.format(language=language)
        async with semaphore:
            try:
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=15)) as resp:
                    if resp.status != 200:
                        self.logger.warning(f"GitHub Trending {language} HTTP {resp.status}")
                        return []
                    html = await resp.text()
            except Exception as e:
                self.logger.error(f"GitHub Trending {language} 요청 실패: {e}")
                return []

        return self._parse(html, language)

    def _parse(self, html: str, language: str) -> List[TrendingRepo]:
        soup = BeautifulSoup(html, "html.parser")
        repos = []
        for article in soup.select("article.Box-row"):
            try:
                name_tag = article.select_one("h2 a")
                if not name_tag:
                    continue
                name = name_tag.get("href", "").lstrip("/")
                url = f"https://github.com/{name}"

                desc_tag = article.select_one("p")
                description = desc_tag.get_text(strip=True) if desc_tag else ""

                lang_tag = article.select_one("[itemprop='programmingLanguage']")
                lang = lang_tag.get_text(strip=True) if lang_tag else language

                stars_tag = article.select_one("span.d-inline-block.float-sm-right")
                stars_text = stars_tag.get_text(strip=True).replace(",", "") if stars_tag else "0"
                try:
                    stars_today = int(stars_text.split()[0])
                except (ValueError, IndexError):
                    stars_today = 0

                repos.append(TrendingRepo(
                    name=name,
                    description=description,
                    language=lang,
                    stars_today=stars_today,
                    url=url,
                ))
            except Exception as e:
                self.logger.debug(f"레포 파싱 실패: {e}")
                continue
        return repos
