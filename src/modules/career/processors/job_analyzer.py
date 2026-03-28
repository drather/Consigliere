import json
from typing import List, Dict, Any
from modules.career.processors.base import BaseAnalyzer
from modules.career.models import JobPosting, JobAnalysis


class JobAnalyzer(BaseAnalyzer):
    def analyze(self, postings: List[JobPosting], persona: Dict[str, Any]) -> JobAnalysis:
        try:
            return self._call_llm("career/job_analyst", {
                "job_postings": json.dumps(
                    [p.model_dump() for p in postings], ensure_ascii=False
                ),
                "persona": json.dumps(persona, ensure_ascii=False),
                "experience_years": persona.get("user", {}).get("experience_years", 3),
            }, JobAnalysis)
        except Exception as e:
            self.logger.error(f"JobAnalyzer 실패, 기본값 반환: {e}")
            return JobAnalysis()
