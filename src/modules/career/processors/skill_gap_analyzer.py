import json
from typing import List, Dict, Any
from modules.career.processors.base import BaseAnalyzer
from modules.career.models import JobAnalysis, TrendAnalysis, SkillGapAnalysis, SkillGapSnapshot


class SkillGapAnalyzer(BaseAnalyzer):
    def analyze(
        self,
        job_analysis: JobAnalysis,
        trend_analysis: TrendAnalysis,
        persona: Dict[str, Any],
        gap_history: List[SkillGapSnapshot],
    ) -> SkillGapAnalysis:
        try:
            skills = persona.get("skills", {})
            return self._call_llm("career/skill_gap_analyst", {
                "job_analysis": json.dumps(job_analysis.model_dump(), ensure_ascii=False),
                "trend_analysis": json.dumps(trend_analysis.model_dump(), ensure_ascii=False),
                "current_skills": json.dumps(skills.get("current", []), ensure_ascii=False),
                "learning_skills": json.dumps(skills.get("learning", []), ensure_ascii=False),
                "target_skills": json.dumps(skills.get("target", []), ensure_ascii=False),
                "current_focus": persona.get("learning", {}).get("current_focus", ""),
                "gap_history": json.dumps(
                    [s.model_dump() for s in gap_history], ensure_ascii=False
                ),
            }, SkillGapAnalysis)
        except Exception as e:
            self.logger.error(f"SkillGapAnalyzer 실패, 기본값 반환: {e}")
            return SkillGapAnalysis()
