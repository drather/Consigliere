import os
import json
from typing import Dict, Any, Optional
from abc import ABC, abstractmethod
from core.logger import get_logger

logger = get_logger(__name__)

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
        self.model_name = os.getenv("GEMINI_MODEL", "gemini-3-flash-preview")
        self.thinking_level = os.getenv("GEMINI_THINKING_LEVEL", "low")
        if not self.api_key:
            logger.warning("GEMINI_API_KEY not found. Gemini LLM features will fail.")
        else:
            from google import genai
            self.client = genai.Client(api_key=self.api_key)
            logger.info(f"Gemini LLM Client initialized. Model: {self.model_name}, Thinking: {self.thinking_level}")

    def _make_config(self, extra: Optional[Dict[str, Any]] = None):
        from google.genai import types
        thinking = types.ThinkingConfig(thinking_level=self.thinking_level)
        kwargs = {"thinking_config": thinking}
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
            return json.loads(response.text)
        except Exception as e:
            logger.error(f"Gemini LLM JSON Error: {e}")
            try:
                import re
                match = re.search(r"\{.*\}", str(e), re.DOTALL)
                if match:
                    return json.loads(match.group(0))
            except Exception:
                pass
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
            # Strip potential markdown code fences
            import re
            raw = re.sub(r"^```(?:json)?\s*", "", raw, flags=re.MULTILINE)
            raw = re.sub(r"```\s*$", "", raw, flags=re.MULTILINE).strip()
            # Extract JSON boundaries — handle both object {...} and array [...]
            obj_start = raw.find('{')
            arr_start = raw.find('[')
            # Pick whichever comes first (and exists)
            if obj_start == -1 and arr_start == -1:
                pass  # fall through to json.loads which will raise
            elif arr_start != -1 and (obj_start == -1 or arr_start < obj_start):
                end = raw.rfind(']')
                if end != -1:
                    raw = raw[arr_start:end + 1]
            else:
                end = raw.rfind('}')
                if end != -1:
                    raw = raw[obj_start:end + 1]
            return json.loads(raw)
        except json.JSONDecodeError as e:
            logger.error(f"Claude LLM JSON Parse Error: {e}. Raw output saved.")
            return {"error": str(e)}
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
