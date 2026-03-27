"""
Tests for Career Daily Report Module
브랜치: feature/career-daily-report
"""
import os
import sys
import json
import pytest
import asyncio
from datetime import date
from unittest.mock import MagicMock, AsyncMock, patch

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))

from modules.career.models import (
    JobPosting, TrendingRepo, HNStory, DevToArticle,
    JobAnalysis, TrendAnalysis, SkillGapAnalysis, SkillGapSnapshot,
)
from modules.career.reporters.daily_reporter import DailyReporter
from modules.career.presenter import CareerPresenter
from modules.career.history.tracker import HistoryTracker
from modules.career.config import CareerConfig


# ─────────────────────────────────────────────────────────────────────────────
# Fixtures
# ─────────────────────────────────────────────────────────────────────────────

@pytest.fixture
def sample_job_postings():
    return [
        JobPosting(id="1", company="A사", position="백엔드 개발자", skills=["Python", "FastAPI", "Kubernetes"],
                   salary_min=60000000, salary_max=90000000, experience_min=3, url="https://example.com/1", source="wanted"),
        JobPosting(id="2", company="B사", position="서버 개발자", skills=["Go", "Kubernetes", "PostgreSQL"],
                   salary_min=70000000, salary_max=100000000, experience_min=5, url="https://example.com/2", source="jumpit"),
        JobPosting(id="3", company="C사", position="백엔드 엔지니어", skills=["Python", "Docker", "Redis"],
                   salary_min=None, salary_max=None, experience_min=2, url="https://example.com/3", source="wanted"),
    ]


@pytest.fixture
def sample_job_analysis():
    return JobAnalysis(
        top_skills=["Python", "Kubernetes", "Go", "FastAPI", "Docker"],
        skill_frequency={"Python": 42, "Kubernetes": 28, "Go": 15, "FastAPI": 20, "Docker": 18},
        salary_range={"median": 70000000, "p75": 85000000, "p90": 100000000},
        hiring_signal="백엔드 시장 채용 수요 꾸준히 증가, Kubernetes 경험 필수화 추세",
        notable_postings=[
            {"company": "A사", "position": "백엔드 개발자", "url": "https://example.com/1", "reason": "연봉 상위권"},
        ],
    )


@pytest.fixture
def sample_trend_analysis():
    return TrendAnalysis(
        hot_topics=["Rust + WASM", "LLM 인프라", "eBPF", "Kubernetes", "OpenTelemetry"],
        github_top=[
            {"name": "owner/awesome-repo", "description": "desc", "language": "Go", "stars_today": 300, "url": "https://github.com/owner/awesome-repo"},
        ],
        hn_highlight="Why eBPF is taking over observability — score 512",
        devto_picks=[
            {"title": "Kubernetes Best Practices", "url": "https://dev.to/1", "tags": ["kubernetes"], "reactions": 200},
        ],
        backend_relevance_comment="eBPF 기반 옵저버빌리티 도구가 급부상 중, 백엔드 인프라 엔지니어에게 필수 지식이 될 전망",
    )


@pytest.fixture
def sample_skill_gap():
    return SkillGapAnalysis(
        gap_score=72,
        missing_skills=[
            {"skill": "Kubernetes", "urgency": "high", "frequency_in_jd": 28},
            {"skill": "Go", "urgency": "medium", "frequency_in_jd": 15},
        ],
        study_recommendations=[
            {"topic": "Kubernetes CKA 준비", "why": "채용공고 28건 요구, 현재 학습 포커스", "resource": "Kodekloud CKA 강의"},
            {"topic": "Go 언어 기초", "why": "채용공고 15건 요구, 목표 스킬", "resource": "Tour of Go"},
        ],
        gap_trend="지난주 대비 +2점 상승 (Kubernetes 요구 증가)",
    )


# ─────────────────────────────────────────────────────────────────────────────
# Models
# ─────────────────────────────────────────────────────────────────────────────

class TestModels:
    def test_job_posting_required_fields(self):
        p = JobPosting(id="1", company="테스트", position="개발자", url="https://x.com", source="wanted")
        assert p.id == "1"
        assert p.skills == []
        assert p.salary_min is None

    def test_skill_gap_score_bounds(self):
        with pytest.raises(Exception):
            SkillGapAnalysis(gap_score=101)
        with pytest.raises(Exception):
            SkillGapAnalysis(gap_score=-1)

    def test_skill_gap_snapshot_serialization(self):
        snap = SkillGapSnapshot(
            date="2026-03-27",
            gap_score=72,
            missing_skills=["Kubernetes", "Go"],
            study_recommendations=[],
        )
        d = snap.model_dump()
        assert d["date"] == "2026-03-27"
        assert d["gap_score"] == 72
        assert "Kubernetes" in d["missing_skills"]

    def test_job_analysis_defaults(self):
        a = JobAnalysis()
        assert a.top_skills == []
        assert a.skill_frequency == {}
        assert a.hiring_signal == ""


# ─────────────────────────────────────────────────────────────────────────────
# DailyReporter
# ─────────────────────────────────────────────────────────────────────────────

class TestDailyReporter:
    def setup_method(self):
        self.reporter = DailyReporter()

    def test_report_contains_date(self, sample_job_analysis, sample_trend_analysis, sample_skill_gap):
        report = self.reporter.generate(
            report_date=date(2026, 3, 27),
            job_analysis=sample_job_analysis,
            trend_analysis=sample_trend_analysis,
            skill_gap=sample_skill_gap,
            job_count_wanted=50,
            job_count_jumpit=40,
        )
        assert "2026-03-27" in report

    def test_report_contains_job_counts(self, sample_job_analysis, sample_trend_analysis, sample_skill_gap):
        report = self.reporter.generate(
            report_date=date(2026, 3, 27),
            job_analysis=sample_job_analysis,
            trend_analysis=sample_trend_analysis,
            skill_gap=sample_skill_gap,
            job_count_wanted=50,
            job_count_jumpit=40,
        )
        assert "Wanted 50건" in report
        assert "점핏 40건" in report

    def test_report_contains_top_skills(self, sample_job_analysis, sample_trend_analysis, sample_skill_gap):
        report = self.reporter.generate(
            report_date=date(2026, 3, 27),
            job_analysis=sample_job_analysis,
            trend_analysis=sample_trend_analysis,
            skill_gap=sample_skill_gap,
            job_count_wanted=10,
            job_count_jumpit=10,
        )
        assert "Python" in report
        assert "Kubernetes" in report

    def test_report_contains_gap_score(self, sample_job_analysis, sample_trend_analysis, sample_skill_gap):
        report = self.reporter.generate(
            report_date=date(2026, 3, 27),
            job_analysis=sample_job_analysis,
            trend_analysis=sample_trend_analysis,
            skill_gap=sample_skill_gap,
            job_count_wanted=10,
            job_count_jumpit=10,
        )
        assert "72/100" in report

    def test_report_contains_all_sections(self, sample_job_analysis, sample_trend_analysis, sample_skill_gap):
        report = self.reporter.generate(
            report_date=date(2026, 3, 27),
            job_analysis=sample_job_analysis,
            trend_analysis=sample_trend_analysis,
            skill_gap=sample_skill_gap,
            job_count_wanted=10,
            job_count_jumpit=10,
        )
        assert "## 💼 채용공고 요약" in report
        assert "## 🔥 기술 트렌드" in report
        assert "## 🎯 스킬 갭 & 학습 추천" in report

    def test_report_empty_data_no_crash(self):
        """분석 결과가 비어있어도 크래시 없이 리포트 생성"""
        report = self.reporter.generate(
            report_date=date(2026, 3, 27),
            job_analysis=JobAnalysis(),
            trend_analysis=TrendAnalysis(),
            skill_gap=SkillGapAnalysis(),
            job_count_wanted=0,
            job_count_jumpit=0,
        )
        assert "2026-03-27" in report


# ─────────────────────────────────────────────────────────────────────────────
# CareerPresenter
# ─────────────────────────────────────────────────────────────────────────────

class TestCareerPresenter:
    def test_build_daily_report_returns_blocks(self, sample_job_analysis, sample_trend_analysis, sample_skill_gap):
        result = CareerPresenter.build_daily_report(
            report_date=date(2026, 3, 27),
            job_analysis=sample_job_analysis,
            trend_analysis=sample_trend_analysis,
            skill_gap=sample_skill_gap,
            job_count_wanted=50,
            job_count_jumpit=40,
        )
        assert "blocks" in result
        assert len(result["blocks"]) > 0

    def test_blocks_contain_header(self, sample_job_analysis, sample_trend_analysis, sample_skill_gap):
        result = CareerPresenter.build_daily_report(
            report_date=date(2026, 3, 27),
            job_analysis=sample_job_analysis,
            trend_analysis=sample_trend_analysis,
            skill_gap=sample_skill_gap,
            job_count_wanted=10,
            job_count_jumpit=10,
        )
        header = result["blocks"][0]
        assert header["type"] == "header"
        assert "2026-03-27" in header["text"]["text"]

    def test_score_bar_length(self):
        """갭 점수 100점 → 바 길이 10"""
        from modules.career.presenter import _score_bar
        assert len(_score_bar(100)) == 10
        assert len(_score_bar(0)) == 10
        assert len(_score_bar(50)) == 10

    def test_score_bar_content(self):
        from modules.career.presenter import _score_bar
        bar = _score_bar(100)
        assert "🟥" in bar
        assert "⬜" not in bar

        bar0 = _score_bar(0)
        assert "⬜" in bar0
        assert "🟥" not in bar0


# ─────────────────────────────────────────────────────────────────────────────
# HistoryTracker
# ─────────────────────────────────────────────────────────────────────────────

class TestHistoryTracker:
    def test_save_and_load(self, tmp_path):
        tracker = HistoryTracker(data_dir=str(tmp_path))
        snap = SkillGapSnapshot(
            date="2026-03-27",
            gap_score=72,
            missing_skills=["Kubernetes", "Go"],
            study_recommendations=[],
        )
        tracker.save_snapshot(snap)
        loaded = tracker.load_recent(weeks=4)
        assert len(loaded) == 1
        assert loaded[0].gap_score == 72
        assert "Kubernetes" in loaded[0].missing_skills

    def test_load_empty_dir_returns_empty(self, tmp_path):
        tracker = HistoryTracker(data_dir=str(tmp_path))
        result = tracker.load_recent(weeks=4)
        assert result == []

    def test_old_snapshot_filtered_out(self, tmp_path):
        tracker = HistoryTracker(data_dir=str(tmp_path))
        # 8주 전 스냅샷 — 4주 필터에 걸려야 함
        snap = SkillGapSnapshot(
            date="2026-01-01",
            gap_score=50,
            missing_skills=[],
            study_recommendations=[],
        )
        tracker.save_snapshot(snap)
        loaded = tracker.load_recent(weeks=4)
        assert loaded == []

    def test_multiple_snapshots_sorted(self, tmp_path):
        tracker = HistoryTracker(data_dir=str(tmp_path))
        for d, score in [("2026-03-25", 70), ("2026-03-26", 71), ("2026-03-27", 72)]:
            tracker.save_snapshot(SkillGapSnapshot(date=d, gap_score=score, missing_skills=[], study_recommendations=[]))
        loaded = tracker.load_recent(weeks=4)
        assert len(loaded) == 3
        assert loaded[0].gap_score == 70  # 날짜 오름차순


# ─────────────────────────────────────────────────────────────────────────────
# CareerConfig
# ─────────────────────────────────────────────────────────────────────────────

class TestCareerConfig:
    def test_default_values(self):
        config = CareerConfig(config_path="nonexistent.yaml")
        assert isinstance(config.get_github_languages(), list)
        assert isinstance(config.get_hn_min_score(), int)
        assert isinstance(config.get_devto_tags(), list)

    def test_load_from_file(self):
        config = CareerConfig(config_path="src/modules/career/config.yaml")
        assert "python" in config.get_github_languages()
        assert config.get_hn_min_score() == 50
        assert "backend" in config.get_devto_tags()


# ─────────────────────────────────────────────────────────────────────────────
# Collectors (단위 테스트 — 네트워크 없이 파싱 로직만 검증)
# ─────────────────────────────────────────────────────────────────────────────

class TestGithubTrendingParser:
    def test_parse_valid_html(self):
        from modules.career.collectors.github_trending import GithubTrendingCollector
        collector = GithubTrendingCollector(languages=["python"], trending_url_template="")
        html = """
        <article class="Box-row">
          <h2><a href="/owner/repo-name">owner/repo-name</a></h2>
          <p>A great Python library</p>
          <span itemprop="programmingLanguage">Python</span>
          <span class="d-inline-block float-sm-right">123 stars today</span>
        </article>
        """
        repos = collector._parse(html, "python")
        assert len(repos) == 1
        assert repos[0].name == "owner/repo-name"
        assert repos[0].stars_today == 123
        assert repos[0].language == "Python"

    def test_parse_empty_html_returns_empty(self):
        from modules.career.collectors.github_trending import GithubTrendingCollector
        collector = GithubTrendingCollector(languages=["python"], trending_url_template="")
        repos = collector._parse("<html></html>", "python")
        assert repos == []


class TestWantedParser:
    def test_parse_valid_data(self):
        from modules.career.collectors.wanted import WantedCollector
        collector = WantedCollector(api_url="", job_group_id=518, limit=10)
        data = {
            "data": [
                {
                    "job": {
                        "id": 999,
                        "position": "백엔드 개발자",
                        "company": {"name": "테스트사"},
                        "tags": [{"title": "Python"}, {"title": "FastAPI"}],
                        "salary": {"min": 60000000, "max": 90000000},
                        "experience_min": 3,
                    }
                }
            ]
        }
        postings = collector._parse(data)
        assert len(postings) == 1
        assert postings[0].company == "테스트사"
        assert "Python" in postings[0].skills
        assert postings[0].source == "wanted"

    def test_parse_empty_data_returns_empty(self):
        from modules.career.collectors.wanted import WantedCollector
        collector = WantedCollector(api_url="", job_group_id=518, limit=10)
        assert collector._parse({"data": []}) == []


class TestJumpitParser:
    def test_parse_valid_items(self):
        from modules.career.collectors.jumpit import JumpitCollector
        collector = JumpitCollector(api_url="", job_category=1, limit=10)
        items = [
            {
                "id": 777,
                "title": "서버 개발자",
                "companyName": "점핏사",
                "techStacks": ["Go", "Kubernetes"],
                "minCareer": 2,
            }
        ]
        postings = collector._parse(items)
        assert len(postings) == 1
        assert postings[0].position == "서버 개발자"
        assert "Go" in postings[0].skills
        assert postings[0].source == "jumpit"


# ─────────────────────────────────────────────────────────────────────────────
# CareerAgent (서비스 레이어 — LLM/네트워크 Mock)
# ─────────────────────────────────────────────────────────────────────────────

def _make_mock_agent(tmp_path):
    """LLM, Collector, Storage 전부 mock한 CareerAgent 인스턴스를 반환한다."""
    import types
    from modules.career import service as _svc

    # CareerAgent.__init__ 없이 인스턴스 생성
    agent = object.__new__(_svc.CareerAgent)
    agent.config = CareerConfig(config_path="src/modules/career/config.yaml")
    agent.data_dir = str(tmp_path / "career")
    agent.persona = {
        "user": {"experience_years": 3},
        "skills": {"current": ["Python"], "learning": ["Kubernetes"], "target": ["Go"]},
        "learning": {"current_focus": "Kubernetes CKA"},
    }

    # Collectors mock
    agent.wanted_collector = MagicMock()
    agent.wanted_collector.safe_collect = AsyncMock(return_value=[
        JobPosting(id="1", company="A사", position="백엔드", skills=["Python"], url="https://x.com", source="wanted"),
    ])
    agent.jumpit_collector = MagicMock()
    agent.jumpit_collector.safe_collect = AsyncMock(return_value=[])
    agent.github_collector = MagicMock()
    agent.github_collector.safe_collect = AsyncMock(return_value=[])
    agent.hn_collector = MagicMock()
    agent.hn_collector.safe_collect = AsyncMock(return_value=[])
    agent.devto_collector = MagicMock()
    agent.devto_collector.safe_collect = AsyncMock(return_value=[])

    # Processors mock
    agent.job_analyzer = MagicMock()
    agent.job_analyzer.analyze = MagicMock(return_value=JobAnalysis(
        top_skills=["Python"], skill_frequency={"Python": 10},
        salary_range={"median": 70000000, "p75": 85000000, "p90": None},
        hiring_signal="테스트 시그널",
    ))
    agent.trend_analyzer = MagicMock()
    agent.trend_analyzer.analyze = MagicMock(return_value=TrendAnalysis(
        hot_topics=["Kubernetes"], hn_highlight="테스트 HN",
    ))
    agent.skill_gap_analyzer = MagicMock()
    agent.skill_gap_analyzer.analyze = MagicMock(return_value=SkillGapAnalysis(
        gap_score=65, missing_skills=[{"skill": "Kubernetes", "urgency": "high", "frequency_in_jd": 10}],
    ))

    agent.daily_reporter = DailyReporter()
    agent.tracker = HistoryTracker(data_dir=str(tmp_path / "career"))
    agent.presenter = CareerPresenter()

    # service.py의 메서드들을 바인딩
    for method_name in ("fetch_jobs", "fetch_trends", "generate_report", "run_pipeline",
                        "_jobs_path", "_trends_path", "_daily_report_path"):
        fn = getattr(_svc.CareerAgent, method_name, None)
        if fn:
            setattr(agent, method_name, types.MethodType(fn, agent))

    return agent


class TestCareerAgentPipeline:
    @pytest.fixture
    def mock_agent(self, tmp_path):
        return _make_mock_agent(tmp_path)

    def test_fetch_jobs_saves_file(self, mock_agent):
        postings = asyncio.run(mock_agent.fetch_jobs(date(2026, 3, 27)))
        assert len(postings) == 1
        assert os.path.exists(mock_agent._jobs_path(date(2026, 3, 27)))

    def test_fetch_jobs_uses_cache(self, mock_agent):
        asyncio.run(mock_agent.fetch_jobs(date(2026, 3, 27)))
        # 두 번째 호출은 캐시 사용 → collector 호출 횟수 여전히 1
        asyncio.run(mock_agent.fetch_jobs(date(2026, 3, 27)))
        assert mock_agent.wanted_collector.safe_collect.call_count == 1

    def test_fetch_trends_saves_file(self, mock_agent):
        asyncio.run(mock_agent.fetch_trends(date(2026, 3, 27)))
        assert os.path.exists(mock_agent._trends_path(date(2026, 3, 27)))

    def test_generate_report_creates_md_file(self, mock_agent):
        asyncio.run(mock_agent.generate_report(date(2026, 3, 27)))
        path = mock_agent._daily_report_path(date(2026, 3, 27))
        assert os.path.exists(path)
        with open(path) as f:
            content = f.read()
        assert "2026-03-27" in content

    def test_generate_report_saves_gap_snapshot(self, mock_agent):
        asyncio.run(mock_agent.generate_report(date(2026, 3, 27)))
        history = mock_agent.tracker.load_recent(weeks=4)
        assert len(history) == 1
        assert history[0].gap_score == 65

    def test_run_pipeline_returns_report_and_blocks(self, mock_agent):
        result = asyncio.run(mock_agent.run_pipeline(date(2026, 3, 27)))
        assert "report_md" in result
        assert "slack_blocks" in result
        assert "blocks" in result["slack_blocks"]


# ─────────────────────────────────────────────────────────────────────────────
# SOLID Review: 에러 처리 (Red → 현재 실패, 리팩토링 후 Green)
# ─────────────────────────────────────────────────────────────────────────────

class TestProcessorErrorHandling:
    """Processor LLM 호출 실패 시 기본값 반환 (파이프라인 중단 방지)"""

    def test_job_analyzer_llm_failure_returns_default(self):
        from modules.career.processors.job_analyzer import JobAnalyzer
        llm = MagicMock()
        llm.generate_json.side_effect = Exception("LLM timeout")
        prompt_loader = MagicMock()
        prompt_loader.load.return_value = ({}, "prompt")

        analyzer = JobAnalyzer(llm=llm, prompt_loader=prompt_loader)
        result = analyzer.analyze(postings=[], persona={})
        assert isinstance(result, JobAnalysis)
        assert result.top_skills == []

    def test_trend_analyzer_llm_failure_returns_default(self):
        from modules.career.processors.trend_analyzer import TrendAnalyzer
        llm = MagicMock()
        llm.generate_json.side_effect = Exception("LLM timeout")
        prompt_loader = MagicMock()
        prompt_loader.load.return_value = ({}, "prompt")

        analyzer = TrendAnalyzer(llm=llm, prompt_loader=prompt_loader)
        result = analyzer.analyze(repos=[], stories=[], articles=[], github_languages=[])
        assert isinstance(result, TrendAnalysis)
        assert result.hot_topics == []

    def test_skill_gap_analyzer_llm_failure_returns_default(self):
        from modules.career.processors.skill_gap_analyzer import SkillGapAnalyzer
        llm = MagicMock()
        llm.generate_json.side_effect = Exception("LLM timeout")
        prompt_loader = MagicMock()
        prompt_loader.load.return_value = ({}, "prompt")

        analyzer = SkillGapAnalyzer(llm=llm, prompt_loader=prompt_loader)
        result = analyzer.analyze(
            job_analysis=JobAnalysis(),
            trend_analysis=TrendAnalysis(),
            persona={},
            gap_history=[],
        )
        assert isinstance(result, SkillGapAnalysis)
        assert result.gap_score == 0


class TestCollectorErrorHandling:
    """Collector 예외 발생 시 빈 리스트 반환"""

    def test_hn_fetch_ids_failure_returns_empty(self):
        """HN top stories API 실패 시 전체 수집이 빈 리스트로 graceful 처리"""
        from modules.career.collectors.hacker_news import HackerNewsCollector
        collector = HackerNewsCollector(
            top_stories_url="https://invalid.url",
            item_url_template="https://invalid.url/{id}",
            min_score=50,
            stories_limit=5,
        )
        result = asyncio.run(collector.safe_collect())
        assert result == []

    def test_wanted_json_parse_failure_returns_empty(self):
        """Wanted API가 잘못된 JSON 반환 시 빈 리스트 반환"""
        from modules.career.collectors.wanted import WantedCollector
        collector = WantedCollector(api_url="", job_group_id=518, limit=10)
        result = collector._parse({"data": [{"job": None}]})
        assert result == []


class TestReporterErrorHandling:
    """Reporter LLM 실패 시 에러 메시지 포함 문자열 반환 (크래시 방지)"""

    def test_weekly_reporter_llm_failure_returns_fallback(self):
        from modules.career.reporters.weekly_reporter import WeeklyReporter
        llm = MagicMock()
        llm.generate.side_effect = Exception("LLM error")
        prompt_loader = MagicMock()
        prompt_loader.load.return_value = ({}, "prompt")

        reporter = WeeklyReporter(llm=llm, prompt_loader=prompt_loader)
        result = reporter.generate(
            week_label="2026-W13",
            start_date="2026-03-23",
            end_date="2026-03-29",
            daily_reports=["# Day 1"],
        )
        assert isinstance(result, str)
        assert "2026-W13" in result

    def test_monthly_reporter_llm_failure_returns_fallback(self):
        from modules.career.reporters.monthly_reporter import MonthlyReporter
        llm = MagicMock()
        llm.generate.side_effect = Exception("LLM error")
        prompt_loader = MagicMock()
        prompt_loader.load.return_value = ({}, "prompt")

        reporter = MonthlyReporter(llm=llm, prompt_loader=prompt_loader)
        result = reporter.generate(
            month_label="2026-03",
            year=2026,
            month=3,
            weekly_reports=["# Week 1"],
        )
        assert isinstance(result, str)
        assert "2026-03" in result


class TestConfigErrorHandling:
    """Config YAML 파싱 실패 시 기본값 반환"""

    def test_corrupted_yaml_returns_empty(self, tmp_path):
        bad_yaml = tmp_path / "config.yaml"
        bad_yaml.write_text("key: [unclosed bracket", encoding="utf-8")
        config = CareerConfig(config_path=str(bad_yaml))
        assert config.get("key") is None
        assert isinstance(config.get_github_languages(), list)


class TestTrackerErrorHandling:
    """Tracker 파일 손상 시 해당 스냅샷만 건너뜀"""

    def test_corrupted_snapshot_file_is_skipped(self, tmp_path):
        tracker = HistoryTracker(data_dir=str(tmp_path))
        gap_dir = tmp_path / "history" / "skill_gap"
        gap_dir.mkdir(parents=True)
        # 정상 스냅샷
        (gap_dir / "2026-03-27_skill_gap.json").write_text(
            '{"date":"2026-03-27","gap_score":70,"missing_skills":[],"study_recommendations":[]}',
            encoding="utf-8",
        )
        # 손상된 파일
        (gap_dir / "2026-03-26_skill_gap.json").write_text("INVALID JSON", encoding="utf-8")

        result = tracker.load_recent(weeks=4)
        assert len(result) == 1
        assert result[0].gap_score == 70


class TestPersonaManager:
    """SRP: PersonaManager가 persona YAML I/O를 단독으로 담당"""

    def test_load_persona(self):
        from modules.career.persona_manager import PersonaManager
        pm = PersonaManager(persona_path="src/modules/career/persona.yaml")
        persona = pm.get()
        assert "user" in persona
        assert "skills" in persona

    def test_update_persona(self, tmp_path):
        from modules.career.persona_manager import PersonaManager
        import yaml, shutil
        src = "src/modules/career/persona.yaml"
        dst = tmp_path / "persona.yaml"
        shutil.copy(src, dst)

        pm = PersonaManager(persona_path=str(dst))
        pm.update({"user": {"name": "test_user", "experience_years": 5,
                             "domain": "백엔드", "career_goal": "아키텍트",
                             "current_company_type": "스타트업",
                             "target_company_types": []}})
        pm2 = PersonaManager(persona_path=str(dst))
        assert pm2.get()["user"]["name"] == "test_user"
        assert pm2.get()["user"]["experience_years"] == 5
