import os
import re
import json
from typing import Dict, Any, Optional
from abc import ABC, abstractmethod
from core.logger import get_logger

logger = get_logger(__name__)


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

class GeminiClient(BaseLLMClient):
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("GEMINI_API_KEY")
        self.model_name = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
        self.thinking_level = os.getenv("GEMINI_THINKING_LEVEL", "low")
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

    def generate(self, prompt: str) -> str:
        if not self.api_key:
            return "[Error: Missing API Key]"
        try:
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=prompt,
                config=self._make_config(),
            )
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
            raw = response.text.strip()
            return _parse_json_robust(raw, logger, "Gemini")
        except Exception as e:
            logger.error(f"Gemini LLM JSON Error: {e}")
            return {"error": str(e)}

class ClaudeClient(BaseLLMClient):
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("ANTHROPIC_API_KEY")
        self.model_name = os.getenv("CLAUDE_MODEL", "claude-sonnet-4-6")
        if not self.api_key:
            logger.warning("ANTHROPIC_API_KEY not found. Claude LLM features will fail.")
        else:
            import anthropic
            self.client = anthropic.Anthropic(api_key=self.api_key)
            logger.info(f"Claude LLM Client initialized. Model: {self.model_name}")

    def generate(self, prompt: str) -> str:
        if not self.api_key:
            return "[Error: Missing Claude API Key]"
        try:
            message = self.client.messages.create(
                model=self.model_name,
                max_tokens=4096,
                messages=[{"role": "user", "content": prompt}]
            )
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
            raw = message.content[0].text.strip()
            return _parse_json_robust(raw, logger, "Claude")
        except Exception as e:
            logger.error(f"Claude LLM JSON Error: {e}")
            return {"error": str(e)}


class LLMFactory:
    """
    Returns the appropriate LLMClient based on the environment variables.
    """
    @staticmethod
    def create() -> BaseLLMClient:
        provider = os.getenv("LLM_PROVIDER", "gemini").lower()
        if provider == "claude":
            logger.info("Initializing Claude LLM Client.")
            return ClaudeClient()
        
        # Default
        logger.info("Initializing Gemini LLM Client.")
        return GeminiClient()

# Backward compatibility alias (to avoid breaking legacy code immediately)
LLMClient = LLMFactory.create
