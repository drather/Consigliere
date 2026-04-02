"""
LLM Filter Chain — 테스트 모음 (TDD: Red → Green)

테스트 구성:
  U01~U02  : LLMRequest / LLMResponse 데이터클래스
  MR01~MR05: ModelRoutingFilter
  SC01~SC04: SemanticCacheFilter
  PC01~PC04: PromptCacheFilter
  TL01~TL03: TokenLogFilter
  CH01~CH04: LLMFilterChain
  INT01~INT05: build_llm_pipeline() 통합
"""
import json
import os
import sys
import time
from types import SimpleNamespace
from typing import Dict, Any
from unittest.mock import MagicMock, patch, call

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))


# ─────────────────────────────────────────────────────────────────────────────
# 헬퍼: mock inner LLM client 생성
# ─────────────────────────────────────────────────────────────────────────────

def _make_mock_inner(json_response=None, model_name="mock-model"):
    from core.llm import TokenUsage
    inner = MagicMock()
    inner.model_name = model_name
    inner.generate_json.return_value = json_response or {"result": "ok"}
    inner.generate_json_with_cache = MagicMock(return_value=json_response or {"result": "ok"})
    inner.get_last_usage.return_value = TokenUsage(input_tokens=100, output_tokens=50)
    return inner


# ─────────────────────────────────────────────────────────────────────────────
# U01~U02: LLMRequest / LLMResponse 데이터클래스
# ─────────────────────────────────────────────────────────────────────────────

class TestLLMRequestResponse:
    def test_u01_request_defaults(self):
        """U01: LLMRequest 기본 생성 — metadata 기본값 빈 dict, static_prompt None"""
        from core.llm_pipeline import LLMRequest
        req = LLMRequest(prompt="hello")
        assert req.prompt == "hello"
        assert req.max_tokens == 8192
        assert req.metadata == {}
        assert req.static_prompt is None
        assert req.dynamic_prompt is None

    def test_u02_response_from_cache_default(self):
        """U02: LLMResponse from_cache 기본값 — False"""
        from core.llm_pipeline import LLMResponse
        from core.llm import TokenUsage
        resp = LLMResponse(data={"x": 1}, usage=TokenUsage(), model_used="test-model")
        assert resp.from_cache is False


# ─────────────────────────────────────────────────────────────────────────────
# MR01~MR05: ModelRoutingFilter
# ─────────────────────────────────────────────────────────────────────────────

class TestModelRoutingFilter:
    def _make_chain(self, inner, request):
        """필터 없는 체인 (실제 API 호출 직행) — ModelRoutingFilter 단독 테스트용."""
        from core.llm_pipeline import LLMFilterChain
        chain = LLMFilterChain(filters=[], inner=inner)
        return chain

    def test_mr01_extraction_selects_haiku(self, monkeypatch, tmp_path):
        """MR01: task_type=extraction → haiku 계열 client 선택 (LLMFactory mock)"""
        from core.llm_pipeline import ModelRoutingFilter, LLMRequest, LLMFilterChain
        from core.llm import TokenUsage

        monkeypatch.setenv("LLM_PROVIDER", "claude")
        monkeypatch.setenv("CLAUDE_EXTRACTION_MODEL", "claude-haiku-4-5")

        haiku_client = MagicMock()
        haiku_client.model_name = "claude-haiku-4-5"
        haiku_client.generate_json.return_value = {"result": "ok"}
        haiku_client.get_last_usage.return_value = TokenUsage(10, 5)

        with patch("core.llm_pipeline.LLMFactory") as mock_factory:
            mock_factory.create.return_value = haiku_client

            inner = _make_mock_inner()
            filt = ModelRoutingFilter()
            chain = LLMFilterChain(filters=[filt], inner=inner)

            req = LLMRequest(prompt="test", metadata={"task_type": "extraction"})
            resp = chain.generate_json("test", metadata={"task_type": "extraction"})

            # LLMFactory.create가 task_type으로 호출되었는지 확인
            assert mock_factory.create.called

    def test_mr02_analysis_selects_sonnet(self, monkeypatch):
        """MR02: task_type=analysis → sonnet 계열 client 선택"""
        from core.llm_pipeline import ModelRoutingFilter, LLMRequest, LLMFilterChain
        from core.llm import TokenUsage

        monkeypatch.setenv("LLM_PROVIDER", "claude")

        sonnet_client = MagicMock()
        sonnet_client.model_name = "claude-sonnet-4-6"
        sonnet_client.generate_json.return_value = {"result": "ok"}
        sonnet_client.get_last_usage.return_value = TokenUsage(100, 50)

        with patch("core.llm_pipeline.LLMFactory") as mock_factory:
            mock_factory.create.return_value = sonnet_client

            inner = _make_mock_inner()
            chain = LLMFilterChain(filters=[ModelRoutingFilter()], inner=inner)
            chain.generate_json("test", metadata={"task_type": "analysis"})

            assert mock_factory.create.called

    def test_mr03_synthesis_selects_sonnet(self, monkeypatch):
        """MR03: task_type=synthesis → sonnet 계열 client 선택"""
        from core.llm_pipeline import ModelRoutingFilter, LLMRequest, LLMFilterChain
        from core.llm import TokenUsage

        monkeypatch.setenv("LLM_PROVIDER", "claude")

        sonnet_client = MagicMock()
        sonnet_client.model_name = "claude-sonnet-4-6"
        sonnet_client.generate_json.return_value = {"result": "ok"}
        sonnet_client.get_last_usage.return_value = TokenUsage(100, 50)

        with patch("core.llm_pipeline.LLMFactory") as mock_factory:
            mock_factory.create.return_value = sonnet_client

            inner = _make_mock_inner()
            chain = LLMFilterChain(filters=[ModelRoutingFilter()], inner=inner)
            chain.generate_json("test", metadata={"task_type": "synthesis"})

            assert mock_factory.create.called

    def test_mr04_no_task_type_uses_inner(self, monkeypatch):
        """MR04: task_type 없음 → 기본 inner client 그대로 사용 (LLMFactory.create 미호출)"""
        from core.llm_pipeline import ModelRoutingFilter, LLMFilterChain
        from core.llm import TokenUsage

        monkeypatch.setenv("LLM_PROVIDER", "claude")

        inner = _make_mock_inner()
        with patch("core.llm_pipeline.LLMFactory") as mock_factory:
            chain = LLMFilterChain(filters=[ModelRoutingFilter()], inner=inner)
            chain.generate_json("test", metadata={})

            # task_type 없으면 LLMFactory.create 미호출
            mock_factory.create.assert_not_called()

        inner.generate_json.assert_called_once()

    def test_mr05_gemini_provider_noop(self, monkeypatch):
        """MR05: provider=gemini → task_type 무시, inner 그대로 사용"""
        from core.llm_pipeline import ModelRoutingFilter, LLMFilterChain
        from core.llm import TokenUsage

        monkeypatch.setenv("LLM_PROVIDER", "gemini")

        inner = _make_mock_inner()
        with patch("core.llm_pipeline.LLMFactory") as mock_factory:
            chain = LLMFilterChain(filters=[ModelRoutingFilter()], inner=inner)
            chain.generate_json("test", metadata={"task_type": "extraction"})

            # Gemini provider이면 LLMFactory.create 미호출
            mock_factory.create.assert_not_called()

        inner.generate_json.assert_called_once()


# ─────────────────────────────────────────────────────────────────────────────
# SC01~SC04: SemanticCacheFilter
# ─────────────────────────────────────────────────────────────────────────────

class TestSemanticCacheFilter:
    def test_sc01_cache_miss_calls_proceed_and_puts_cache(self, tmp_path):
        """SC01: 캐시 미스 → chain.proceed() 호출, LLMResponseCache.put() 호출 확인"""
        from core.llm_pipeline import SemanticCacheFilter, LLMFilterChain
        from core.llm_cache import LLMResponseCache
        from core.llm import TokenUsage

        inner = _make_mock_inner(json_response={"key": "val"})
        cache = LLMResponseCache(base_dir=str(tmp_path))

        filt = SemanticCacheFilter(cache=cache)
        chain = LLMFilterChain(filters=[filt], inner=inner)

        resp = chain.generate_json("new prompt", metadata={})

        assert resp == {"key": "val"}
        inner.generate_json.assert_called_once()
        # 캐시에 저장되었는지 확인
        entry = cache.get("new prompt", ttl_seconds=86400)
        assert entry is not None

    def test_sc02_cache_hit_skips_proceed(self, tmp_path):
        """SC02: 캐시 히트 → chain.proceed() 미호출, response.from_cache == True"""
        from core.llm_pipeline import SemanticCacheFilter, LLMFilterChain, LLMResponse
        from core.llm_cache import LLMResponseCache
        from core.llm import TokenUsage

        inner = _make_mock_inner(json_response={"fresh": True})
        cache = LLMResponseCache(base_dir=str(tmp_path))

        # 미리 캐시에 데이터 저장
        cache.put("cached prompt", json.dumps({"cached": True}), TokenUsage(10, 5))

        filt = SemanticCacheFilter(cache=cache)
        chain = LLMFilterChain(filters=[filt], inner=inner)

        # SemanticCacheFilter가 LLMResponse를 반환하는지 체크하기 위해 generate_json 직접 호출
        # chain.generate_json은 dict를 반환하므로, 내부적으로 LLMResponse.from_cache를 확인하려면
        # _last_response를 체크하거나 체인 내부 동작 확인
        result = chain.generate_json("cached prompt", metadata={})

        # inner는 호출되지 않아야 함
        inner.generate_json.assert_not_called()
        assert result == {"cached": True}

    def test_sc03_metadata_ttl_applied(self, tmp_path):
        """SC03: metadata["ttl"] 적용 — 지정 TTL로 cache.get() 호출 확인"""
        from core.llm_pipeline import SemanticCacheFilter, LLMFilterChain
        from core.llm_cache import LLMResponseCache
        from core.llm import TokenUsage

        inner = _make_mock_inner()
        cache = LLMResponseCache(base_dir=str(tmp_path))

        with patch.object(cache, 'get', wraps=cache.get) as mock_get:
            filt = SemanticCacheFilter(cache=cache)
            chain = LLMFilterChain(filters=[filt], inner=inner)
            chain.generate_json("test prompt", metadata={"ttl": 3600})

            mock_get.assert_called_once_with("test prompt", 3600)

    def test_sc05_error_response_not_cached(self, tmp_path):
        """SC05: 에러 응답 캐시 저장 금지 — inner가 {"error": ...} 반환 시 캐시에 저장하지 않음"""
        from core.llm_pipeline import SemanticCacheFilter, LLMFilterChain
        from core.llm_cache import LLMResponseCache

        inner = _make_mock_inner(json_response={"error": "credit balance too low"})
        cache = LLMResponseCache(base_dir=str(tmp_path))

        filt = SemanticCacheFilter(cache=cache)
        chain = LLMFilterChain(filters=[filt], inner=inner)

        chain.generate_json("some prompt", metadata={})

        # 에러 응답은 캐시에 저장되지 않아야 함
        entry = cache.get("some prompt", ttl_seconds=86400)
        assert entry is None

    def test_sc04_expired_ttl_is_miss(self, tmp_path):
        """SC04: TTL 만료 항목 → 미스 처리, chain.proceed() 재호출"""
        import hashlib
        from core.llm_pipeline import SemanticCacheFilter, LLMFilterChain
        from core.llm_cache import LLMResponseCache
        from core.llm import TokenUsage

        inner = _make_mock_inner(json_response={"fresh": True})
        cache = LLMResponseCache(base_dir=str(tmp_path))

        # 캐시에 저장 후 created_at을 과거로 변경
        prompt = "expired prompt"
        cache.put(prompt, json.dumps({"old": True}), TokenUsage(10, 5))

        key = hashlib.sha256(prompt.encode()).hexdigest()
        path = tmp_path / key[:2] / f"{key}.json"
        data = json.loads(path.read_text())
        data["created_at"] = time.time() - 90000  # TTL 초과
        path.write_text(json.dumps(data))

        filt = SemanticCacheFilter(cache=cache)
        chain = LLMFilterChain(filters=[filt], inner=inner)

        result = chain.generate_json(prompt, metadata={"ttl": 86400})

        # 만료됐으므로 inner 호출됨
        inner.generate_json.assert_called_once()
        assert result == {"fresh": True}


# ─────────────────────────────────────────────────────────────────────────────
# PC01~PC04: PromptCacheFilter
# ─────────────────────────────────────────────────────────────────────────────

class TestPromptCacheFilter:
    def test_pc01_static_prompt_uses_generate_json_with_cache(self, monkeypatch):
        """PC01: static_prompt 있음, Claude provider → generate_json_with_cache() 호출"""
        from core.llm_pipeline import PromptCacheFilter, LLMRequest, LLMFilterChain
        from core.llm import TokenUsage

        monkeypatch.setenv("LLM_PROVIDER", "claude")

        inner = _make_mock_inner()
        inner.generate_json_with_cache.return_value = {"cached_result": True}

        filt = PromptCacheFilter()
        chain = LLMFilterChain(filters=[filt], inner=inner)

        # static_prompt가 세팅된 경우 — generate_json에서 static_prompt를 metadata로 전달하거나
        # 직접 LLMRequest 생성하여 chain.proceed() 흐름으로 테스트
        # PromptCacheFilter는 request.static_prompt를 보고 동작
        # chain.generate_json은 LLMRequest를 만들고 proceed를 호출함
        # static_prompt를 주입하기 위해 _inject_static 파라미터 방식 사용
        # (spec에 따라 metadata에 cache_boundary가 없으면 no-op이므로, static_prompt는 metadata로 전달 불가)
        # 대신 LLMRequest를 직접 생성하여 chain._proceed 수준에서 테스트
        from core.llm_pipeline import LLMRequest

        req = LLMRequest(
            prompt="full prompt",
            metadata={"task_type": "extraction"},
            static_prompt="static part",
            dynamic_prompt="dynamic part",
        )
        # chain.proceed를 통해 직접 필터 실행
        chain._index = 0
        resp = chain.proceed(req)

        inner.generate_json_with_cache.assert_called_once_with("static part", "dynamic part", max_tokens=8192)
        inner.generate_json.assert_not_called()

    def test_pc02_no_cache_boundary_noop(self, monkeypatch):
        """PC02: static_prompt None, cache_boundary 없음 → 일반 generate_json() 호출 (no-op)"""
        from core.llm_pipeline import PromptCacheFilter, LLMFilterChain, LLMRequest
        from core.llm import TokenUsage

        monkeypatch.setenv("LLM_PROVIDER", "claude")

        inner = _make_mock_inner()
        filt = PromptCacheFilter()
        chain = LLMFilterChain(filters=[filt], inner=inner)

        req = LLMRequest(prompt="simple prompt", metadata={})
        chain._index = 0
        resp = chain.proceed(req)

        inner.generate_json.assert_called_once()
        inner.generate_json_with_cache.assert_not_called()

    def test_pc03_gemini_provider_noop(self, monkeypatch):
        """PC03: Gemini provider → 필터 통과 (no-op), generate_json 호출"""
        from core.llm_pipeline import PromptCacheFilter, LLMFilterChain, LLMRequest
        from core.llm import TokenUsage

        monkeypatch.setenv("LLM_PROVIDER", "gemini")

        inner = _make_mock_inner()
        filt = PromptCacheFilter()
        chain = LLMFilterChain(filters=[filt], inner=inner)

        req = LLMRequest(
            prompt="full prompt",
            metadata={"task_type": "extraction"},
            static_prompt="static part",
            dynamic_prompt="dynamic part",
        )
        chain._index = 0
        resp = chain.proceed(req)

        # Gemini는 generate_json_with_cache를 호출하지 않아야 함
        inner.generate_json_with_cache.assert_not_called()
        inner.generate_json.assert_called_once()

    def test_pc04_empty_dynamic_prompt(self, monkeypatch):
        """PC04: static_prompt 있음, dynamic_prompt 빈 문자열 → 정상 동작"""
        from core.llm_pipeline import PromptCacheFilter, LLMFilterChain, LLMRequest
        from core.llm import TokenUsage

        monkeypatch.setenv("LLM_PROVIDER", "claude")

        inner = _make_mock_inner()
        inner.generate_json_with_cache.return_value = {"ok": True}

        filt = PromptCacheFilter()
        chain = LLMFilterChain(filters=[filt], inner=inner)

        req = LLMRequest(
            prompt="full prompt",
            metadata={},
            static_prompt="static part",
            dynamic_prompt="",  # 빈 문자열
        )
        chain._index = 0
        resp = chain.proceed(req)

        inner.generate_json_with_cache.assert_called_once_with("static part", "", max_tokens=8192)


# ─────────────────────────────────────────────────────────────────────────────
# TL01~TL03: TokenLogFilter
# ─────────────────────────────────────────────────────────────────────────────

class TestTokenLogFilter:
    def test_tl01_logs_after_call(self, caplog):
        """TL01: 호출 후 logger.info 호출 확인 (caplog로 로그 메시지 검증)"""
        import logging
        from core.llm_pipeline import TokenLogFilter, LLMFilterChain, LLMRequest
        from core.llm import TokenUsage

        inner = _make_mock_inner()
        filt = TokenLogFilter()
        chain = LLMFilterChain(filters=[filt], inner=inner)

        with caplog.at_level(logging.INFO):
            chain.generate_json("test prompt", metadata={"task_type": "extraction"})

        # 로그 메시지에 TokenLog 키워드 포함 확인
        assert any("[TokenLog]" in r.message for r in caplog.records)

    def test_tl02_session_usage_accumulates(self):
        """TL02: session_usage 누적 — 2회 호출 후 합산값 확인"""
        from core.llm_pipeline import TokenLogFilter, LLMFilterChain
        from core.llm import TokenUsage

        inner = _make_mock_inner()
        inner.get_last_usage.return_value = TokenUsage(input_tokens=100, output_tokens=50)

        filt = TokenLogFilter()
        chain = LLMFilterChain(filters=[filt], inner=inner)

        chain.generate_json("prompt 1")
        chain.generate_json("prompt 2")

        session = filt.get_session_usage()
        assert session.input_tokens == 200
        assert session.output_tokens == 100

    def test_tl03_from_cache_logged(self, caplog, tmp_path):
        """TL03: from_cache=True 시에도 로그 기록, from_cache 필드 로그 포함
        TokenLogFilter를 SemanticCacheFilter 앞에 배치하면 캐시 히트 시에도 로그가 기록된다.
        """
        import logging
        from core.llm_pipeline import TokenLogFilter, SemanticCacheFilter, LLMFilterChain
        from core.llm_cache import LLMResponseCache
        from core.llm import TokenUsage

        inner = _make_mock_inner()
        cache = LLMResponseCache(base_dir=str(tmp_path))
        cache.put("cached prompt", json.dumps({"cached": True}), TokenUsage(10, 5))

        # TokenLogFilter를 앞에 배치 → 캐시 히트 시에도 로그 기록됨
        filt_log = TokenLogFilter()
        filt_cache = SemanticCacheFilter(cache=cache)
        chain = LLMFilterChain(filters=[filt_log, filt_cache], inner=inner)

        with caplog.at_level(logging.INFO):
            chain.generate_json("cached prompt")

        # 로그에 from_cache 관련 정보 포함 확인
        log_messages = [r.message for r in caplog.records]
        assert any("[TokenLog]" in m for m in log_messages)
        # from_cache=True 가 로그에 포함되었는지 확인
        token_log_msgs = [m for m in log_messages if "[TokenLog]" in m]
        assert any("from_cache=True" in m for m in token_log_msgs)


# ─────────────────────────────────────────────────────────────────────────────
# CH01~CH04: LLMFilterChain
# ─────────────────────────────────────────────────────────────────────────────

class TestLLMFilterChain:
    def test_ch01_filter_order_preserved(self):
        """CH01: 필터 순서 보장 — 실행 순서 기록 후 검증"""
        from core.llm_pipeline import LLMFilter, LLMRequest, LLMResponse, LLMFilterChain
        from core.llm import TokenUsage

        execution_order = []

        class OrderFilter(LLMFilter):
            def __init__(self, name):
                self._name = name

            def process(self, request, chain):
                execution_order.append(self._name)
                return chain.proceed(request)

        inner = _make_mock_inner()
        f1 = OrderFilter("first")
        f2 = OrderFilter("second")
        f3 = OrderFilter("third")

        chain = LLMFilterChain(filters=[f1, f2, f3], inner=inner)
        chain.generate_json("test")

        assert execution_order == ["first", "second", "third"]

    def test_ch02_empty_filter_calls_inner(self):
        """CH02: 필터 없는 체인 → inner.generate_json() 직접 호출"""
        from core.llm_pipeline import LLMFilterChain

        inner = _make_mock_inner()
        chain = LLMFilterChain(filters=[], inner=inner)
        result = chain.generate_json("direct prompt")

        inner.generate_json.assert_called_once()
        assert result == {"result": "ok"}

    def test_ch03_get_last_usage(self):
        """CH03: get_last_usage() — 마지막 LLMResponse.usage 반환"""
        from core.llm_pipeline import LLMFilterChain
        from core.llm import TokenUsage

        inner = _make_mock_inner()
        inner.get_last_usage.return_value = TokenUsage(input_tokens=200, output_tokens=80)

        chain = LLMFilterChain(filters=[], inner=inner)
        chain.generate_json("test prompt")

        usage = chain.get_last_usage()
        assert usage.input_tokens == 200
        assert usage.output_tokens == 80

    def test_ch04_isinstance_base_llm_client(self):
        """CH04: BaseLLMClient 인터페이스 준수 — isinstance(chain, BaseLLMClient) True"""
        from core.llm_pipeline import LLMFilterChain
        from core.llm import BaseLLMClient

        inner = _make_mock_inner()
        chain = LLMFilterChain(filters=[], inner=inner)
        assert isinstance(chain, BaseLLMClient)


# ─────────────────────────────────────────────────────────────────────────────
# INT01~INT05: build_llm_pipeline() 통합 테스트
# ─────────────────────────────────────────────────────────────────────────────

class TestBuildLLMPipeline:
    def test_int01_default_pipeline_has_4_filters(self, monkeypatch):
        """INT01: 기본 파이프라인 생성 — 4개 필터 모두 포함"""
        from core.llm_pipeline import (
            build_llm_pipeline, ModelRoutingFilter, SemanticCacheFilter,
            PromptCacheFilter, TokenLogFilter
        )

        monkeypatch.setenv("LLM_PROVIDER", "gemini")

        with patch("core.llm_pipeline.LLMFactory"):
            pipeline = build_llm_pipeline()

        assert len(pipeline.filters) == 4
        filter_types = [type(f) for f in pipeline.filters]
        assert ModelRoutingFilter in filter_types
        assert SemanticCacheFilter in filter_types
        assert PromptCacheFilter in filter_types
        assert TokenLogFilter in filter_types

    def test_int02_model_routing_false_excludes_routing_filter(self, monkeypatch):
        """INT02: model_routing=False → ModelRoutingFilter 제외"""
        from core.llm_pipeline import build_llm_pipeline, ModelRoutingFilter

        monkeypatch.setenv("LLM_PROVIDER", "gemini")

        with patch("core.llm_pipeline.LLMFactory"):
            pipeline = build_llm_pipeline(model_routing=False)

        filter_types = [type(f) for f in pipeline.filters]
        assert ModelRoutingFilter not in filter_types
        assert len(pipeline.filters) == 3

    def test_int03_semantic_cache_false_excludes_cache_filter(self, monkeypatch):
        """INT03: semantic_cache=False → SemanticCacheFilter 제외"""
        from core.llm_pipeline import build_llm_pipeline, SemanticCacheFilter

        monkeypatch.setenv("LLM_PROVIDER", "gemini")

        with patch("core.llm_pipeline.LLMFactory"):
            pipeline = build_llm_pipeline(semantic_cache=False)

        filter_types = [type(f) for f in pipeline.filters]
        assert SemanticCacheFilter not in filter_types
        assert len(pipeline.filters) == 3

    def test_int04_end_to_end_with_mock_inner(self, monkeypatch, tmp_path):
        """INT04: mock inner로 end-to-end 호출 — metadata={"task_type": "extraction"} 전달 시 정상 응답"""
        from core.llm_pipeline import build_llm_pipeline
        from core.llm import TokenUsage

        monkeypatch.setenv("LLM_PROVIDER", "gemini")
        monkeypatch.setenv("SEMANTIC_CACHE_DIR", str(tmp_path))

        mock_inner = _make_mock_inner(json_response={"jobs": ["Python"]})

        with patch("core.llm_pipeline.LLMFactory") as mock_factory:
            mock_factory.create.return_value = mock_inner
            pipeline = build_llm_pipeline()
            # inner를 직접 교체하여 실제 API 호출 방지
            pipeline._inner = mock_inner

        result = pipeline.generate_json("test prompt", metadata={"task_type": "extraction"})

        assert result == {"jobs": ["Python"]}

    def test_int05_career_agent_integration(self, monkeypatch, tmp_path):
        """INT05: CareerAgent와 통합 (mock llm) — self.llm = build_llm_pipeline() 후 generate_json 호출 성공"""
        from core.llm_pipeline import build_llm_pipeline, LLMFilterChain
        from core.llm import BaseLLMClient, TokenUsage

        monkeypatch.setenv("LLM_PROVIDER", "gemini")
        monkeypatch.setenv("SEMANTIC_CACHE_DIR", str(tmp_path))

        mock_inner = _make_mock_inner(json_response={"status": "ok"})

        with patch("core.llm_pipeline.LLMFactory") as mock_factory:
            mock_factory.create.return_value = mock_inner
            pipeline = build_llm_pipeline()
            pipeline._inner = mock_inner

        # pipeline이 BaseLLMClient 구현체인지 확인
        assert isinstance(pipeline, BaseLLMClient)
        assert isinstance(pipeline, LLMFilterChain)

        # generate_json 호출 성공 확인
        result = pipeline.generate_json("career analysis prompt", metadata={"task_type": "analysis"})
        assert result is not None
        assert isinstance(result, dict)
