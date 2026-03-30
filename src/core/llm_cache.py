"""
LLM Response Cache — 프롬프트 → 응답 파일 기반 캐시.

설계:
  - CacheEntry: 캐시 항목 (응답, 타임스탬프, 토큰 수)
  - LLMResponseCache: SHA256(prompt) → data/llm_cache/{hash[:2]}/{hash}.json
  - CachedLLMClient: BaseLLMClient를 감싸는 Decorator (OCP 원칙)
"""
import hashlib
import json
import os
import time
from dataclasses import dataclass
from typing import Dict, Any, Optional

from core.llm import BaseLLMClient, TokenUsage
from core.logger import get_logger

logger = get_logger(__name__)


@dataclass
class CacheEntry:
    response: str          # raw text 또는 JSON 문자열
    created_at: float      # unix timestamp
    input_tokens: int = 0
    output_tokens: int = 0


class LLMResponseCache:
    """
    파일 기반 LLM 응답 캐시.

    캐시 키: SHA256(prompt_text)
    저장 경로: {base_dir}/{hash[:2]}/{hash}.json
    TTL: 호출별로 지정 (초 단위)
    """

    def __init__(self, base_dir: str = "data/llm_cache"):
        self.base_dir = base_dir

    def _key(self, prompt: str) -> str:
        return hashlib.sha256(prompt.encode("utf-8")).hexdigest()

    def _path(self, key: str) -> str:
        return os.path.join(self.base_dir, key[:2], f"{key}.json")

    def get(self, prompt: str, ttl_seconds: int) -> Optional[CacheEntry]:
        """캐시에서 항목을 조회한다. TTL 초과 시 None 반환."""
        key = self._key(prompt)
        path = self._path(key)
        if not os.path.exists(path):
            return None
        try:
            with open(path, encoding="utf-8") as f:
                data = json.load(f)
            entry = CacheEntry(**data)
            if time.time() - entry.created_at > ttl_seconds:
                logger.debug("[LLMCache] EXPIRED key=%s", key[:8])
                return None
            logger.debug("[LLMCache] HIT key=%s", key[:8])
            return entry
        except Exception as e:
            logger.warning("[LLMCache] 읽기 실패 (key=%s): %s", key[:8], e)
            return None

    def put(self, prompt: str, response: str, usage: TokenUsage) -> None:
        """응답을 캐시에 저장한다."""
        key = self._key(prompt)
        path = self._path(key)
        try:
            os.makedirs(os.path.dirname(path), exist_ok=True)
            entry = CacheEntry(
                response=response,
                created_at=time.time(),
                input_tokens=usage.input_tokens,
                output_tokens=usage.output_tokens,
            )
            with open(path, "w", encoding="utf-8") as f:
                json.dump(entry.__dict__, f, ensure_ascii=False)
            logger.debug("[LLMCache] STORED key=%s", key[:8])
        except Exception as e:
            logger.warning("[LLMCache] 저장 실패 (key=%s): %s", key[:8], e)

    def invalidate(self, prompt: str) -> bool:
        """캐시 항목을 삭제한다. 삭제 성공 시 True, 존재하지 않으면 False."""
        path = self._path(self._key(prompt))
        if os.path.exists(path):
            os.remove(path)
            return True
        return False


class CachedLLMClient(BaseLLMClient):
    """
    BaseLLMClient를 감싸는 Decorator 패턴 캐싱 레이어.

    동일한 프롬프트의 응답을 TTL 이내에 재사용한다.
    cache miss 시에는 inner client를 호출하고 결과를 캐시에 저장한다.
    """

    def __init__(
        self,
        inner: BaseLLMClient,
        cache: LLMResponseCache,
        ttl_seconds: int = 86400,
    ):
        self._inner = inner
        self._cache = cache
        self._ttl = ttl_seconds
        self._last_usage = TokenUsage()

    def generate(self, prompt: str) -> str:
        entry = self._cache.get(prompt, self._ttl)
        if entry:
            self._last_usage = TokenUsage(entry.input_tokens, entry.output_tokens)
            return entry.response

        response = self._inner.generate(prompt)
        self._cache.put(prompt, response, self._inner.get_last_usage())
        self._last_usage = self._inner.get_last_usage()
        return response

    def generate_json(self, prompt: str, max_tokens: int = 8192) -> Dict[str, Any]:
        entry = self._cache.get(prompt, self._ttl)
        if entry:
            self._last_usage = TokenUsage(entry.input_tokens, entry.output_tokens)
            try:
                return json.loads(entry.response)
            except json.JSONDecodeError:
                pass  # 캐시 항목이 손상된 경우 재생성

        result = self._inner.generate_json(prompt, max_tokens)
        self._cache.put(prompt, json.dumps(result, ensure_ascii=False), self._inner.get_last_usage())
        self._last_usage = self._inner.get_last_usage()
        return result

    def get_last_usage(self) -> TokenUsage:
        return self._last_usage
