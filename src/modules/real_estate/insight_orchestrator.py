import json
from datetime import date
from typing import Dict, Any, List, Optional
from core.logger import get_logger
from core.llm import LLMClient
from core.prompt_loader import PromptLoader
from .agents.specialized import ContextAnalystAgent, CodeBasedValidator, SynthesizerAgent
from .presenter import RealEstatePresenter

logger = get_logger(__name__)

class InsightOrchestrator:
    """
    Orchestrates the multi-agent pipeline to generate validated real estate strategies.

    Cost-optimized flow (3 LLM calls vs original 6):
      1. ContextAnalystAgent  — macro + data analysis in a single call  (was 2 calls)
      2. SynthesizerAgent     — generates Slack Block Kit report          (1 call)
      3. CodeBasedValidator   — rule-based budget check, no LLM           (was 1-2 calls)
    """
    def __init__(self, llm: LLMClient, prompt_loader: PromptLoader):
        self.context_analyst = ContextAnalystAgent(llm, prompt_loader)
        self.synthesizer = SynthesizerAgent(llm, prompt_loader)
        self.validator = CodeBasedValidator()
        self.presenter = RealEstatePresenter()

    def generate_strategy(
        self,
        target_date: date,
        macro_dict: Dict[str, Any],
        policy_context: Dict[str, Any],
        daily_txs: List[Dict[str, Any]],
        persona_data: Dict[str, Any],
        policy_facts: List[Dict[str, Any]],
        budget_dict: Dict[str, Any],
        fallback_note: str = ""
    ) -> Dict[str, Any]:

        # 1. Preliminary Analysis (single combined LLM call)
        logger.info("👨‍💼 [Orchestrator] Running combined context analysis...")
        context_result = self.context_analyst.run({
            "macro_data": macro_dict,
            "policy_context": policy_context,
            "tx_data": daily_txs,
            "interest_areas": persona_data.get("interest_areas", [])
        })
        economist_insight = context_result["economist_insight"]
        analyst_insight = context_result["analyst_insight"]

        # 2. Synthesize (최대 3회 재시도)
        base_variables = {
            "target_date": target_date.strftime("%Y-%m-%d"),
            "economist_insight": economist_insight,
            "analyst_insight": analyst_insight,
            "persona_data": json.dumps(persona_data, ensure_ascii=False),
            "policy_context": json.dumps(policy_context, ensure_ascii=False),
            "policy_facts": json.dumps(policy_facts, ensure_ascii=False),
            "budget_plan": json.dumps(budget_dict, ensure_ascii=False),
            "fallback_note": fallback_note,
            "validator_feedback": "",
        }
        report_json = {}
        for attempt in range(1, 4):
            logger.info(f"🧠 [Orchestrator] Synthesizing report (attempt {attempt}/3)...")
            report_json = self.synthesizer.run(base_variables)
            if "blocks" in report_json:
                break
            logger.warning(f"⚠️ [Orchestrator] Invalid structure on attempt {attempt}: {str(report_json)[:200]}")

        if "blocks" not in report_json:
            logger.error("❌ [Orchestrator] Synthesizer failed after 3 attempts.")
            return {"blocks": [{"type": "section", "text": {"type": "mrkdwn", "text": "⚠️ 리포트 생성 중 오류가 발생했습니다."}}]}

        # 3. Rule-based validation (no LLM call)
        validation_result = self.validator.run({
            "budget_plan": budget_dict,
            "generated_report": report_json,
        })
        score = validation_result.get("score", 0)
        feedback = validation_result.get("feedback", "")

        if score < 90:
            logger.warning(f"⚠️ [Orchestrator] Validation warning (Score: {score}): {feedback}")
        else:
            logger.info(f"✅ [Orchestrator] Validated (Score: {score}).")

        # 4. Final Polish
        report_json = self.presenter.inject_validation_warning(report_json, score)
        report_json = self.presenter.beautify_citations(report_json, policy_facts)
        report_json["_score"] = score
        return report_json
