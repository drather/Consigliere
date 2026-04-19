"""
InsightOrchestrator — 부동산 인사이트 리포트 파이프라인 오케스트레이터

흐름:
  1. Python: preference_rules 필터
  2. LLM: horea_validator → horea_scores (news_articles 있을 때만)
  3. Python: ScoringEngine(horea_scores) → 상위 N개 선정
  4. LLM: report_synthesizer → 리포트 서술
"""
import json
from datetime import date
from typing import Any, Dict, List, Optional

from core.llm import BaseLLMClient
from core.prompt_loader import PromptLoader
from core.logger import get_logger
from .candidate_filter import CandidateFilter
from .scoring import ScoringEngine
from .presenter import RealEstatePresenter

logger = get_logger(__name__)


class InsightOrchestrator:
    def __init__(
        self,
        llm: BaseLLMClient,
        prompt_loader: PromptLoader,
        presenter: Optional[RealEstatePresenter] = None,
    ):
        self.llm = llm
        self.prompt_loader = prompt_loader
        self.presenter = presenter or RealEstatePresenter()

    # ── Public API ─────────────────────────────────────────────────────

    def generate_strategy(
        self,
        target_date: date,
        candidates: List[Dict[str, Any]],
        budget_plan: Any,
        persona_data: Dict[str, Any],
        preference_rules: List[Dict[str, Any]],
        scoring_config: Dict[str, Any],
        report_config: Dict[str, Any],
        horea_data: Optional[Dict[str, Any]] = None,
        macro_summary: str = "",
        horea_text: str = "",
        news_articles: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        """
        Args:
            candidates:       예산 필터 + enrich 완료된 거래 목록
            budget_plan:      BudgetPlan 인스턴스
            persona_data:     persona.yaml user 섹션
            preference_rules: preference_rules.yaml rules 목록
            scoring_config:   config.yaml scoring 섹션
            report_config:    config.yaml report 섹션
            horea_data:       Python으로 사전 추출된 호재 데이터 dict
            macro_summary:    Python으로 사전 포맷팅된 거시경제 요약 문자열
            horea_text:       Python으로 사전 변환된 호재 텍스트 문자열
            news_articles:    Job2가 저장한 기사 목록 (horea_validator 입력용, 없으면 None)
        """
        horea_data = horea_data or {}
        top_n = report_config.get("top_n", 5)

        # Step 1: preference_rules 필터 (Python 코드)
        filtered = CandidateFilter(preference_rules).apply(candidates)
        logger.info(f"[Orchestrator] preference_rules 필터 후: {len(filtered)}건")

        if not filtered:
            logger.warning("[Orchestrator] 필터 후 후보 없음 — 빈 리포트 반환")
            return self._empty_report()

        # Step 2: horea_validator LLM (news_articles 있을 때만)
        interest_areas = persona_data.get("user", {}).get("interest_areas", [])
        horea_scores = self._validate_horea(interest_areas, news_articles)

        # Step 3: 점수 계산 (Python 수식)
        priority_weights = persona_data.get("priority_weights", {})
        engine = ScoringEngine(weights=priority_weights, config=scoring_config)
        scored = engine.score_all(filtered, horea_scores=horea_scores)
        top_candidates = scored[:top_n]
        logger.info(f"[Orchestrator] 상위 {len(top_candidates)}개 선정 (전체 {len(scored)}개 중)")

        # Step 4: LLM — 리포트 서술
        return self._synthesize_report(
            target_date=target_date,
            top_candidates=top_candidates,
            budget_plan=budget_plan,
            persona_data=persona_data,
            top_n=top_n,
            macro_summary=macro_summary,
            horea_text=horea_text,
            horea_assessments=horea_scores or {},
        )

    # ── horea_validator LLM 단계 ───────────────────────────────────────

    def _validate_horea(
        self,
        interest_areas: List[str],
        news_articles: Optional[List[Dict[str, Any]]],
    ) -> Optional[Dict[str, Any]]:
        """horea_validator LLM 호출. 기사 없거나 실패 시 None 반환."""
        if not news_articles:
            return None
        try:
            today = date.today().strftime("%Y-%m-%d")
            _, prompt = self.prompt_loader.load(
                "horea_validator",
                variables={
                    "today_date": today,
                    "interest_areas": json.dumps(interest_areas, ensure_ascii=False),
                    "articles_json": json.dumps(news_articles, ensure_ascii=False),
                },
            )
            result = self.llm.generate_json(prompt)
            assessments = result.get("horea_assessments", {})
            logger.info(f"[Orchestrator] horea_validator 완료: {list(assessments.keys())}")
            return assessments
        except Exception as e:
            logger.warning(f"[Orchestrator] horea_validator 실패 — 중립값 적용: {e}")
            return None

    # ── LLM 단일 호출: 리포트 서술 ────────────────────────────────────

    def _synthesize_report(
        self,
        target_date: date,
        top_candidates: List[Dict],
        budget_plan: Any,
        persona_data: Dict,
        top_n: int,
        macro_summary: str = "",
        horea_text: str = "",
        horea_assessments: Optional[Dict] = None,
    ) -> Dict[str, Any]:
        """scored 상위 목록 + 거시경제 요약 + 호재 텍스트 → Slack Block Kit JSON 리포트."""
        pw = persona_data.get("priority_weights", {})
        total_w = sum(pw.values()) or 1
        label_map = {
            "commute": "출퇴근편의성",
            "liquidity": "환금성",
            "price_potential": "가격상승가능성",
            "living_convenience": "생활편의",
            "school": "학군",
        }
        ranked = sorted(pw.items(), key=lambda x: x[1], reverse=True)
        priority_desc = ", ".join(
            f"{label_map.get(k, k)} {round(v/total_w*100)}%"
            for k, v in ranked
        )

        try:
            metadata, prompt = self.prompt_loader.load(
                "report_synthesizer",
                variables={
                    "target_date": target_date.strftime("%Y-%m-%d"),
                    "budget_reasoning": getattr(budget_plan, "reasoning", ""),
                    "priority_weights_desc": priority_desc,
                    "top_n": top_n,
                    "macro_summary": macro_summary or "거시경제 데이터 없음",
                    "horea_text": horea_text or "호재 정보 없음",
                    "horea_assessments": json.dumps(
                        horea_assessments or {}, ensure_ascii=False
                    ),
                    "ranked_candidates": json.dumps(
                        top_candidates, ensure_ascii=False, default=str
                    ),
                },
            )
            result = self.llm.generate_json(prompt, metadata=metadata)
            if "blocks" in result:
                return result
            logger.warning("[Orchestrator] Synthesizer 응답에 blocks 없음")
        except Exception as e:
            logger.error(f"[Orchestrator] 리포트 생성 실패: {e}")

        return self._empty_report()

    def _empty_report(self) -> Dict[str, Any]:
        return {
            "blocks": [{
                "type": "section",
                "text": {"type": "mrkdwn", "text": "⚠️ 조건에 맞는 추천 단지가 없습니다."},
            }]
        }
