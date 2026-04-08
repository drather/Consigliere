import asyncio
import json
import os
from collections import defaultdict
from datetime import date, timedelta
from typing import Dict, Any, List, Optional

from core.llm import LLMClient
from core.llm_pipeline import build_llm_pipeline
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
from modules.career.collectors.factory import CollectorFactory
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

# 카테고리 → 모델 매핑 (새 카테고리 추가 시에만 변경, 소스 추가 시 무수정)
_CATEGORY_MODEL = {
    "reddit": "RedditPost",
    "mastodon": "NitterTweet",
    "korean": "KoreanPost",
}


class CareerAgent:
    """
    Career 모듈 파사드. 모든 Job을 오케스트레이션한다.
    """

    def __init__(self):
        self.config = CareerConfig()
        root_storage = get_storage_provider("local", root_path=".")
        self.prompt_loader = PromptLoader(root_storage, base_dir="src/prompts")
        self.llm = build_llm_pipeline()
        self.data_dir = self.config.get_data_dir()
        self._persona_manager = PersonaManager()
        self.persona = self._persona_manager.get()

        # Collectors — 카테고리별 딕셔너리 (새 소스 추가: collectors/factory.py만 수정)
        self.trend_collectors = CollectorFactory.build_trend_collectors(self.config)
        self.job_collectors = CollectorFactory.build_job_collectors(self.config)
        self.community_collectors = CollectorFactory.build_community_collectors(self.config)

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
            self.job_collectors["wanted"].safe_collect(),
            self.job_collectors["jumpit"].safe_collect(),
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
            self.trend_collectors["github"].safe_collect(),
            self.trend_collectors["hn"].safe_collect(),
            self.trend_collectors["devto"].safe_collect(),
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

        names = list(self.community_collectors.keys())
        results = await asyncio.gather(*[
            c.safe_collect() for c in self.community_collectors.values()
        ])

        collection_status = {
            name: "ok" if posts else "failed"
            for name, posts in zip(names, results)
        }
        data = {
            name: [p.model_dump() for p in posts]
            for name, posts in zip(names, results)
        }
        data["collection_status"] = collection_status
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

        source_categories = self.config.get_community_source_categories()
        category_model_map = {
            "reddit": RedditPost,
            "mastodon": NitterTweet,
            "korean": KoreanPost,
        }
        grouped: Dict[str, list] = defaultdict(list)
        for source_key, posts_data in community_data.items():
            if source_key == "collection_status" or not isinstance(posts_data, list):
                continue
            cat = source_categories.get(source_key)
            model_cls = category_model_map.get(cat) if cat else None
            if model_cls:
                grouped[cat].extend(model_cls(**p) for p in posts_data)

        reddit_posts = grouped["reddit"]
        mastodon_posts = grouped["mastodon"]
        korean_posts = grouped["korean"]
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
            reddit_posts, mastodon_posts, korean_posts, collection_status
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
