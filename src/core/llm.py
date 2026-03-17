import os
import json
from typing import Dict, Any, Optional
from abc import ABC, abstractmethod
import google.generativeai as genai
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
    def generate_json(self, prompt: str) -> Dict[str, Any]:
        pass

class GeminiClient(BaseLLMClient):
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("GEMINI_API_KEY")
        if not self.api_key:
            logger.warning("GEMINI_API_KEY not found. Gemini LLM features will fail.")
        else:
            genai.configure(api_key=self.api_key)
            self.model = genai.GenerativeModel('gemini-2.5-flash')

    def generate(self, prompt: str) -> str:
        if not self.api_key:
            return "[Error: Missing API Key]"
        try:
            response = self.model.generate_content(prompt)
            return response.text
        except Exception as e:
            logger.error(f"Gemini LLM Error: {e}")
            return str(e)

    def generate_json(self, prompt: str) -> Dict[str, Any]:
        if not self.api_key:
            return {"error": "Missing API Key"}
        try:
            response = self.model.generate_content(
                prompt,
                generation_config={"response_mime_type": "application/json"}
            )
            return json.loads(response.text)
        except Exception as e:
            logger.error(f"Gemini LLM JSON Error: {e}")
            try:
                import re
                match = re.search(r"\{.*\}", str(e), re.DOTALL)
                if match:
                    return json.loads(match.group(0))
            except:
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

    def generate_json(self, prompt: str) -> Dict[str, Any]:
        if not self.api_key:
            return {"error": "Missing Claude API Key"}
        try:
            full_prompt = f"{prompt}\n\nIMPORTANT: You MUST respond with ONLY a valid JSON object or JSON array. No markdown formatting, no ```json blocks, no explanation text. Just raw JSON."
            message = self.client.messages.create(
                model=self.model_name,
                max_tokens=4096,
                messages=[{"role": "user", "content": full_prompt}]
            )
            raw = message.content[0].text.strip()
            # Strip potential markdown code fences
            import re
            raw = re.sub(r"^```(?:json)?\s*", "", raw, flags=re.MULTILINE)
            raw = re.sub(r"```\s*$", "", raw, flags=re.MULTILINE).strip()
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
