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
        filtered_tx_count: int = 0,
        news_summary: str = "",
        fallback_note: str = ""
    ) -> Dict[str, Any]:

        # 1. Preliminary Analysis (single combined LLM call)
        logger.info("👨‍💼 [Orchestrator] Running combined context analysis...")
        context_result = self.context_analyst.run({
            "macro_data": macro_dict,
            "policy_context": policy_context,
            "tx_data": daily_txs,
            "interest_areas": persona_data.get("interest_areas", []),
            "news_summary": news_summary,
        })
        economist_insight = context_result["economist_insight"]
        analyst_insight = context_result["analyst_insight"]

        # 2. Synthesize + Validate loop (최대 3회 재시도)
        budget_constraint_note = (
            f"⚠️ 예산 필터 적용: {filtered_tx_count}건의 예산 초과 거래가 제거되었습니다. "
            f"아래 리스트에 포함된 단지만 추천하십시오. 리스트 외 단지 추천은 즉시 기각됩니다."
            if filtered_tx_count > 0
            else ""
        )

        # priority_weights → 리포트 분석 강조 지침 생성
        pw = persona_data.get("priority_weights", {})
        if pw:
            total = sum(pw.values()) or 1
            label_map = {
                "commute": "출퇴근 편의성",
                "liquidity": "환금성(역세권)",
                "school": "학군",
                "living_convenience": "생활편의",
                "price_potential": "가격상승 가능성",
            }
            ranked = sorted(pw.items(), key=lambda x: x[1], reverse=True)
            weights_desc = ", ".join(
                f"{label_map.get(k, k)} {round(v/total*100)}%"
                for k, v in ranked
            )
            priority_note = (
                f"사용자의 선호 기준 가중치 (높을수록 중요): {weights_desc}. "
                f"각 추천 단지마다 이 기준 순서대로 분석 섹션을 구성하고, "
                f"가중치가 높은 항목을 더 상세히 서술하십시오."
            )
        else:
            priority_note = ""

        base_variables = {
            "target_date": target_date.strftime("%Y-%m-%d"),
            "economist_insight": economist_insight,
            "analyst_insight": analyst_insight,
            "persona_data": json.dumps(persona_data, ensure_ascii=False),
            "policy_context": json.dumps(policy_context, ensure_ascii=False),
            "policy_facts": json.dumps(policy_facts, ensure_ascii=False),
            "budget_plan": json.dumps(budget_dict, ensure_ascii=False),
            "budget_constraint_note": budget_constraint_note,
            "priority_note": priority_note,
            "news_summary": news_summary,
            "fallback_note": fallback_note,
            "validator_feedback": "",
        }
        report_json = {}
        score = 0
        feedback = ""
        for attempt in range(1, 4):
            logger.info(f"🧠 [Orchestrator] Synthesizing report (attempt {attempt}/3)...")
            report_json = self.synthesizer.run(base_variables)
            if "blocks" not in report_json:
                logger.warning(f"⚠️ [Orchestrator] Invalid structure on attempt {attempt}: {str(report_json)[:200]}")
                continue

            validation_result = self.validator.run({
                "budget_plan": budget_dict,
                "generated_report": report_json,
                "policy_facts": policy_facts,
            })
            score = validation_result.get("score", 0)
            feedback = validation_result.get("feedback", "")

            if score >= 75:
                logger.info(f"✅ [Orchestrator] Validated (Score: {score}) on attempt {attempt}.")
                break

            logger.warning(f"⚠️ [Orchestrator] Score {score} < 75 on attempt {attempt}, retrying with feedback: {feedback}")
            base_variables["validator_feedback"] = feedback

        if "blocks" not in report_json:
            logger.error("❌ [Orchestrator] Synthesizer failed after 3 attempts.")
            return {"blocks": [{"type": "section", "text": {"type": "mrkdwn", "text": "⚠️ 리포트 생성 중 오류가 발생했습니다."}}]}

        # 4. Final Polish
        report_json = self.presenter.inject_validation_warning(report_json, score)
        report_json = self.presenter.beautify_citations(report_json, policy_facts)
        report_json["_score"] = score
        return report_json
