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
        if not self.api_key:
            logger.warning("ANTHROPIC_API_KEY not found. Claude LLM features will fail.")

    def generate(self, prompt: str) -> str:
        if not self.api_key:
            return "[Error: Missing Claude API Key]"
        # TODO: Implement actual anthropic library call
        logger.info("[Claude] Generate text placeholder called.")
        return "This is a dummy response from ClaudeClient. Real implementation requires 'anthropic' package."

    def generate_json(self, prompt: str) -> Dict[str, Any]:
        if not self.api_key:
            return {"error": "Missing Claude API Key"}
        # TODO: Implement actual anthropic library JSON call
        logger.info("[Claude] Generate JSON placeholder called.")
        return {"response": "This is a dummy JSON response from ClaudeClient."}

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
