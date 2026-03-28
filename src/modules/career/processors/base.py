from typing import TypeVar, Type, Dict, Any

from core.llm import LLMClient
from core.prompt_loader import PromptLoader
from core.logger import get_logger

T = TypeVar("T")


class BaseAnalyzer:
    """
    Processor 공통 기반 클래스.

    LLM 호출 패턴(프롬프트 로드 → generate_json → 모델 파싱)을 공통화한다.
    예외 처리는 각 서브클래스의 analyze()가 담당한다.
    """

    def __init__(self, llm: LLMClient, prompt_loader: PromptLoader):
        self.llm = llm
        self.prompt_loader = prompt_loader
        self.logger = get_logger(self.__class__.__name__)

    def _call_llm(self, prompt_key: str, variables: Dict[str, Any], model_class: Type[T]) -> T:
        """프롬프트 로드 → LLM 호출 → model_class 파싱. 실패 시 예외 전파."""
        _, prompt = self.prompt_loader.load(prompt_key, variables=variables)
        data = self.llm.generate_json(prompt)
        return model_class(**data)
