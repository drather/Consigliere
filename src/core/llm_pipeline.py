"""
LLM Filter Chain — Filter Chain 패턴으로 LLM 최적화 관심사를 분리한다.

설계:
  LLMFilter (ABC)        — process(request, chain) 추상 메서드
  LLMRequest             — 요청 데이터클래스 (prompt, metadata, static_prompt 등)
  LLMResponse            — 응답 데이터클래스 (data, usage, from_cache, model_used)
  LLMFilterChain         — 필터 체인 실행 엔진 (BaseLLMClient 구현)
  ModelRoutingFilter     — task_type 기반 모델 선택
  SemanticCacheFilter    — SHA256(prompt) 파일 캐시
  PromptCacheFilter      — Claude prompt cache_control 적용
  TokenLogFilter         — 호출 후 토큰 사용량 로깅
  build_llm_pipeline()   — 파이프라인 팩토리 함수
"""
import json
import os
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional

from core.llm import BaseLLMClient, LLMFactory, TaskType, TokenUsage
from core.llm_cache import LLMResponseCache
from core.logger import get_logger

logger = get_logger(__name__)


# ─────────────────────────────────────────────────────────────────────────────
# 데이터클래스
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class LLMRequest:
    """LLM 파이프라인 요청 데이터."""
    prompt: str
    max_tokens: int = 8192
    metadata: Dict[str, Any] = field(default_factory=dict)
    static_prompt: Optional[str] = None
    dynamic_prompt: Optional[str] = None
    # 내부 필드: ModelRoutingFilter가 선택한 클라이언트 (request 스코프)
    _routed_client: Optional[BaseLLMClient] = field(default=None, repr=False)


@dataclass
class LLMResponse:
    """LLM 파이프라인 응답 데이터."""
    data: Dict[str, Any]
    usage: TokenUsage
    model_used: str
    from_cache: bool = False


# ─────────────────────────────────────────────────────────────────────────────
# Abstract Filter
# ─────────────────────────────────────────────────────────────────────────────

class LLMFilter(ABC):
    """
    LLM 파이프라인 필터 인터페이스.

    chain.proceed(request)를 호출하면 다음 필터로 이동한다.
    캐시 히트 등의 경우 proceed()를 호출하지 않고 즉시 반환할 수 있다.
    """

    @abstractmethod
    def process(self, request: LLMRequest, chain: "LLMFilterChain") -> LLMResponse:
        pass


# ─────────────────────────────────────────────────────────────────────────────
# LLMFilterChain — 체인 실행 엔진 (BaseLLMClient 구현)
# ─────────────────────────────────────────────────────────────────────────────

class LLMFilterChain(BaseLLMClient):
    """
    필터 체인 실행 엔진.

    BaseLLMClient를 구현하므로 기존 self.llm 할당 지점에서 투명하게 교체된다.
    generate_json() → LLMRequest 생성 → proceed() → 필터 순차 실행 → inner API 호출.
    """

    def __init__(self, filters: List[LLMFilter], inner: BaseLLMClient):
        self.filters = filters
        self._inner = inner
        self._index = 0
        self._last_response: Optional[LLMResponse] = None

    def proceed(self, request: LLMRequest) -> LLMResponse:
        """현재 인덱스의 필터를 호출하고 인덱스를 증가시킨다. 필터 소진 시 실제 API 호출."""
        if self._index < len(self.filters):
            current = self.filters[self._index]
            self._index += 1
            return current.process(request, self)

        # 모든 필터 소진 → 실제 API 호출
        return self._call_inner(request)

    def _call_inner(self, request: LLMRequest) -> LLMResponse:
        """실제 LLM API 호출. ModelRoutingFilter가 선택한 클라이언트 우선 사용.

        PromptCacheFilter가 static_prompt를 처리하므로 여기서는 prompt 전문(full prompt)만 사용한다.
        """
        client = request._routed_client or self._inner
        data = client.generate_json(request.prompt, max_tokens=request.max_tokens)
        usage = client.get_last_usage()
        model_used = getattr(client, "model_name", "unknown")
        return LLMResponse(data=data, usage=usage, model_used=model_used)

    def generate(self, prompt: str) -> str:
        """BaseLLMClient 인터페이스 구현 (텍스트 반환)."""
        return self._inner.generate(prompt)

    def generate_json(
        self,
        prompt: str,
        max_tokens: int = 8192,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """BaseLLMClient 인터페이스 구현 — 파이프라인 진입점."""
        request = LLMRequest(
            prompt=prompt,
            max_tokens=max_tokens,
            metadata=metadata or {},
        )
        self._index = 0  # 매 호출마다 인덱스 초기화
        response = self.proceed(request)
        self._last_response = response
        return response.data

    def get_last_usage(self) -> TokenUsage:
        """마지막 LLMResponse.usage 반환."""
        if self._last_response is not None:
            return self._last_response.usage
        return TokenUsage()


# ─────────────────────────────────────────────────────────────────────────────
# Filter 1: ModelRoutingFilter
# ─────────────────────────────────────────────────────────────────────────────

class ModelRoutingFilter(LLMFilter):
    """
    task_type 기반 모델 선택 필터.

    - Claude provider: task_type → LLMFactory.create(TaskType[...]) 호출
    - Gemini provider: no-op (단일 모델)
    - task_type 없음: inner client 그대로 사용
    결과로 생성된 client를 request._routed_client에 저장하여 이후 필터에 전달한다.
    """

    def process(self, request: LLMRequest, chain: LLMFilterChain) -> LLMResponse:
        provider = os.getenv("LLM_PROVIDER", "gemini").lower()
        task_type_str = request.metadata.get("task_type")

        if provider == "claude" and task_type_str:
            try:
                task_type = TaskType[task_type_str.upper()]
                routed_client = LLMFactory.create(task_type=task_type)
                request._routed_client = routed_client
                logger.debug(
                    "[ModelRoutingFilter] task_type=%s → model=%s",
                    task_type_str,
                    getattr(routed_client, "model_name", "unknown"),
                )
            except (KeyError, ValueError) as e:
                logger.warning("[ModelRoutingFilter] 알 수 없는 task_type=%s: %s", task_type_str, e)

        # Gemini or no task_type: pass-through
        return chain.proceed(request)


# ─────────────────────────────────────────────────────────────────────────────
# Filter 2: SemanticCacheFilter
# ─────────────────────────────────────────────────────────────────────────────

class SemanticCacheFilter(LLMFilter):
    """
    SHA256(prompt) 기반 파일 캐시 필터.

    - 캐시 히트: chain.proceed() 미호출, LLMResponse(from_cache=True) 즉시 반환
    - 캐시 미스: proceed() 결과를 캐시에 저장 후 반환
    - TTL: metadata["ttl"] > SEMANTIC_CACHE_TTL_SECONDS > 86400 순으로 우선 적용
    """

    DEFAULT_TTL = int(os.getenv("SEMANTIC_CACHE_TTL_SECONDS", "86400"))

    def __init__(self, cache: Optional[LLMResponseCache] = None):
        cache_dir = os.getenv("SEMANTIC_CACHE_DIR", "data/llm_cache")
        self._cache = cache or LLMResponseCache(base_dir=cache_dir)

    def process(self, request: LLMRequest, chain: LLMFilterChain) -> LLMResponse:
        ttl = int(request.metadata.get("ttl", self.DEFAULT_TTL))
        entry = self._cache.get(request.prompt, ttl)

        if entry is not None:
            logger.debug("[SemanticCacheFilter] HIT prompt_prefix=%s", request.prompt[:30])
            try:
                data = json.loads(entry.response)
            except json.JSONDecodeError:
                data = {"raw": entry.response}
            return LLMResponse(
                data=data,
                usage=TokenUsage(entry.input_tokens, entry.output_tokens),
                model_used="cache",
                from_cache=True,
            )

        # 캐시 미스 → 다음 필터로 진행
        response = chain.proceed(request)

        # 결과를 캐시에 저장 (에러 응답은 캐시하지 않음)
        if "error" not in response.data:
            try:
                self._cache.put(
                    request.prompt,
                    json.dumps(response.data, ensure_ascii=False),
                    response.usage,
                )
            except Exception as e:
                logger.warning("[SemanticCacheFilter] 캐시 저장 실패: %s", e)
        else:
            logger.warning("[SemanticCacheFilter] 에러 응답은 캐시 저장 건너뜀: %s", list(response.data.keys()))

        return response


# ─────────────────────────────────────────────────────────────────────────────
# Filter 3: PromptCacheFilter
# ─────────────────────────────────────────────────────────────────────────────

class PromptCacheFilter(LLMFilter):
    """
    Claude Prompt Cache (cache_control: ephemeral) 적용 필터.

    - request.static_prompt가 있고 Claude provider → generate_json_with_cache() 사용
    - Gemini provider → no-op (pass-through)
    - cache_boundary 없음 → no-op
    """

    def process(self, request: LLMRequest, chain: LLMFilterChain) -> LLMResponse:
        provider = os.getenv("LLM_PROVIDER", "gemini").lower()

        # Gemini: no-op
        if provider != "claude":
            return chain.proceed(request)

        # static_prompt가 분리되어 있으면 Claude prompt cache 경로 사용
        if request.static_prompt is not None:
            client = request._routed_client or chain._inner
            if hasattr(client, "generate_json_with_cache"):
                data = client.generate_json_with_cache(
                    request.static_prompt,
                    request.dynamic_prompt or "",
                    max_tokens=request.max_tokens,
                )
                usage = client.get_last_usage()
                model_used = getattr(client, "model_name", "unknown")
                return LLMResponse(data=data, usage=usage, model_used=model_used)

        # static_prompt 없음 → no-op
        return chain.proceed(request)


# ─────────────────────────────────────────────────────────────────────────────
# Filter 4: TokenLogFilter
# ─────────────────────────────────────────────────────────────────────────────

class TokenLogFilter(LLMFilter):
    """
    토큰 사용량 구조화 로깅 필터.

    - chain.proceed() 후 response.usage를 로깅한다.
    - session_usage: 세션 내 누적 토큰 카운터
    - 비즈니스 로직에 영향을 주지 않으며 response를 그대로 반환한다.
    """

    def __init__(self):
        self._session_usage = TokenUsage()

    def process(self, request: LLMRequest, chain: LLMFilterChain) -> LLMResponse:
        response = chain.proceed(request)

        task_type = request.metadata.get("task_type", "unknown")
        logger.info(
            "[TokenLog] task_type=%s model=%s in=%d out=%d cached=%d from_cache=%s",
            task_type,
            response.model_used,
            response.usage.input_tokens,
            response.usage.output_tokens,
            response.usage.cached_input_tokens,
            response.from_cache,
        )

        self._session_usage = self._session_usage + response.usage
        return response

    def get_session_usage(self) -> TokenUsage:
        """세션 내 누적 토큰 사용량 반환."""
        return self._session_usage


# ─────────────────────────────────────────────────────────────────────────────
# 팩토리 함수
# ─────────────────────────────────────────────────────────────────────────────

def build_llm_pipeline(
    token_log: bool = True,
    semantic_cache: bool = True,
    prompt_cache: bool = True,
    model_routing: bool = True,
) -> LLMFilterChain:
    """
    LLM 파이프라인 팩토리 함수.

    기본 필터 순서: ModelRoutingFilter → SemanticCacheFilter → PromptCacheFilter → TokenLogFilter

    Args:
        token_log: TokenLogFilter 활성화 여부 (기본 True)
        semantic_cache: SemanticCacheFilter 활성화 여부 (기본 True)
        prompt_cache: PromptCacheFilter 활성화 여부 (기본 True)
        model_routing: ModelRoutingFilter 활성화 여부 (기본 True)

    환경변수:
        LLM_PIPELINE_FILTERS: 콤마 구분 필터 이름으로 활성 필터 override
            예) "model_routing,token_log" → 2개 필터만 활성화
    """
    # 환경변수로 필터 override 지원
    env_filters = os.getenv("LLM_PIPELINE_FILTERS", "").strip()
    if env_filters:
        enabled = {f.strip().lower() for f in env_filters.split(",")}
        model_routing = "model_routing" in enabled
        semantic_cache = "semantic_cache" in enabled
        prompt_cache = "prompt_cache" in enabled
        token_log = "token_log" in enabled

    filters: List[LLMFilter] = []

    if model_routing:
        filters.append(ModelRoutingFilter())

    if semantic_cache:
        cache_dir = os.getenv("SEMANTIC_CACHE_DIR", "data/llm_cache")
        filters.append(SemanticCacheFilter(cache=LLMResponseCache(base_dir=cache_dir)))

    if prompt_cache:
        filters.append(PromptCacheFilter())

    if token_log:
        filters.append(TokenLogFilter())

    inner = LLMFactory.create()
    logger.info(
        "[build_llm_pipeline] filters=%s inner=%s",
        [type(f).__name__ for f in filters],
        getattr(inner, "model_name", type(inner).__name__),
    )

    return LLMFilterChain(filters=filters, inner=inner)
