"""
CollectorFactory — config 기반 Collector 생성 책임을 분리한다.

새 수집 소스 추가 시 이 파일만 수정하면 된다.
service.py는 build_*() 메서드를 호출할 뿐, 개별 Collector를 직접 import하지 않는다.
"""
from typing import Dict

from modules.career.collectors.base import BaseCollector
from modules.career.collectors.github_trending import GithubTrendingCollector
from modules.career.collectors.hacker_news import HackerNewsCollector
from modules.career.collectors.devto import DevToCollector
from modules.career.collectors.wanted import WantedCollector
from modules.career.collectors.jumpit import JumpitCollector
from modules.career.collectors.reddit import RedditCollector
from modules.career.collectors.mastodon import MastodonCollector
from modules.career.collectors.clien import ClienCollector
from modules.career.collectors.dcinside import DCInsideCollector


class CollectorFactory:
    """
    CareerConfig를 받아 카테고리별 Collector 딕셔너리를 반환한다.
    키는 데이터 소스 식별자(collection_status, cache 키와 동일)로 사용된다.
    """

    @staticmethod
    def build_trend_collectors(config) -> Dict[str, BaseCollector]:
        """GitHub Trending / Hacker News / Dev.to Collector를 반환한다."""
        ts = config.get("trend_sources", {})
        return {
            "github": GithubTrendingCollector(
                languages=config.get_github_languages(),
                trending_url_template=ts.get(
                    "github_trending_url",
                    "https://github.com/trending/{language}?since=daily",
                ),
            ),
            "hn": HackerNewsCollector(
                top_stories_url=ts.get(
                    "hn_top_stories_url",
                    "https://hacker-news.firebaseio.com/v0/topstories.json",
                ),
                item_url_template=ts.get(
                    "hn_item_url",
                    "https://hacker-news.firebaseio.com/v0/item/{id}.json",
                ),
                min_score=config.get_hn_min_score(),
                stories_limit=config.get("concurrency", {}).get("hn_stories_limit", 30),
            ),
            "devto": DevToCollector(
                api_url=ts.get("devto_api_url", "https://dev.to/api/articles"),
                tags=config.get_devto_tags(),
                per_page=ts.get("devto_per_page", 30),
            ),
        }

    @staticmethod
    def build_job_collectors(config) -> Dict[str, BaseCollector]:
        """Wanted / Jumpit Collector를 반환한다."""
        js = config.get("job_sources", {})
        wanted_cfg = js.get("wanted", {})
        jumpit_cfg = js.get("jumpit", {})
        return {
            "wanted": WantedCollector(
                api_url=wanted_cfg.get("api_url", "https://www.wanted.co.kr/api/v4/jobs"),
                job_group_id=wanted_cfg.get("job_group_id", 518),
                limit=wanted_cfg.get("limit", 100),
            ),
            "jumpit": JumpitCollector(
                api_url=jumpit_cfg.get("api_url", "https://api.jumpit.co.kr/api/positions"),
                job_category=jumpit_cfg.get("job_category", 1),
                limit=jumpit_cfg.get("limit", 100),
            ),
        }

    @staticmethod
    def build_community_collectors(config) -> Dict[str, BaseCollector]:
        """Reddit / Mastodon / Clien / DCInside Collector를 반환한다.

        새 커뮤니티 소스 추가:
          1. collectors/<new>.py 구현
          2. 여기에 키-값 한 줄 추가
          3. service.py의 _REDDIT_SOURCES / _MASTODON_SOURCES / _KOREAN_SOURCES 중 해당 집합에 키 추가
        """
        cs = config.get("community_sources", {})
        reddit_cfg = cs.get("reddit", {})
        mastodon_cfg = cs.get("mastodon", {})
        clien_cfg = cs.get("clien", {})
        dcinside_cfg = cs.get("dcinside", {})
        return {
            "reddit": RedditCollector(
                subreddits=reddit_cfg.get("subreddits", ["programming", "MachineLearning"]),
                limit=reddit_cfg.get("limit_per_subreddit", 10),
                min_score=reddit_cfg.get("min_score", 50),
                user_agent=reddit_cfg.get("user_agent", "Consigliere Career Bot 1.0"),
                timeout=reddit_cfg.get("timeout", 20),
            ),
            "mastodon": MastodonCollector(
                instances=mastodon_cfg.get(
                    "instances", ["fosstodon.org", "hachyderm.io", "mastodon.social"]
                ),
                hashtags=mastodon_cfg.get("hashtags", ["programming", "llm", "ai", "devops"]),
                limit_per_hashtag=mastodon_cfg.get("limit_per_hashtag", 10),
                timeout=mastodon_cfg.get("timeout", 15),
            ),
            "clien": ClienCollector(
                board_url=clien_cfg.get(
                    "board_url", "https://www.clien.net/service/board/cm_app"
                ),
                limit=clien_cfg.get("limit", 20),
            ),
            "dcinside": DCInsideCollector(
                gallery_id=dcinside_cfg.get("gallery_id", "programming"),
                list_url=dcinside_cfg.get(
                    "list_url", "https://gall.dcinside.com/board/lists/?id=programming"
                ),
                limit=dcinside_cfg.get("limit", 20),
            ),
        }
