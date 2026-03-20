import json
from datetime import date
from typing import Dict, Any, List, Optional
from core.logger import get_logger
from core.llm import LLMClient
from core.prompt_loader import PromptLoader
from .agents.specialized import MacroEconomistAgent, DataAnalystAgent, SynthesizerAgent, StrategyValidatorAgent
from .presenter import RealEstatePresenter

logger = get_logger(__name__)

class InsightOrchestrator:
    """
    Orchestrates the multi-agent consensus loop to generate 
    consistent and validated real estate strategies.
    """
    def __init__(self, llm: LLMClient, prompt_loader: PromptLoader):
        self.economist = MacroEconomistAgent(llm, prompt_loader)
        self.analyst = DataAnalystAgent(llm, prompt_loader)
        self.synthesizer = SynthesizerAgent(llm, prompt_loader)
        self.validator = StrategyValidatorAgent(llm, prompt_loader)
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
        
        # 1. Preliminary Analysis
        logger.info("👨‍💼 [Orchestrator] Running preliminary agent analysis...")
        economist_insight = self.economist.run({
            "macro_data": macro_dict,
            "policy_context": policy_context
        })
        analyst_insight = self.analyst.run({
            "tx_data": daily_txs,
            "interest_areas": persona_data.get("interest_areas", [])
        })

        # 2. Consensus Loop
        base_variables = {
            "target_date": target_date.strftime("%Y-%m-%d"),
            "economist_insight": economist_insight,
            "analyst_insight": analyst_insight,
            "persona_data": json.dumps(persona_data, ensure_ascii=False),
            "policy_context": json.dumps(policy_context, ensure_ascii=False),
            "policy_facts": json.dumps(policy_facts, ensure_ascii=False),
            "budget_plan": json.dumps(budget_dict, ensure_ascii=False),
            "fallback_note": fallback_note
        }

        MAX_ITERATIONS = 2
        current_iter = 0
        validator_feedback = ""
        final_report_json = None
        best_score = -1

        while current_iter < MAX_ITERATIONS:
            current_iter += 1
            logger.info(f"🧠 [Orchestrator] Consensusing (Iter {current_iter}/{MAX_ITERATIONS})...")
            
            # Step A: Synthesize
            base_variables["validator_feedback"] = validator_feedback
            report_json = self.synthesizer.run(base_variables)

            if "blocks" not in report_json:
                validator_feedback = "JSON structure error: must contain top-level 'blocks' list."
                continue

            # Step B: Validate
            validation_result = self.validator.run({
                "budget_plan": budget_dict,
                "policy_context": policy_context,
                "macro_data": macro_dict,
                "generated_report": report_json
            })
            
            status = validation_result.get("status", "FAIL")
            score = validation_result.get("score", 0)
            feedback = validation_result.get("feedback", "")

            if score > best_score:
                best_score = score
                final_report_json = report_json

            if score >= 90:
                logger.info(f"✅ [Orchestrator] Approved (Score: {score}).")
                break
            else:
                logger.warning(f"⚠️ [Orchestrator] Rejected (Score: {score}): {feedback}")
                validator_feedback = f"이전 생성물 비인가 사유: {feedback}"

        if not final_report_json:
             return {"blocks": [{"type": "section", "text": {"type": "mrkdwn", "text": "⚠️ 리포트 생성 중 오류가 발생했습니다."}}]}

        # 3. Final Polish via Presenter
        final_report_json = self.presenter.inject_validation_warning(final_report_json, best_score)
        final_report_json = self.presenter.beautify_citations(final_report_json, policy_facts)
        final_report_json["_score"] = best_score
        return final_report_json
