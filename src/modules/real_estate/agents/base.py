from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from core.llm import LLMClient
from core.prompt_loader import PromptLoader

class BaseAgent(ABC):
    """
    Base class for all specialized AI agents.
    Provides standard interface for loading prompts and generating responses.
    """
    def __init__(self, llm: LLMClient, prompt_loader: PromptLoader):
        self.llm = llm
        self.prompt_loader = prompt_loader

    @abstractmethod
    def run(self, context: Dict[str, Any]) -> Any:
        """
        Executes the agent's logic given the context.
        """
        pass

    def _load_prompt(self, prompt_name: str, variables: Dict[str, Any]) -> str:
        _, prompt_str = self.prompt_loader.load(prompt_name, variables=variables)
        return prompt_str
