import os
import re
import json
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, Any, Optional, List
from abc import ABC, abstractmethod
from core.logger import get_logger

logger = get_logger(__name__)


# ─────────────────────────────────────────────────────────────────────────────
# Token Observability
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class TokenUsage:
    """LLM 호출 1회의 토큰 사용량."""
    input_tokens: int = 0
    output_tokens: int = 0
    cached_input_tokens: int = 0  # Claude prompt cache read tokens

    @property
    def total_tokens(self) -> int:
        return self.input_tokens + self.output_tokens

    def __add__(self, other: "TokenUsage") -> "TokenUsage":
        return TokenUsage(
            self.input_tokens + other.input_tokens,
            self.output_tokens + other.output_tokens,
            self.cached_input_tokens + other.cached_input_tokens,
        )


# ─────────────────────────────────────────────────────────────────────────────
# Model Routing
# ─────────────────────────────────────────────────────────────────────────────

class TaskType(str, Enum):
    ANALYSIS   = "analysis"    # 복잡한 추론 → sonnet-4-6
    EXTRACTION = "extraction"  # 구조화 JSON 추출 → haiku-4-5
    SYNTHESIS  = "synthesis"   # 긴 리포트 생성 → sonnet-4-6


# ─────────────────────────────────────────────────────────────────────────────
# JSON 파싱 유틸리티
# ─────────────────────────────────────────────────────────────────────────────

def _parse_json_robust(raw: str, log, provider: str = "LLM") -> Dict[str, Any]:
    """
    LLM 응답에서 JSON을 안정적으로 파싱한다.

    시도 순서:
    1. 마크다운 펜스 제거 후 json.loads (가장 빠름)
    2. outermost JSON 경계 추출 후 json.loads
    3. 문자열 내 제어문자 이스케이프 후 json.loads
    4. json_repair 라이브러리로 복구 후 json.loads (가장 강력)
    """
    # ── 단계 1: 마크다운 펜스 제거 ──────────────────────────────────────
    cleaned = re.sub(r"^```(?:json)?\s*", "", raw, flags=re.MULTILINE)
    cleaned = re.sub(r"```\s*$", "", cleaned, flags=re.MULTILINE).strip()

    # ── 단계 2: outermost {} or [] 추출 ──────────────────────────────
    obj_start, arr_start = cleaned.find("{"), cleaned.find("[")
    if obj_start != -1 or arr_start != -1:
        if arr_start != -1 and (obj_start == -1 or arr_start < obj_start):
            end = cleaned.rfind("]")
            if end != -1:
                cleaned = cleaned[arr_start:end + 1]
        else:
            end = cleaned.rfind("}")
            if end != -1:
                cleaned = cleaned[obj_start:end + 1]

    # ── 단계 3: 직접 파싱 시도 ──────────────────────────────────────
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        pass

    # ── 단계 4: 문자열 내 제어문자 이스케이프 ─────────────────────────
    fixed, in_string, escape_next = "", False, False
    for ch in cleaned:
        if escape_next:
            fixed += ch; escape_next = False
        elif ch == "\\":
            fixed += ch; escape_next = True
        elif ch == '"':
            fixed += ch; in_string = not in_string
        elif in_string and ch == "\n":
            fixed += "\\n"
        elif in_string and ch == "\r":
            fixed += "\\r"
        elif in_string and ch == "\t":
            fixed += "\\t"
        elif in_string and ord(ch) < 0x20:
            fixed += f"\\u{ord(ch):04x}"
        else:
            fixed += ch

    try:
        return json.loads(fixed)
    except json.JSONDecodeError:
        pass

    # ── 단계 5: json_repair 로 복구 ─────────────────────────────────
    try:
        from json_repair import repair_json
        repaired = repair_json(cleaned, return_objects=True)
        if isinstance(repaired, (dict, list)):
            log.warning(f"{provider} LLM JSON was repaired by json_repair. First 200 chars of raw: {cleaned[:200]!r}")
            return repaired
        return json.loads(repair_json(cleaned))
    except Exception as e:
        log.error(f"{provider} LLM JSON repair failed: {e}. Raw (first 300): {cleaned[:300]!r}")
        return {"error": str(e)}


# ─────────────────────────────────────────────────────────────────────────────
# Abstract Base
# ─────────────────────────────────────────────────────────────────────────────

class BaseLLMClient(ABC):
    """
    Abstract Base Class for LLM providers.
    All models (Gemini, Claude, GPT) must strictly implement these interfaces.
    """
    @abstractmethod
    def generate(self, prompt: str) -> str:
        pass

    @abstractmethod
    def generate_json(self, prompt: str, max_tokens: int = 8192) -> Dict[str, Any]:
        pass

    def get_last_usage(self) -> TokenUsage:
        """마지막 LLM 호출의 토큰 사용량 반환. 서브클래스에서 override."""
        return TokenUsage()


# ─────────────────────────────────────────────────────────────────────────────
# Gemini Client
# ─────────────────────────────────────────────────────────────────────────────

class GeminiClient(BaseLLMClient):
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("GEMINI_API_KEY")
        self.model_name = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
        self.thinking_level = os.getenv("GEMINI_THINKING_LEVEL", "low")
        self._last_usage = TokenUsage()
        if not self.api_key:
            logger.warning("GEMINI_API_KEY not found. Gemini LLM features will fail.")
        else:
            from google import genai
            self.client = genai.Client(api_key=self.api_key)
            logger.info(f"Gemini LLM Client initialized. Model: {self.model_name}, Thinking: {self.thinking_level}")

    def _make_config(self, extra: Optional[Dict[str, Any]] = None):
        from google.genai import types
        kwargs = {}
        # Only attach ThinkingConfig when thinking is explicitly enabled
        if self.thinking_level and self.thinking_level.lower() not in ("none", "off", ""):
            kwargs["thinking_config"] = types.ThinkingConfig(thinking_level=self.thinking_level)
        if extra:
            kwargs.update(extra)
        return types.GenerateContentConfig(**kwargs)

    def _record_usage(self, response) -> None:
        meta = getattr(response, "usage_metadata", None)
        if meta:
            self._last_usage = TokenUsage(
                input_tokens=getattr(meta, "prompt_token_count", 0),
                output_tokens=getattr(meta, "candidates_token_count", 0),
            )
            logger.info(
                "[Gemini] usage: in=%d out=%d",
                self._last_usage.input_tokens,
                self._last_usage.output_tokens,
            )

    def generate(self, prompt: str) -> str:
        if not self.api_key:
            return "[Error: Missing API Key]"
        try:
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=prompt,
                config=self._make_config(),
            )
            self._record_usage(response)
            return response.text
        except Exception as e:
            logger.error(f"Gemini LLM Error: {e}")
            return str(e)

    def generate_json(self, prompt: str, max_tokens: int = 8192) -> Dict[str, Any]:
        if not self.api_key:
            return {"error": "Missing API Key"}
        try:
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=prompt,
                config=self._make_config({
                    "response_mime_type": "application/json",
                    "max_output_tokens": max_tokens,
                }),
            )
            self._record_usage(response)
            raw = response.text.strip()
            return _parse_json_robust(raw, logger, "Gemini")
        except Exception as e:
            logger.error(f"Gemini LLM JSON Error: {e}")
            return {"error": str(e)}

    def get_last_usage(self) -> TokenUsage:
        return self._last_usage


# ─────────────────────────────────────────────────────────────────────────────
# Claude Client
# ─────────────────────────────────────────────────────────────────────────────

class ClaudeClient(BaseLLMClient):
    def __init__(self, api_key: Optional[str] = None, model_override: Optional[str] = None):
        self.api_key = api_key or os.getenv("ANTHROPIC_API_KEY")
        self.model_name = model_override or os.getenv("CLAUDE_MODEL", "claude-sonnet-4-6")
        self._last_usage = TokenUsage()
        if not self.api_key:
            logger.warning("ANTHROPIC_API_KEY not found. Claude LLM features will fail.")
        else:
            import anthropic
            self.client = anthropic.Anthropic(api_key=self.api_key)
            logger.info(f"Claude LLM Client initialized. Model: {self.model_name}")

    def _record_usage(self, message) -> None:
        usage = getattr(message, "usage", None)
        if usage:
            self._last_usage = TokenUsage(
                input_tokens=getattr(usage, "input_tokens", 0),
                output_tokens=getattr(usage, "output_tokens", 0),
                cached_input_tokens=getattr(usage, "cache_read_input_tokens", 0),
            )
            logger.info(
                "[Claude] usage: in=%d out=%d cached=%d",
                self._last_usage.input_tokens,
                self._last_usage.output_tokens,
                self._last_usage.cached_input_tokens,
            )

    def generate(self, prompt: str) -> str:
        if not self.api_key:
            return "[Error: Missing Claude API Key]"
        try:
            message = self.client.messages.create(
                model=self.model_name,
                max_tokens=4096,
                messages=[{"role": "user", "content": prompt}]
            )
            self._record_usage(message)
            return message.content[0].text
        except Exception as e:
            logger.error(f"Claude LLM Error: {e}")
            return str(e)

    def generate_json(self, prompt: str, max_tokens: int = 8192) -> Dict[str, Any]:
        if not self.api_key:
            return {"error": "Missing Claude API Key"}
        try:
            full_prompt = f"{prompt}\n\nIMPORTANT: You MUST respond with ONLY a valid JSON object or JSON array. No markdown formatting, no ```json blocks, no explanation text. Just raw JSON."
            message = self.client.messages.create(
                model=self.model_name,
                max_tokens=max_tokens,
                messages=[{"role": "user", "content": full_prompt}]
            )
            self._record_usage(message)
            raw = message.content[0].text.strip()
            return _parse_json_robust(raw, logger, "Claude")
        except Exception as e:
            logger.error(f"Claude LLM JSON Error: {e}")
            return {"error": str(e)}

    def generate_with_cache(
        self,
        static_prompt: str,
        dynamic_prompt: str,
        max_tokens: int = 4096,
    ) -> str:
        """Static 부분에 cache_control을 붙여 Claude prompt cache를 활용한다."""
        if not self.api_key:
            return "[Error: Missing Claude API Key]"
        try:
            content_blocks: List[Dict[str, Any]] = []
            if static_prompt:
                content_blocks.append({
                    "type": "text",
                    "text": static_prompt,
                    "cache_control": {"type": "ephemeral"},
                })
            if dynamic_prompt:
                content_blocks.append({"type": "text", "text": dynamic_prompt})

            if not content_blocks:
                return "[Error: empty prompt]"

            message = self.client.messages.create(
                model=self.model_name,
                max_tokens=max_tokens,
                messages=[{"role": "user", "content": content_blocks}],
                extra_headers={"anthropic-beta": "prompt-caching-2024-07-31"},
            )
            self._record_usage(message)
            return message.content[0].text
        except Exception as e:
            logger.error(f"Claude LLM (cache) Error: {e}")
            return str(e)

    def generate_json_with_cache(
        self,
        static_prompt: str,
        dynamic_prompt: str,
        max_tokens: int = 8192,
    ) -> Dict[str, Any]:
        """generate_with_cache의 JSON 출력 버전."""
        if not self.api_key:
            return {"error": "Missing Claude API Key"}
        try:
            json_instruction = "\n\nIMPORTANT: You MUST respond with ONLY a valid JSON object or JSON array. No markdown formatting, no ```json blocks, no explanation text. Just raw JSON."
            full_dynamic = (dynamic_prompt or "") + json_instruction
            raw = self.generate_with_cache(static_prompt, full_dynamic, max_tokens)
            return _parse_json_robust(raw.strip(), logger, "Claude")
        except Exception as e:
            logger.error(f"Claude LLM JSON (cache) Error: {e}")
            return {"error": str(e)}

    def get_last_usage(self) -> TokenUsage:
        return self._last_usage


# ─────────────────────────────────────────────────────────────────────────────
# LLM Factory (Model Routing 포함)
# ─────────────────────────────────────────────────────────────────────────────

class LLMFactory:
    """
    Returns the appropriate LLMClient based on the environment variables.
    task_type을 지정하면 작업 유형에 최적화된 모델을 반환한다.
    """
    _CLAUDE_MODEL_ENV_MAP = {
        TaskType.ANALYSIS:   ("CLAUDE_ANALYSIS_MODEL",   "claude-sonnet-4-6"),
        TaskType.EXTRACTION: ("CLAUDE_EXTRACTION_MODEL", "claude-haiku-4-5"),
        TaskType.SYNTHESIS:  ("CLAUDE_SYNTHESIS_MODEL",  "claude-sonnet-4-6"),
    }

    @staticmethod
    def create(task_type: Optional[TaskType] = None) -> BaseLLMClient:
        provider = os.getenv("LLM_PROVIDER", "gemini").lower()
        if provider == "claude":
            if task_type is None:
                logger.info("Initializing Claude LLM Client.")
                return ClaudeClient()
            env_key, default_model = LLMFactory._CLAUDE_MODEL_ENV_MAP[task_type]
            model = os.getenv(env_key, default_model)
            logger.info(f"Initializing Claude LLM Client. task_type={task_type}, model={model}")
            return ClaudeClient(model_override=model)

        # Default: Gemini
        logger.info("Initializing Gemini LLM Client.")
        return GeminiClient()


# Backward compatibility alias (to avoid breaking legacy code immediately)
LLMClient = LLMFactory.create
