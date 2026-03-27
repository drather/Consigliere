import json
from typing import List, Dict, Any
from core.llm import LLMClient
from core.prompt_loader import PromptLoader
from core.logger import get_logger
from modules.career.models import JobPosting, JobAnalysis

logger = get_logger(__name__)


class JobAnalyzer:
    def __init__(self, llm: LLMClient, prompt_loader: PromptLoader):
        self.llm = llm
        self.prompt_loader = prompt_loader

    def analyze(self, postings: List[JobPosting], persona: Dict[str, Any]) -> JobAnalysis:
        try:
            _, prompt = self.prompt_loader.load("career/job_analyst", variables={
                "job_postings": json.dumps(
                    [p.model_dump() for p in postings], ensure_ascii=False
                ),
                "persona": json.dumps(persona, ensure_ascii=False),
                "experience_years": persona.get("user", {}).get("experience_years", 3),
            })
            data = self.llm.generate_json(prompt)
            return JobAnalysis(**data)
        except Exception as e:
            logger.error(f"JobAnalyzer 실패, 기본값 반환: {e}")
            return JobAnalysis()
