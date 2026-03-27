from typing import List
from core.llm import LLMClient
from core.prompt_loader import PromptLoader
from core.logger import get_logger

logger = get_logger(__name__)


class WeeklyReporter:
    """
    7일치 daily report MD 텍스트를 LLM으로 종합해 주간 리포트를 생성한다.
    """
    def __init__(self, llm: LLMClient, prompt_loader: PromptLoader):
        self.llm = llm
        self.prompt_loader = prompt_loader

    def generate(
        self,
        week_label: str,
        start_date: str,
        end_date: str,
        daily_reports: List[str],
    ) -> str:
        try:
            combined = "\n\n---\n\n".join(daily_reports)
            _, prompt = self.prompt_loader.load("career/weekly_synthesizer", variables={
                "week_label": week_label,
                "start_date": start_date,
                "end_date": end_date,
                "daily_reports": combined,
            })
            return self.llm.generate(prompt)
        except Exception as e:
            logger.error(f"WeeklyReporter LLM 실패: {e}")
            return f"# 커리어 Weekly Report — {week_label}\n\n리포트 생성 실패: {e}"
