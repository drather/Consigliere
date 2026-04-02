from typing import TypeVar, Type, Dict, Any

from core.llm import LLMClient, BaseLLMClient
from core.prompt_loader import PromptLoader
from core.logger import get_logger

T = TypeVar("T")


class BaseAnalyzer:
    """
    Processor 공통 기반 클래스.

    LLM 호출 패턴(프롬프트 로드 → generate_json → 모델 파싱)을 공통화한다.
    예외 처리는 각 서브클래스의 analyze()가 담당한다.
    """

    def __init__(self, llm: BaseLLMClient, prompt_loader: PromptLoader):
        self.llm = llm
        self.prompt_loader = prompt_loader
        self.logger = get_logger(self.__class__.__name__)

    def _call_llm(
        self,
        prompt_key: str,
        variables: Dict[str, Any],
        model_class: Type[T],
        use_cache: bool = False,
    ) -> T:
        """
        프롬프트 로드 → LLM 호출 → model_class 파싱. 실패 시 예외 전파.

        Args:
            prompt_key: PromptLoader에서 로드할 프롬프트 경로
            variables: Jinja2 템플릿 변수
            model_class: LLM 응답을 파싱할 Pydantic 모델
            use_cache: True이면 ClaudeClient.generate_json_with_cache()를 사용.
                       LLM이 generate_json_with_cache를 지원하지 않으면 일반 경로로 폴백.
        """
        if use_cache and hasattr(self.llm, "generate_json_with_cache"):
            _, static_text, dynamic_text = self.prompt_loader.load_with_cache_split(
                prompt_key, variables=variables
            )
            data = self.llm.generate_json_with_cache(static_text, dynamic_text)
        else:
            metadata, prompt = self.prompt_loader.load(prompt_key, variables=variables)
            data = self.llm.generate_json(prompt, metadata=metadata)
        return model_class(**data)
