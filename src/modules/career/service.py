import asyncio
import json
import os
from datetime import date, timedelta
from typing import Dict, Any, List, Optional

from core.llm import LLMClient
from core.prompt_loader import PromptLoader
from core.storage import get_storage_provider
from core.logger import get_logger

from modules.career.config import CareerConfig
from modules.career.persona_manager import PersonaManager
from modules.career.models import (
    CommunityTrendAnalysis,
    DevToArticle,
    HNStory,
    JobAnalysis,
    JobPosting,
    KoreanPost,
    NitterTweet,
    RedditPost,
    SkillGapAnalysis,
    SkillGapSnapshot,
    TrendAnalysis,
    TrendingRepo,
)
from modules.career.collectors.github_trending import GithubTrendingCollector
from modules.career.collectors.hacker_news import HackerNewsCollector
from modules.career.collectors.devto import DevToCollector
from modules.career.collectors.wanted import WantedCollector
from modules.career.collectors.jumpit import JumpitCollector
from modules.career.collectors.reddit import RedditCollector
from modules.career.collectors.nitter import NitterCollector
from modules.career.collectors.clien import ClienCollector
from modules.career.collectors.dcinside import DCInsideCollector
from modules.career.processors.job_analyzer import JobAnalyzer
from modules.career.processors.trend_analyzer import TrendAnalyzer
from modules.career.processors.skill_gap_analyzer import SkillGapAnalyzer
from modules.career.processors.community_analyzer import CommunityAnalyzer
from modules.career.reporters.daily_reporter import DailyReporter
from modules.career.reporters.weekly_reporter import WeeklyReporter
from modules.career.reporters.monthly_reporter import MonthlyReporter
from modules.career.history.tracker import HistoryTracker
from modules.career.presenter import CareerPresenter

logger = get_logger(__name__)


class CareerAgent:
    """
    Career 모듈 파사드. 모든 Job을 오케스트레이션한다.
    """

    def __init__(self):
        self.config = CareerConfig()
        root_storage = get_storage_provider("local", root_path=".")
        self.prompt_loader = PromptLoader(root_storage, base_dir="src/prompts")
        self.llm = LLMClient()
        self.data_dir = self.config.get_data_dir()
        self._persona_manager = PersonaManager()
        self.persona = self._persona_manager.get()

        # Collectors
        ts = self.config.get("trend_sources", {})
        js = self.config.get("job_sources", {})
        self.github_collector = GithubTrendingCollector(
            languages=self.config.get_github_languages(),
            trending_url_template=ts.get("github_trending_url", "https://github.com/trending/{language}?since=daily"),
        )
        self.hn_collector = HackerNewsCollector(
            top_stories_url=ts.get("hn_top_stories_url", "https://hacker-news.firebaseio.com/v0/topstories.json"),
            item_url_template=ts.get("hn_item_url", "https://hacker-news.firebaseio.com/v0/item/{id}.json"),
            min_score=self.config.get_hn_min_score(),
            stories_limit=self.config.get("concurrency", {}).get("hn_stories_limit", 30),
        )
        self.devto_collector = DevToCollector(
            api_url=ts.get("devto_api_url", "https://dev.to/api/articles"),
            tags=self.config.get_devto_tags(),
            per_page=ts.get("devto_per_page", 30),
        )
        wanted_cfg = js.get("wanted", {})
        self.wanted_collector = WantedCollector(
            api_url=wanted_cfg.get("api_url", "https://www.wanted.co.kr/api/v4/jobs"),
            job_group_id=wanted_cfg.get("job_group_id", 518),
            limit=wanted_cfg.get("limit", 100),
        )
        jumpit_cfg = js.get("jumpit", {})
        self.jumpit_collector = JumpitCollector(
            api_url=jumpit_cfg.get("api_url", "https://api.jumpit.co.kr/api/positions"),
            job_category=jumpit_cfg.get("job_category", 1),
            limit=jumpit_cfg.get("limit", 100),
        )

        # Community Collectors
        cs = self.config.get("community_sources", {})
        reddit_cfg = cs.get("reddit", {})
        self.reddit_collector = RedditCollector(
            subreddits=reddit_cfg.get("subreddits", ["programming", "MachineLearning"]),
            limit=reddit_cfg.get("limit_per_subreddit", 10),
            min_score=reddit_cfg.get("min_score", 50),
            client_id=os.getenv("REDDIT_CLIENT_ID", ""),
            client_secret=os.getenv("REDDIT_CLIENT_SECRET", ""),
            user_agent=reddit_cfg.get("user_agent", "Consigliere Career Bot 1.0"),
        )
        nitter_cfg = cs.get("nitter", {})
        self.nitter_collector = NitterCollector(
            instances=nitter_cfg.get("instances", ["https://nitter.net"]),
            keywords=nitter_cfg.get("keywords", ["AI LLM", "programming"]),
            timeout=nitter_cfg.get("timeout", 15),
            max_tweets_per_keyword=nitter_cfg.get("max_tweets_per_keyword", 10),
        )
        clien_cfg = cs.get("clien", {})
        self.clien_collector = ClienCollector(
            board_url=clien_cfg.get("board_url", "https://www.clien.net/service/board/cm_programmers"),
            limit=clien_cfg.get("limit", 20),
        )
        dcinside_cfg = cs.get("dcinside", {})
        self.dcinside_collector = DCInsideCollector(
            gallery_id=dcinside_cfg.get("gallery_id", "programming"),
            list_url=dcinside_cfg.get("list_url", "https://gall.dcinside.com/board/lists/?id=programming"),
            limit=dcinside_cfg.get("limit", 20),
        )

        # Processors
        self.job_analyzer = JobAnalyzer(self.llm, self.prompt_loader)
        self.trend_analyzer = TrendAnalyzer(self.llm, self.prompt_loader)
        self.skill_gap_analyzer = SkillGapAnalyzer(self.llm, self.prompt_loader)
        self.community_analyzer = CommunityAnalyzer(self.llm, self.prompt_loader)

        # Reporters
        self.daily_reporter = DailyReporter()
        self.weekly_reporter = WeeklyReporter(self.llm, self.prompt_loader)
        self.monthly_reporter = MonthlyReporter(self.llm, self.prompt_loader)

        # History
        self.tracker = HistoryTracker(self.data_dir)
        self.presenter = CareerPresenter()

    # ── Persona (PersonaManager에 위임) ──────────────────────────────────

    def get_persona(self) -> Dict[str, Any]:
        return self._persona_manager.get()

    def update_persona(self, updates: Dict[str, Any]) -> Dict[str, Any]:
        self.persona = self._persona_manager.update(updates)
        return self.persona

    # ── Job 1: fetch_jobs ─────────────────────────────────────────────

    async def fetch_jobs(self, target_date: Optional[date] = None) -> List[JobPosting]:
        if target_date is None:
            target_date = date.today()
        path = self._jobs_path(target_date)

        if os.path.exists(path):
            try:
                logger.info(f"채용공고 캐시 사용: {path}")
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                return [JobPosting(**d) for d in data]
            except (json.JSONDecodeError, OSError) as e:
                logger.warning(f"캐시 파일 손상, 재수집: {e}")

        wanted, jumpit = await asyncio.gather(
            self.wanted_collector.safe_collect(),
            self.jumpit_collector.safe_collect(),
        )
        postings = wanted + jumpit
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump([p.model_dump() for p in postings], f, ensure_ascii=False, indent=2)
        logger.info(f"채용공고 저장: {len(postings)}건 → {path}")
        return postings

    # ── Job 2: fetch_trends ───────────────────────────────────────────

    async def fetch_trends(self, target_date: Optional[date] = None) -> Dict[str, Any]:
        if target_date is None:
            target_date = date.today()
        path = self._trends_path(target_date)

        if os.path.exists(path):
            try:
                logger.info(f"트렌드 캐시 사용: {path}")
                with open(path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except (json.JSONDecodeError, OSError) as e:
                logger.warning(f"트렌드 캐시 손상, 재수집: {e}")

        repos, stories, articles = await asyncio.gather(
            self.github_collector.safe_collect(),
            self.hn_collector.safe_collect(),
            self.devto_collector.safe_collect(),
        )
        data = {
            "repos": [r.model_dump() for r in repos],
            "stories": [s.model_dump() for s in stories],
            "articles": [a.model_dump() for a in articles],
        }
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        logger.info(f"트렌드 저장 → {path}")
        return data

    # ── fetch_community ───────────────────────────────────────────────

    async def fetch_community(self, target_date: Optional[date] = None) -> Dict[str, Any]:
        if target_date is None:
            target_date = date.today()
        path = self._community_path(target_date)

        if os.path.exists(path):
            try:
                logger.info(f"커뮤니티 캐시 사용: {path}")
                with open(path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except (json.JSONDecodeError, OSError) as e:
                logger.warning(f"커뮤니티 캐시 손상, 재수집: {e}")

        reddit_posts, nitter_tweets, clien_posts, dcinside_posts = await asyncio.gather(
            self.reddit_collector.safe_collect(),
            self.nitter_collector.safe_collect(),
            self.clien_collector.safe_collect(),
            self.dcinside_collector.safe_collect(),
        )

        collection_status = {
            "reddit": "ok" if reddit_posts else "failed",
            "nitter": "ok" if nitter_tweets else "failed",
            "clien": "ok" if clien_posts else "failed",
            "dcinside": "ok" if dcinside_posts else "failed",
        }

        data = {
            "reddit": [p.model_dump() for p in reddit_posts],
            "nitter": [t.model_dump() for t in nitter_tweets],
            "clien": [p.model_dump() for p in clien_posts],
            "dcinside": [p.model_dump() for p in dcinside_posts],
            "collection_status": collection_status,
        }
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        logger.info(f"커뮤니티 저장 → {path} | status={collection_status}")
        return data

    # ── Job 3: generate_report ────────────────────────────────────────

    async def generate_report(self, target_date: Optional[date] = None) -> str:
        if target_date is None:
            target_date = date.today()
        report_path = self._daily_report_path(target_date)

        if os.path.exists(report_path):
            logger.info(f"일별 리포트 캐시 사용: {report_path}")
            with open(report_path, "r", encoding="utf-8") as f:
                return f.read()

        postings = await self.fetch_jobs(target_date)
        trend_data = await self.fetch_trends(target_date)
        community_data = await self.fetch_community(target_date)

        repos = [TrendingRepo(**r) for r in trend_data.get("repos", [])]
        stories = [HNStory(**s) for s in trend_data.get("stories", [])]
        articles = [DevToArticle(**a) for a in trend_data.get("articles", [])]

        reddit_posts = [RedditPost(**p) for p in community_data.get("reddit", [])]
        nitter_tweets = [NitterTweet(**t) for t in community_data.get("nitter", [])]
        korean_posts = [
            KoreanPost(**p)
            for p in community_data.get("clien", []) + community_data.get("dcinside", [])
        ]
        collection_status = community_data.get("collection_status", {})

        gap_history = self.tracker.load_recent(
            weeks=self.config.get("report", {}).get("skill_gap_history_weeks", 4)
        )

        job_analysis = self.job_analyzer.analyze(postings, self.persona)
        trend_analysis = self.trend_analyzer.analyze(
            repos, stories, articles, self.config.get_github_languages()
        )
        skill_gap = self.skill_gap_analyzer.analyze(
            job_analysis, trend_analysis, self.persona, gap_history
        )
        community_trend = self.community_analyzer.analyze(
            reddit_posts, nitter_tweets, korean_posts, collection_status
        )

        wanted_count = sum(1 for p in postings if p.source == "wanted")
        jumpit_count = sum(1 for p in postings if p.source == "jumpit")

        report_md = self.daily_reporter.generate(
            report_date=target_date,
            job_analysis=job_analysis,
            trend_analysis=trend_analysis,
            skill_gap=skill_gap,
            job_count_wanted=wanted_count,
            job_count_jumpit=jumpit_count,
            community_trend=community_trend,
        )

        snapshot = SkillGapSnapshot(
            date=str(target_date),
            gap_score=skill_gap.gap_score,
            missing_skills=[s.get("skill", "") for s in skill_gap.missing_skills],
            study_recommendations=skill_gap.study_recommendations,
        )
        self.tracker.save_snapshot(snapshot)

        os.makedirs(os.path.dirname(report_path), exist_ok=True)
        with open(report_path, "w", encoding="utf-8") as f:
            f.write(report_md)
        logger.info(f"일별 리포트 저장 → {report_path}")
        return report_md

    # ── run_pipeline ──────────────────────────────────────────────────

    async def run_pipeline(self, target_date: Optional[date] = None) -> Dict[str, Any]:
        if target_date is None:
            target_date = date.today()
        report_md = await self.generate_report(target_date)

        postings = await self.fetch_jobs(target_date)
        trend_data = await self.fetch_trends(target_date)

        repos = [TrendingRepo(**r) for r in trend_data.get("repos", [])]
        stories = [HNStory(**s) for s in trend_data.get("stories", [])]
        articles = [DevToArticle(**a) for a in trend_data.get("articles", [])]
        gap_history = self.tracker.load_recent()

        job_analysis = self.job_analyzer.analyze(postings, self.persona)
        trend_analysis = self.trend_analyzer.analyze(
            repos, stories, articles, self.config.get_github_languages()
        )
        skill_gap = self.skill_gap_analyzer.analyze(
            job_analysis, trend_analysis, self.persona, gap_history
        )

        wanted_count = sum(1 for p in postings if p.source == "wanted")
        jumpit_count = sum(1 for p in postings if p.source == "jumpit")

        slack_blocks = self.presenter.build_daily_report(
            report_date=target_date,
            job_analysis=job_analysis,
            trend_analysis=trend_analysis,
            skill_gap=skill_gap,
            job_count_wanted=wanted_count,
            job_count_jumpit=jumpit_count,
        )
        return {"report_md": report_md, "slack_blocks": slack_blocks}

    # ── Job 4: generate_weekly_report ─────────────────────────────────

    async def generate_weekly_report(self, iso_week: Optional[str] = None) -> str:
        """iso_week: '2026-W13' 형식. None이면 이번 주."""
        today = date.today()
        if iso_week is None:
            year, week, _ = today.isocalendar()
            iso_week = f"{year}-W{week:02d}"

        report_path = self._weekly_report_path(iso_week)
        if os.path.exists(report_path):
            with open(report_path, "r", encoding="utf-8") as f:
                return f.read()

        year, week_num = int(iso_week.split("-W")[0]), int(iso_week.split("-W")[1])
        start = date.fromisocalendar(year, week_num, 1)
        end = date.fromisocalendar(year, week_num, 7)

        daily_reports = []
        for i in range(7):
            d = start + timedelta(days=i)
            p = self._daily_report_path(d)
            if os.path.exists(p):
                with open(p, "r", encoding="utf-8") as f:
                    daily_reports.append(f.read())

        if not daily_reports:
            return f"# 커리어 Weekly Report — {iso_week}\n\n일별 리포트 없음."

        report_md = self.weekly_reporter.generate(
            week_label=iso_week,
            start_date=str(start),
            end_date=str(end),
            daily_reports=daily_reports,
        )

        os.makedirs(os.path.dirname(report_path), exist_ok=True)
        with open(report_path, "w", encoding="utf-8") as f:
            f.write(report_md)
        return report_md

    # ── Job 5: generate_monthly_report ────────────────────────────────

    async def generate_monthly_report(self, year_month: Optional[str] = None) -> str:
        """year_month: '2026-03' 형식. None이면 이번 달."""
        today = date.today()
        if year_month is None:
            year_month = today.strftime("%Y-%m")

        report_path = self._monthly_report_path(year_month)
        if os.path.exists(report_path):
            with open(report_path, "r", encoding="utf-8") as f:
                return f.read()

        year, month = int(year_month.split("-")[0]), int(year_month.split("-")[1])
        weekly_dir = os.path.join(self.data_dir, "reports", "weekly")
        weekly_reports = []
        if os.path.exists(weekly_dir):
            for fname in sorted(os.listdir(weekly_dir)):
                if fname.endswith("_WeeklyReport.md") and fname.startswith(str(year)):
                    week_str = fname.replace("_WeeklyReport.md", "")
                    try:
                        w_year, w_week = week_str.split("-W")
                        start = date.fromisocalendar(int(w_year), int(w_week), 1)
                        if start.year == year and start.month == month:
                            with open(os.path.join(weekly_dir, fname), "r", encoding="utf-8") as f:
                                weekly_reports.append(f.read())
                    except Exception:
                        continue

        if not weekly_reports:
            return f"# 커리어 Monthly Report — {year_month}\n\n주간 리포트 없음."

        report_md = self.monthly_reporter.generate(
            month_label=year_month,
            year=year,
            month=month,
            weekly_reports=weekly_reports,
        )

        os.makedirs(os.path.dirname(report_path), exist_ok=True)
        with open(report_path, "w", encoding="utf-8") as f:
            f.write(report_md)
        return report_md

    # ── 대시보드용 조회 ───────────────────────────────────────────────

    def list_daily_reports(self) -> List[str]:
        d = os.path.join(self.data_dir, "reports", "daily")
        if not os.path.exists(d):
            return []
        return sorted(
            f.replace("_CareerReport.md", "")
            for f in os.listdir(d) if f.endswith("_CareerReport.md")
        )

    def get_daily_report(self, report_date: str) -> Optional[str]:
        path = os.path.join(self.data_dir, "reports", "daily", f"{report_date}_CareerReport.md")
        if not os.path.exists(path):
            return None
        with open(path, "r", encoding="utf-8") as f:
            return f.read()

    def list_weekly_reports(self) -> List[str]:
        d = os.path.join(self.data_dir, "reports", "weekly")
        if not os.path.exists(d):
            return []
        return sorted(
            f.replace("_WeeklyReport.md", "")
            for f in os.listdir(d) if f.endswith("_WeeklyReport.md")
        )

    def list_monthly_reports(self) -> List[str]:
        d = os.path.join(self.data_dir, "reports", "monthly")
        if not os.path.exists(d):
            return []
        return sorted(
            f.replace("_MonthlyReport.md", "")
            for f in os.listdir(d) if f.endswith("_MonthlyReport.md")
        )

    def get_skill_gap_history(self, weeks: int = 4) -> List[Dict[str, Any]]:
        return [s.model_dump() for s in self.tracker.load_recent(weeks=weeks)]

    # ── 경로 헬퍼 ────────────────────────────────────────────────────

    def _jobs_path(self, d: date) -> str:
        return os.path.join(self.data_dir, "jobs", f"{d}_jobs.json")

    def _trends_path(self, d: date) -> str:
        return os.path.join(self.data_dir, "trends", f"{d}_trends.json")

    def _community_path(self, d: date) -> str:
        return os.path.join(self.data_dir, "community", f"{d}_community.json")

    def _daily_report_path(self, d: date) -> str:
        return os.path.join(self.data_dir, "reports", "daily", f"{d}_CareerReport.md")

    def _weekly_report_path(self, iso_week: str) -> str:
        return os.path.join(self.data_dir, "reports", "weekly", f"{iso_week}_WeeklyReport.md")

    def _monthly_report_path(self, ym: str) -> str:
        return os.path.join(self.data_dir, "reports", "monthly", f"{ym}_MonthlyReport.md")
