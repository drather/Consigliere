import json
from typing import List, Dict, Any
from core.llm import LLMClient
from core.prompt_loader import PromptLoader
from core.logger import get_logger
from modules.career.models import JobAnalysis, TrendAnalysis, SkillGapAnalysis, SkillGapSnapshot

logger = get_logger(__name__)


class SkillGapAnalyzer:
    def __init__(self, llm: LLMClient, prompt_loader: PromptLoader):
        self.llm = llm
        self.prompt_loader = prompt_loader

    def analyze(
        self,
        job_analysis: JobAnalysis,
        trend_analysis: TrendAnalysis,
        persona: Dict[str, Any],
        gap_history: List[SkillGapSnapshot],
    ) -> SkillGapAnalysis:
        try:
            skills = persona.get("skills", {})
            _, prompt = self.prompt_loader.load("career/skill_gap_analyst", variables={
                "job_analysis": json.dumps(job_analysis.model_dump(), ensure_ascii=False),
                "trend_analysis": json.dumps(trend_analysis.model_dump(), ensure_ascii=False),
                "current_skills": json.dumps(skills.get("current", []), ensure_ascii=False),
                "learning_skills": json.dumps(skills.get("learning", []), ensure_ascii=False),
                "target_skills": json.dumps(skills.get("target", []), ensure_ascii=False),
                "current_focus": persona.get("learning", {}).get("current_focus", ""),
                "gap_history": json.dumps(
                    [s.model_dump() for s in gap_history], ensure_ascii=False
                ),
            })
            data = self.llm.generate_json(prompt)
            return SkillGapAnalysis(**data)
        except Exception as e:
            logger.error(f"SkillGapAnalyzer 실패, 기본값 반환: {e}")
            return SkillGapAnalysis()
