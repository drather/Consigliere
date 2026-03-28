import os
import yaml
from datetime import date
from typing import Dict, Any, List, Optional
from core.logger import get_logger
from core.llm import LLMClient
from core.prompt_loader import PromptLoader
from .agents.specialized import ContextAnalystAgent, ReportValidator, SynthesizerAgent
from .presenter import RealEstatePresenter
from .prompt_optimizer import PromptTokenOptimizer as PTO

logger = get_logger(__name__)

_RULES_FILE = os.path.join(os.path.dirname(__file__), "preference_rules.yaml")


def _load_preference_rules() -> str:
    """preference_rules.yaml에서 enabled=True 규칙만 읽어 프롬프트용 문자열로 반환."""
    try:
        with open(_RULES_FILE, encoding="utf-8") as f:
            data = yaml.safe_load(f)
        enabled = [r for r in data.get("rules", []) if r.get("enabled", False)]
        if not enabled:
            return ""
        lines = ["아래 조건을 모두 충족하는 단지만 추천하십시오 (위반 시 즉시 기각):"]
        for r in enabled:
            lines.append(f"- [{r['id']}] {r['constraint'].strip()}")
        return "\n".join(lines)
    except Exception as e:
        logger.warning(f"⚠️ [Orchestrator] preference_rules.yaml 로드 실패: {e}")
        return ""

# tx_data에서 ContextAnalyst에 전달할 핵심 필드만 유지 (입력 토큰 절감)
TX_SLIM_FIELDS = {
    "apt_name", "deal_price", "exclusive_area", "deal_date", "floor",
    "commute_minutes_to_samsung", "nearest_stations", "school_zone_notes",
    "elementary_schools", "reconstruction_status", "reconstruction_potential", "gtx_benefit",
}

# Synthesizer에 전달할 persona 핵심 필드
PERSONA_SLIM_KEYS = {"priority_weights", "investment_style", "commute", "apartment_preferences"}

class InsightOrchestrator:
    """
    Orchestrates the multi-agent pipeline to generate validated real estate strategies.

    Cost-optimized flow (3 LLM calls vs original 6):
      1. ContextAnalystAgent  — macro + data analysis in a single call  (was 2 calls)
      2. SynthesizerAgent     — generates Slack Block Kit report          (1 call)
      3. CodeBasedValidator   — rule-based budget check, no LLM           (was 1-2 calls)
    """
    def __init__(
        self,
        llm: LLMClient,
        prompt_loader: PromptLoader,
        context_analyst=None,
        synthesizer=None,
        validator=None,
        presenter=None,
    ):
        self.context_analyst = context_analyst or ContextAnalystAgent(llm, prompt_loader)
        self.synthesizer = synthesizer or SynthesizerAgent(llm, prompt_loader)
        self.validator = validator or ReportValidator()
        self.presenter = presenter or RealEstatePresenter()

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
        fallback_note: str = "",
        budget_complex_names: Optional[List[str]] = None,
    ) -> Dict[str, Any]:

        # ── 입력 데이터 슬림화 (PromptTokenOptimizer 일괄 적용) ──────────────
        slim_tx_data    = PTO.slim_list(daily_txs, TX_SLIM_FIELDS)
        slim_policy_facts = [{"content": PTO.truncate(f.get("content", ""), 500)} for f in policy_facts[:3]]
        slim_persona    = PTO.drop_empty({k: persona_data[k] for k in PERSONA_SLIM_KEYS if k in persona_data})
        slim_budget     = PTO.slim_budget(budget_dict)
        slim_policy_ctx = PTO.slim_policy_context(policy_context)
        # interest_areas는 ContextAnalyst에 필요하므로 별도 유지
        interest_areas  = persona_data.get("interest_areas", [])

        # budget_complex_names: 예산 내 추천 가능 단지 화이트리스트
        complex_names = budget_complex_names or []

        # 1. Preliminary Analysis (single combined LLM call)
        logger.info("👨‍💼 [Orchestrator] Running combined context analysis...")
        context_result = self.context_analyst.run({
            "macro_data": macro_dict,
            "policy_context": slim_policy_ctx,
            "tx_data": slim_tx_data,
            "interest_areas": interest_areas,
            "news_summary": news_summary,
        })
        economist_insight = PTO.truncate(context_result["economist_insight"], 1500)
        analyst_insight   = PTO.truncate(context_result["analyst_insight"],   2000)

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
            "persona_data": PTO.compact_json(slim_persona),
            "policy_context": PTO.compact_json(slim_policy_ctx),
            "policy_facts": PTO.compact_json(slim_policy_facts),
            "budget_plan": PTO.compact_json(slim_budget),
            "budget_constraint_note": budget_constraint_note,
            "priority_note": priority_note,
            "news_summary": news_summary,
            "fallback_note": fallback_note,
            "validator_feedback": "",
            "budget_filtered_complexes": PTO.compact_json(complex_names),
            "user_preference_rules": _load_preference_rules(),
        }
        report_json = {}
        score = 0
        feedback = ""
        for attempt in range(1, 3):  # 최대 2회 시도 (토큰 절감)
            logger.info(f"🧠 [Orchestrator] Synthesizing report (attempt {attempt}/3)...")
            report_json = self.synthesizer.run(base_variables)
            if "blocks" not in report_json:
                logger.warning(f"⚠️ [Orchestrator] Invalid structure on attempt {attempt}: {str(report_json)[:200]}")
                continue

            validation_result = self.validator.run({
                "budget_plan": budget_dict,
                "generated_report": report_json,
                "policy_facts": slim_policy_facts,
                "available_complex_count": len(complex_names),
            })
            score = validation_result.get("score", 0)
            feedback = validation_result.get("feedback", "")

            if score >= 75:
                logger.info(f"✅ [Orchestrator] Validated (Score: {score}) on attempt {attempt}.")
                break

            logger.warning(f"⚠️ [Orchestrator] Score {score} < 75 on attempt {attempt}, retrying with feedback: {feedback}")
            base_variables["validator_feedback"] = feedback

        if "blocks" not in report_json:
            logger.error("❌ [Orchestrator] Synthesizer failed after 2 attempts.")
            return {"blocks": [{"type": "section", "text": {"type": "mrkdwn", "text": "⚠️ 리포트 생성 중 오류가 발생했습니다."}}]}

        # 4. Final Polish
        report_json = self.presenter.inject_validation_warning(report_json, score)
        report_json = self.presenter.beautify_citations(report_json, policy_facts)
        report_json["_score"] = score
        return report_json
