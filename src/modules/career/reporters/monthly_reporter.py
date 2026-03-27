from typing import List
from core.llm import LLMClient
from core.prompt_loader import PromptLoader
from core.logger import get_logger

logger = get_logger(__name__)


class MonthlyReporter:
    """
    해당 월의 주간 리포트 MD 텍스트를 LLM으로 종합해 월간 리포트를 생성한다.
    """
    def __init__(self, llm: LLMClient, prompt_loader: PromptLoader):
        self.llm = llm
        self.prompt_loader = prompt_loader

    def generate(
        self,
        month_label: str,
        year: int,
        month: int,
        weekly_reports: List[str],
    ) -> str:
        try:
            combined = "\n\n---\n\n".join(weekly_reports)
            _, prompt = self.prompt_loader.load("career/monthly_synthesizer", variables={
                "month_label": month_label,
                "year": year,
                "month": month,
                "weekly_reports": combined,
            })
            return self.llm.generate(prompt)
        except Exception as e:
            logger.error(f"MonthlyReporter LLM 실패: {e}")
            return f"# 커리어 Monthly Report — {month_label}\n\n리포트 생성 실패: {e}"
