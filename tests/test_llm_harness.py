"""
LLM Harness Engineering — 테스트 모음

테스트 구성:
  1. Token Observability (TokenUsage, get_last_usage)
  2. Career Context Compression
  3. Model Routing per Agent
  4. Prompt Caching (cache_control)
  5. Semantic/Response Cache
"""
import hashlib
import json
import os
import sys
import time
from dataclasses import dataclass
from types import SimpleNamespace
from typing import Dict, Any
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))

# ─────────────────────────────────────────────────────────────────────────────
# 1. TOKEN OBSERVABILITY
# ─────────────────────────────────────────────────────────────────────────────

class TestTokenUsage:
    def test_token_usage_addition(self):
        from core.llm import TokenUsage
        a = TokenUsage(input_tokens=10, output_tokens=5)
        b = TokenUsage(input_tokens=20, output_tokens=8)
        c = a + b
        assert c.input_tokens == 30
        assert c.output_tokens == 13
        assert c.cached_input_tokens == 0

    def test_token_usage_total(self):
        from core.llm import TokenUsage
        u = TokenUsage(input_tokens=100, output_tokens=50)
        assert u.total_tokens == 150

    def test_token_usage_cached_addition(self):
        from core.llm import TokenUsage
        a = TokenUsage(input_tokens=10, output_tokens=5, cached_input_tokens=200)
        b = TokenUsage(input_tokens=20, output_tokens=8, cached_input_tokens=300)
        c = a + b
        assert c.cached_input_tokens == 500

    def test_token_usage_defaults_to_zero(self):
        from core.llm import TokenUsage
        u = TokenUsage()
        assert u.input_tokens == 0
        assert u.output_tokens == 0
        assert u.cached_input_tokens == 0
        assert u.total_tokens == 0


class TestClaudeTokenObservability:
    def test_claude_generate_records_usage(self):
        from core.llm import ClaudeClient, TokenUsage

        fake_usage = SimpleNamespace(input_tokens=100, output_tokens=50)
        fake_message = SimpleNamespace(
            content=[SimpleNamespace(text="hello")],
            usage=fake_usage,
        )
        with patch("anthropic.Anthropic") as mock_anthropic_cls:
            mock_client = MagicMock()
            mock_anthropic_cls.return_value = mock_client
            mock_client.messages.create.return_value = fake_message

            client = ClaudeClient(api_key="test-key")
            result = client.generate("some prompt")

        assert result == "hello"
        usage = client.get_last_usage()
        assert usage.input_tokens == 100
        assert usage.output_tokens == 50

    def test_claude_generate_json_records_usage(self):
        from core.llm import ClaudeClient

        fake_usage = SimpleNamespace(input_tokens=200, output_tokens=80)
        fake_message = SimpleNamespace(
            content=[SimpleNamespace(text='{"key": "value"}')],
            usage=fake_usage,
        )
        with patch("anthropic.Anthropic") as mock_anthropic_cls:
            mock_client = MagicMock()
            mock_anthropic_cls.return_value = mock_client
            mock_client.messages.create.return_value = fake_message

            client = ClaudeClient(api_key="test-key")
            result = client.generate_json("some prompt")

        assert result == {"key": "value"}
        usage = client.get_last_usage()
        assert usage.input_tokens == 200
        assert usage.output_tokens == 80

    def test_claude_records_cached_tokens(self):
        from core.llm import ClaudeClient

        fake_usage = SimpleNamespace(
            input_tokens=100,
            output_tokens=50,
            cache_read_input_tokens=300,
        )
        fake_message = SimpleNamespace(
            content=[SimpleNamespace(text="cached response")],
            usage=fake_usage,
        )
        with patch("anthropic.Anthropic") as mock_anthropic_cls:
            mock_client = MagicMock()
            mock_anthropic_cls.return_value = mock_client
            mock_client.messages.create.return_value = fake_message

            client = ClaudeClient(api_key="test-key")
            client.generate("prompt")

        assert client.get_last_usage().cached_input_tokens == 300

    def test_claude_get_last_usage_default_before_any_call(self):
        from core.llm import ClaudeClient, TokenUsage
        with patch("anthropic.Anthropic"):
            client = ClaudeClient(api_key="test-key")
        usage = client.get_last_usage()
        assert isinstance(usage, TokenUsage)
        assert usage.total_tokens == 0


class TestGeminiTokenObservability:
    def _make_gemini_client(self, fake_response):
        """GeminiClient를 mock client + _make_config mock으로 생성한다."""
        from core.llm import GeminiClient

        mock_inner_client = MagicMock()
        mock_inner_client.models.generate_content.return_value = fake_response

        client = GeminiClient.__new__(GeminiClient)
        client.api_key = "test-key"
        client.model_name = "gemini-2.5-flash"
        client.thinking_level = "none"
        client._last_usage = __import__("core.llm", fromlist=["TokenUsage"]).TokenUsage()
        client.client = mock_inner_client
        # _make_config은 google.genai.types를 import하므로 mock으로 대체
        client._make_config = MagicMock(return_value=MagicMock())
        return client

    def test_gemini_generate_records_usage(self):
        fake_usage = SimpleNamespace(prompt_token_count=80, candidates_token_count=40)
        fake_response = SimpleNamespace(text="gemini reply", usage_metadata=fake_usage)

        client = self._make_gemini_client(fake_response)
        result = client.generate("prompt")

        assert result == "gemini reply"
        usage = client.get_last_usage()
        assert usage.input_tokens == 80
        assert usage.output_tokens == 40

    def test_gemini_generate_json_records_usage(self):
        fake_usage = SimpleNamespace(prompt_token_count=120, candidates_token_count=60)
        fake_response = SimpleNamespace(text='{"result": 42}', usage_metadata=fake_usage)

        client = self._make_gemini_client(fake_response)
        result = client.generate_json("prompt")

        assert result == {"result": 42}
        usage = client.get_last_usage()
        assert usage.input_tokens == 120
        assert usage.output_tokens == 60


class TestBaseLLMClientDefaultUsage:
    def test_base_client_get_last_usage_no_op(self):
        """BaseLLMClient 기본 구현은 TokenUsage() 반환 (기존 코드 무파괴)."""
        from core.llm import BaseLLMClient, TokenUsage

        class MinimalClient(BaseLLMClient):
            def generate(self, prompt): return ""
            def generate_json(self, prompt, max_tokens=8192): return {}

        client = MinimalClient()
        usage = client.get_last_usage()
        assert isinstance(usage, TokenUsage)
        assert usage.total_tokens == 0


# ─────────────────────────────────────────────────────────────────────────────
# 2. CAREER CONTEXT COMPRESSION
# ─────────────────────────────────────────────────────────────────────────────

class TestPromptOptimizerInCore:
    def test_importable_from_core(self):
        from core.prompt_optimizer import PromptTokenOptimizer
        assert PromptTokenOptimizer is not None

    def test_real_estate_shim_still_works(self):
        from modules.real_estate.prompt_optimizer import PromptTokenOptimizer
        assert PromptTokenOptimizer is not None

    def test_slim_list_keeps_only_fields(self):
        from core.prompt_optimizer import PromptTokenOptimizer
        items = [{"a": 1, "b": 2, "c": 3}, {"a": 4, "b": 5, "c": 6}]
        result = PromptTokenOptimizer.slim_list(items, {"a", "c"})
        assert all("b" not in r for r in result)
        assert result[0]["a"] == 1

    def test_truncate(self):
        from core.prompt_optimizer import PromptTokenOptimizer
        assert PromptTokenOptimizer.truncate("abcdef", 3) == "abc"

    def test_compact_json_no_whitespace(self):
        from core.prompt_optimizer import PromptTokenOptimizer
        result = PromptTokenOptimizer.compact_json({"a": 1, "b": 2})
        assert " " not in result


class TestJobAnalyzerCompression:
    def _make_postings(self, n: int):
        from modules.career.models import JobPosting
        return [
            JobPosting(
                id=str(i),
                company=f"Co {i}",
                position=f"Engineer {i}",
                skills=["Python", "Go"],
                url=f"https://example.com/{i}",
                source="test",
            )
            for i in range(n)
        ]

    def test_limits_to_30_postings(self):
        from modules.career.processors.job_analyzer import JobAnalyzer

        analyzer = JobAnalyzer.__new__(JobAnalyzer)
        analyzer.llm = MagicMock()
        analyzer.prompt_loader = MagicMock()

        captured = {}

        def fake_call_llm(prompt_key, variables, model_class, **kwargs):
            captured["variables"] = variables
            return model_class()

        analyzer._call_llm = fake_call_llm

        postings = self._make_postings(50)
        analyzer.analyze(postings, {"experience_years": 3})

        payload = json.loads(captured["variables"]["job_postings"])
        assert len(payload) == 30

    def test_fewer_than_30_postings_pass_through(self):
        from modules.career.processors.job_analyzer import JobAnalyzer

        analyzer = JobAnalyzer.__new__(JobAnalyzer)
        analyzer.llm = MagicMock()
        analyzer.prompt_loader = MagicMock()

        captured = {}

        def fake_call_llm(prompt_key, variables, model_class, **kwargs):
            captured["variables"] = variables
            return model_class()

        analyzer._call_llm = fake_call_llm

        postings = self._make_postings(10)
        analyzer.analyze(postings, {"experience_years": 3})

        payload = json.loads(captured["variables"]["job_postings"])
        assert len(payload) == 10


class TestTrendAnalyzerCompression:
    def _make_repos(self, n: int, desc_len: int = 50):
        from modules.career.models import TrendingRepo
        return [
            TrendingRepo(
                name=f"repo{i}",
                description="x" * desc_len,
                language="Python",
                stars_today=i,
                url=f"https://github.com/repo{i}",
            )
            for i in range(n)
        ]

    def _make_stories(self, n: int):
        from modules.career.models import HNStory
        return [HNStory(id=i, title=f"story{i}", score=i) for i in range(n)]

    def _make_articles(self, n: int):
        from modules.career.models import DevToArticle
        return [
            DevToArticle(id=i, title=f"article{i}", url=f"https://dev.to/{i}", reactions=i)
            for i in range(n)
        ]

    def test_limits_each_source_to_20(self):
        from modules.career.processors.trend_analyzer import TrendAnalyzer

        analyzer = TrendAnalyzer.__new__(TrendAnalyzer)
        analyzer.llm = MagicMock()
        analyzer.prompt_loader = MagicMock()

        captured = {}

        def fake_call_llm(prompt_key, variables, model_class, **kwargs):
            captured["variables"] = variables
            return model_class()

        analyzer._call_llm = fake_call_llm

        repos = self._make_repos(40)
        stories = self._make_stories(40)
        articles = self._make_articles(40)

        analyzer.analyze(repos, stories, articles, ["Python"])

        assert len(json.loads(captured["variables"]["github_repos"])) <= 20
        assert len(json.loads(captured["variables"]["hn_stories"])) <= 20
        assert len(json.loads(captured["variables"]["devto_articles"])) <= 20

    def test_truncates_repo_description_to_200(self):
        from modules.career.processors.trend_analyzer import TrendAnalyzer

        analyzer = TrendAnalyzer.__new__(TrendAnalyzer)
        analyzer.llm = MagicMock()
        analyzer.prompt_loader = MagicMock()

        captured = {}

        def fake_call_llm(prompt_key, variables, model_class, **kwargs):
            captured["variables"] = variables
            return model_class()

        analyzer._call_llm = fake_call_llm

        repos = self._make_repos(1, desc_len=400)
        analyzer.analyze(repos, [], [], [])

        repos_payload = json.loads(captured["variables"]["github_repos"])
        assert len(repos_payload[0]["description"]) <= 200


class TestCommunityAnalyzerCompression:
    def _make_reddit(self, n: int, selftext_len: int = 100):
        from modules.career.models import RedditPost
        return [
            RedditPost(id=str(i), title=f"Post {i}", subreddit="programming",
                       selftext="x" * selftext_len)
            for i in range(n)
        ]

    def _make_tweets(self, n: int, text_len: int = 100):
        from modules.career.models import NitterTweet
        return [
            NitterTweet(id=str(i), text="x" * text_len, username=f"user{i}")
            for i in range(n)
        ]

    def _make_korean(self, n: int):
        from modules.career.models import KoreanPost
        return [
            KoreanPost(id=str(i), title=f"글 {i}", source="clien")
            for i in range(n)
        ]

    def test_limits_posts_to_25_per_source(self):
        from modules.career.processors.community_analyzer import CommunityAnalyzer

        analyzer = CommunityAnalyzer.__new__(CommunityAnalyzer)
        analyzer.llm = MagicMock()
        analyzer.prompt_loader = MagicMock()

        captured = {}

        def fake_call_llm(prompt_key, variables, model_class, **kwargs):
            captured["variables"] = variables
            result = model_class()
            result.collection_status = {}
            return result

        analyzer._call_llm = fake_call_llm

        reddit = self._make_reddit(40)
        tweets = self._make_tweets(40)
        korean = self._make_korean(40)

        analyzer.analyze(reddit, tweets, korean, {})

        assert len(json.loads(captured["variables"]["reddit_posts"])) <= 25
        assert len(json.loads(captured["variables"]["nitter_tweets"])) <= 25
        assert len(json.loads(captured["variables"]["korean_posts"])) <= 25

    def test_truncates_reddit_selftext_to_150(self):
        from modules.career.processors.community_analyzer import CommunityAnalyzer

        analyzer = CommunityAnalyzer.__new__(CommunityAnalyzer)
        analyzer.llm = MagicMock()
        analyzer.prompt_loader = MagicMock()

        captured = {}

        def fake_call_llm(prompt_key, variables, model_class, **kwargs):
            captured["variables"] = variables
            result = model_class()
            result.collection_status = {}
            return result

        analyzer._call_llm = fake_call_llm

        reddit = self._make_reddit(1, selftext_len=400)
        analyzer.analyze(reddit, [], [], {})

        r_posts = json.loads(captured["variables"]["reddit_posts"])
        assert len(r_posts[0].get("selftext", "")) <= 150

    def test_truncates_tweet_text_to_150(self):
        from modules.career.processors.community_analyzer import CommunityAnalyzer

        analyzer = CommunityAnalyzer.__new__(CommunityAnalyzer)
        analyzer.llm = MagicMock()
        analyzer.prompt_loader = MagicMock()

        captured = {}

        def fake_call_llm(prompt_key, variables, model_class, **kwargs):
            captured["variables"] = variables
            result = model_class()
            result.collection_status = {}
            return result

        analyzer._call_llm = fake_call_llm

        tweets = self._make_tweets(1, text_len=400)
        analyzer.analyze([], tweets, [], {})

        t_posts = json.loads(captured["variables"]["nitter_tweets"])
        assert len(t_posts[0].get("text", "")) <= 150


# ─────────────────────────────────────────────────────────────────────────────
# 3. MODEL ROUTING
# ─────────────────────────────────────────────────────────────────────────────

class TestModelRouting:
    def test_task_type_enum_values(self):
        from core.llm import TaskType
        assert TaskType.ANALYSIS == "analysis"
        assert TaskType.EXTRACTION == "extraction"
        assert TaskType.SYNTHESIS == "synthesis"

    def test_factory_returns_haiku_for_extraction(self, monkeypatch):
        from core.llm import LLMFactory, TaskType
        monkeypatch.setenv("LLM_PROVIDER", "claude")
        monkeypatch.setenv("CLAUDE_EXTRACTION_MODEL", "claude-haiku-4-5")

        with patch("anthropic.Anthropic"):
            client = LLMFactory.create(task_type=TaskType.EXTRACTION)

        assert client.model_name == "claude-haiku-4-5"

    def test_factory_returns_sonnet_for_analysis(self, monkeypatch):
        from core.llm import LLMFactory, TaskType
        monkeypatch.setenv("LLM_PROVIDER", "claude")
        monkeypatch.setenv("CLAUDE_ANALYSIS_MODEL", "claude-sonnet-4-6")

        with patch("anthropic.Anthropic"):
            client = LLMFactory.create(task_type=TaskType.ANALYSIS)

        assert client.model_name == "claude-sonnet-4-6"

    def test_factory_default_no_task_type(self, monkeypatch):
        from core.llm import LLMFactory
        monkeypatch.setenv("LLM_PROVIDER", "claude")

        with patch("anthropic.Anthropic"):
            client = LLMFactory.create()

        # 기본 CLAUDE_MODEL 또는 fallback
        assert client.model_name is not None

    def test_llm_client_alias_still_works(self, monkeypatch):
        from core.llm import LLMClient
        monkeypatch.setenv("LLM_PROVIDER", "claude")

        with patch("anthropic.Anthropic"):
            client = LLMClient()

        assert client is not None

    def test_factory_falls_back_to_default_model_when_env_not_set(self, monkeypatch):
        from core.llm import LLMFactory, TaskType
        monkeypatch.setenv("LLM_PROVIDER", "claude")
        monkeypatch.delenv("CLAUDE_EXTRACTION_MODEL", raising=False)

        with patch("anthropic.Anthropic"):
            client = LLMFactory.create(task_type=TaskType.EXTRACTION)

        # env 없을 때 hardcoded default: claude-haiku-4-5
        assert "haiku" in client.model_name

    def test_claude_client_model_override(self, monkeypatch):
        from core.llm import ClaudeClient
        with patch("anthropic.Anthropic"):
            client = ClaudeClient(api_key="test", model_override="claude-haiku-4-5")
        assert client.model_name == "claude-haiku-4-5"


# ─────────────────────────────────────────────────────────────────────────────
# 4. PROMPT CACHING
# ─────────────────────────────────────────────────────────────────────────────

class TestPromptLoaderCacheSplit:
    def _make_loader(self, prompt_content: str):
        from core.prompt_loader import PromptLoader
        storage = MagicMock()
        storage.read_file.return_value = prompt_content
        return PromptLoader(storage=storage)

    def test_split_at_boundary(self):
        content = "---\ncache_boundary: \"## 입력 데이터\"\n---\n# 역할\n분석관.\n\n## 입력 데이터\n데이터: {{ value }}"
        loader = self._make_loader(content)
        meta, static, dynamic = loader.load_with_cache_split("any/path", {"value": "test"})

        assert "역할" in static
        assert "입력 데이터" in dynamic
        assert "입력 데이터" not in static or static.strip().endswith("분석관.")

    def test_no_boundary_returns_full_as_static(self):
        content = "---\nname: test\n---\n전체 프롬프트 내용"
        loader = self._make_loader(content)
        meta, static, dynamic = loader.load_with_cache_split("any/path", {})

        assert "전체 프롬프트 내용" in static
        assert dynamic == ""

    def test_jinja2_rendered_in_static_portion(self):
        content = "---\ncache_boundary: \"## DATA\"\n---\n역할: {{ role }}\n\n## DATA\n입력"
        loader = self._make_loader(content)
        _, static, _ = loader.load_with_cache_split("p", {"role": "analyst"})
        assert "analyst" in static


class TestClaudeGenerateWithCache:
    def _make_claude_client(self, fake_message):
        from core.llm import ClaudeClient
        with patch("anthropic.Anthropic") as mock_cls:
            mock_client = MagicMock()
            mock_cls.return_value = mock_client
            mock_client.messages.create.return_value = fake_message
            client = ClaudeClient(api_key="test-key")
            client.client = mock_client
        return client

    def test_generate_with_cache_sends_two_blocks(self):
        from core.llm import ClaudeClient

        fake_usage = SimpleNamespace(
            input_tokens=100, output_tokens=50,
            cache_read_input_tokens=0,
        )
        fake_message = SimpleNamespace(
            content=[SimpleNamespace(text="ok")],
            usage=fake_usage,
        )

        with patch("anthropic.Anthropic") as mock_cls:
            mock_client = MagicMock()
            mock_cls.return_value = mock_client
            mock_client.messages.create.return_value = fake_message

            client = ClaudeClient(api_key="test-key")
            client.client = mock_client
            result = client.generate_with_cache("static part", "dynamic part")

        call_kwargs = mock_client.messages.create.call_args
        messages = call_kwargs.kwargs.get("messages") or call_kwargs[1].get("messages") or call_kwargs[0][2]
        content_blocks = messages[0]["content"]
        assert len(content_blocks) == 2
        assert content_blocks[0].get("cache_control") == {"type": "ephemeral"}
        assert "cache_control" not in content_blocks[1]

    def test_generate_with_cache_records_cached_tokens(self):
        from core.llm import ClaudeClient

        fake_usage = SimpleNamespace(
            input_tokens=100, output_tokens=50,
            cache_read_input_tokens=500,
        )
        fake_message = SimpleNamespace(
            content=[SimpleNamespace(text="ok")],
            usage=fake_usage,
        )

        with patch("anthropic.Anthropic") as mock_cls:
            mock_client = MagicMock()
            mock_cls.return_value = mock_client
            mock_client.messages.create.return_value = fake_message

            client = ClaudeClient(api_key="test-key")
            client.client = mock_client
            client.generate_with_cache("static", "dynamic")

        assert client.get_last_usage().cached_input_tokens == 500

    def test_generate_with_cache_only_static_block_when_no_dynamic(self):
        from core.llm import ClaudeClient

        fake_usage = SimpleNamespace(
            input_tokens=50, output_tokens=20, cache_read_input_tokens=0
        )
        fake_message = SimpleNamespace(
            content=[SimpleNamespace(text="ok")], usage=fake_usage
        )

        with patch("anthropic.Anthropic") as mock_cls:
            mock_client = MagicMock()
            mock_cls.return_value = mock_client
            mock_client.messages.create.return_value = fake_message

            client = ClaudeClient(api_key="test-key")
            client.client = mock_client
            client.generate_with_cache("static only", "")

        call_kwargs = mock_client.messages.create.call_args
        messages = (
            call_kwargs.kwargs.get("messages")
            or call_kwargs[1].get("messages")
            or call_kwargs[0][2]
        )
        content_blocks = messages[0]["content"]
        assert len(content_blocks) == 1


class TestBaseAnalyzerUseCacheFlag:
    def test_use_cache_true_calls_generate_json_with_cache(self):
        from modules.career.processors.base import BaseAnalyzer
        from modules.career.models import JobAnalysis

        class FakeAnalyzer(BaseAnalyzer):
            def analyze(self, *args, **kwargs): ...

        fake_llm = MagicMock()
        fake_llm.generate_json_with_cache.return_value = {
            "top_skills": [], "salary_range": {}, "hiring_signal": "neutral",
            "top_companies": [], "analysis_summary": "", "analyzed_at": "2026-01-01"
        }

        fake_loader = MagicMock()
        fake_loader.load_with_cache_split.return_value = ({}, "static", "dynamic")

        analyzer = FakeAnalyzer(llm=fake_llm, prompt_loader=fake_loader)
        result = analyzer._call_llm("some/prompt", {}, JobAnalysis, use_cache=True)

        fake_llm.generate_json_with_cache.assert_called_once()
        fake_llm.generate_json.assert_not_called()

    def test_use_cache_false_calls_generate_json(self):
        from modules.career.processors.base import BaseAnalyzer
        from modules.career.models import JobAnalysis

        class FakeAnalyzer(BaseAnalyzer):
            def analyze(self, *args, **kwargs): ...

        fake_llm = MagicMock()
        fake_llm.generate_json.return_value = {
            "top_skills": [], "salary_range": {}, "hiring_signal": "neutral",
            "top_companies": [], "analysis_summary": "", "analyzed_at": "2026-01-01"
        }

        fake_loader = MagicMock()
        fake_loader.load.return_value = ({}, "full prompt")

        analyzer = FakeAnalyzer(llm=fake_llm, prompt_loader=fake_loader)
        result = analyzer._call_llm("some/prompt", {}, JobAnalysis, use_cache=False)

        fake_llm.generate_json.assert_called_once()
        fake_llm.generate_json_with_cache.assert_not_called()


# ─────────────────────────────────────────────────────────────────────────────
# 5. SEMANTIC / RESPONSE CACHE
# ─────────────────────────────────────────────────────────────────────────────

class TestLLMResponseCache:
    def test_cache_miss_returns_none(self, tmp_path):
        from core.llm_cache import LLMResponseCache
        cache = LLMResponseCache(base_dir=str(tmp_path))
        assert cache.get("some prompt", ttl_seconds=86400) is None

    def test_put_and_get_returns_entry(self, tmp_path):
        from core.llm_cache import LLMResponseCache
        from core.llm import TokenUsage
        cache = LLMResponseCache(base_dir=str(tmp_path))
        cache.put("my prompt", "my response", TokenUsage(100, 50))
        entry = cache.get("my prompt", ttl_seconds=86400)
        assert entry is not None
        assert entry.response == "my response"
        assert entry.input_tokens == 100
        assert entry.output_tokens == 50

    def test_cache_expires_after_ttl(self, tmp_path):
        from core.llm_cache import LLMResponseCache, CacheEntry
        from core.llm import TokenUsage
        cache = LLMResponseCache(base_dir=str(tmp_path))
        cache.put("old prompt", "old response", TokenUsage(10, 5))

        # 강제로 created_at을 과거로 세팅
        key = hashlib.sha256("old prompt".encode()).hexdigest()
        path = tmp_path / key[:2] / f"{key}.json"
        data = json.loads(path.read_text())
        data["created_at"] = time.time() - 90000
        path.write_text(json.dumps(data))

        result = cache.get("old prompt", ttl_seconds=86400)
        assert result is None

    def test_cache_key_is_sha256(self, tmp_path):
        from core.llm_cache import LLMResponseCache
        cache = LLMResponseCache(base_dir=str(tmp_path))
        prompt = "unique prompt"
        expected_hash = hashlib.sha256(prompt.encode()).hexdigest()
        key = cache._key(prompt)
        assert key == expected_hash

    def test_different_prompts_different_keys(self, tmp_path):
        from core.llm_cache import LLMResponseCache
        cache = LLMResponseCache(base_dir=str(tmp_path))
        assert cache._key("prompt A") != cache._key("prompt B")

    def test_invalidate_removes_file(self, tmp_path):
        from core.llm_cache import LLMResponseCache
        from core.llm import TokenUsage
        cache = LLMResponseCache(base_dir=str(tmp_path))
        cache.put("to delete", "data", TokenUsage(10, 5))
        assert cache.get("to delete", 86400) is not None
        removed = cache.invalidate("to delete")
        assert removed is True
        assert cache.get("to delete", 86400) is None

    def test_invalidate_nonexistent_returns_false(self, tmp_path):
        from core.llm_cache import LLMResponseCache
        cache = LLMResponseCache(base_dir=str(tmp_path))
        assert cache.invalidate("nonexistent") is False


class TestCachedLLMClient:
    def _make_inner(self, text_response="hello", json_response=None, usage=None):
        from core.llm import TokenUsage
        inner = MagicMock()
        inner.generate.return_value = text_response
        inner.generate_json.return_value = json_response or {"key": "val"}
        inner.get_last_usage.return_value = usage or TokenUsage(100, 50)
        return inner

    def test_cache_miss_calls_inner(self, tmp_path):
        from core.llm_cache import LLMResponseCache, CachedLLMClient
        inner = self._make_inner()
        cache = LLMResponseCache(base_dir=str(tmp_path))
        client = CachedLLMClient(inner=inner, cache=cache, ttl_seconds=86400)

        result = client.generate("prompt")
        assert result == "hello"
        inner.generate.assert_called_once_with("prompt")

    def test_cache_hit_skips_inner(self, tmp_path):
        from core.llm_cache import LLMResponseCache, CachedLLMClient
        from core.llm import TokenUsage
        inner = self._make_inner()
        cache = LLMResponseCache(base_dir=str(tmp_path))
        cache.put("prompt", "cached hello", TokenUsage(10, 5))

        client = CachedLLMClient(inner=inner, cache=cache, ttl_seconds=86400)
        result = client.generate("prompt")

        assert result == "cached hello"
        inner.generate.assert_not_called()

    def test_generate_json_cache_hit_returns_dict(self, tmp_path):
        from core.llm_cache import LLMResponseCache, CachedLLMClient
        from core.llm import TokenUsage
        inner = self._make_inner()
        cache = LLMResponseCache(base_dir=str(tmp_path))
        cache.put("json prompt", json.dumps({"cached": True}), TokenUsage(10, 5))

        client = CachedLLMClient(inner=inner, cache=cache, ttl_seconds=86400)
        result = client.generate_json("json prompt")

        assert result == {"cached": True}
        inner.generate_json.assert_not_called()

    def test_get_last_usage_on_cache_hit(self, tmp_path):
        from core.llm_cache import LLMResponseCache, CachedLLMClient
        from core.llm import TokenUsage
        inner = self._make_inner()
        cache = LLMResponseCache(base_dir=str(tmp_path))
        cache.put("p", "resp", TokenUsage(10, 5))

        client = CachedLLMClient(inner=inner, cache=cache, ttl_seconds=86400)
        client.generate("p")

        usage = client.get_last_usage()
        assert usage.input_tokens == 10
        assert usage.output_tokens == 5

    def test_get_last_usage_on_cache_miss(self, tmp_path):
        from core.llm_cache import LLMResponseCache, CachedLLMClient
        from core.llm import TokenUsage
        inner = self._make_inner(usage=TokenUsage(100, 50))
        cache = LLMResponseCache(base_dir=str(tmp_path))

        client = CachedLLMClient(inner=inner, cache=cache, ttl_seconds=86400)
        client.generate("fresh prompt")

        usage = client.get_last_usage()
        assert usage.input_tokens == 100
        assert usage.output_tokens == 50

    def test_cached_client_is_base_llm_client(self, tmp_path):
        from core.llm_cache import LLMResponseCache, CachedLLMClient
        from core.llm import BaseLLMClient
        inner = self._make_inner()
        cache = LLMResponseCache(base_dir=str(tmp_path))
        client = CachedLLMClient(inner=inner, cache=cache, ttl_seconds=86400)
        assert isinstance(client, BaseLLMClient)
