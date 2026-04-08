"""
InsightOrchestrator — 부동산 인사이트 리포트 파이프라인 오케스트레이터

흐름:
  1. Python: 예산 필터 → preference_rules 필터 → area_intel enrich
  2. LLM #1 (경량): 뉴스 → 호재 JSON (HoreaAnalyst)
  3. Python: 5개 기준 가중치 점수 계산 → 상위 N개 선정
  4. LLM #2 (단일): scored 결과 → 리포트 서술 (ReportSynthesizer)

모든 임계값·기준·목적지는 config/persona에서 읽는다. Zero Hardcoding.
"""
import json
import os
from datetime import date
from typing import Any, Dict, List, Optional

from core.llm import BaseLLMClient
from core.prompt_loader import PromptLoader
from core.logger import get_logger
from .candidate_filter import CandidateFilter
from .scoring import ScoringEngine
from .presenter import RealEstatePresenter

logger = get_logger(__name__)

_억 = 100_000_000


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
        news_text: str = "",
        interest_areas: List[str] = None,
    ) -> Dict[str, Any]:
        """
        Args:
            candidates: 예산 필터 + enrich 완료된 거래 목록
            budget_plan: BudgetPlan 인스턴스
            persona_data: persona.yaml user 섹션
            preference_rules: preference_rules.yaml rules 목록
            scoring_config: config.yaml scoring 섹션
            report_config: config.yaml report 섹션
            news_text: Job2 뉴스 텍스트 (없으면 빈 문자열)
            interest_areas: 관심 지역 목록
        """
        interest_areas = interest_areas or []
        top_n = report_config.get("top_n", 10)

        # Step 1: preference_rules 필터 (Python 코드)
        filtered = CandidateFilter(preference_rules).apply(candidates)
        logger.info(f"[Orchestrator] preference_rules 필터 후: {len(filtered)}건")

        if not filtered:
            logger.warning("[Orchestrator] 필터 후 후보 없음 — 빈 리포트 반환")
            return self._empty_report()

        # Step 2: LLM #1 — 뉴스 호재 분석 (경량)
        horea_data = {}
        if news_text.strip():
            horea_data = self._analyze_horea(news_text, interest_areas)
            logger.info(f"[Orchestrator] 호재 분석 완료: {list(horea_data.keys())}")

        # Step 3: 점수 계산 (Python 수식)
        priority_weights = persona_data.get("priority_weights", {})
        engine = ScoringEngine(weights=priority_weights, config=scoring_config)
        scored = engine.score_all(filtered, horea_data=horea_data)
        top_candidates = scored[:top_n]
        logger.info(f"[Orchestrator] 상위 {len(top_candidates)}개 선정 (전체 {len(scored)}개 중)")

        # Step 4: LLM #2 — 리포트 서술 (단일 호출)
        report_json = self._synthesize_report(
            target_date=target_date,
            top_candidates=top_candidates,
            budget_plan=budget_plan,
            persona_data=persona_data,
            top_n=top_n,
        )
        return report_json

    # ── LLM #1: 호재 분석 ─────────────────────────────────────────────

    def _analyze_horea(self, news_text: str, interest_areas: List[str]) -> Dict[str, Any]:
        """뉴스 텍스트 → 지역별 호재 JSON. 실패 시 빈 dict 반환."""
        try:
            _, prompt = self.prompt_loader.load(
                "horea_analyst",
                variables={
                    "interest_areas": json.dumps(interest_areas, ensure_ascii=False),
                    "news_text": news_text[:1500],
                },
            )
            result = self.llm.generate_json(prompt)
            return result if isinstance(result, dict) else {}
        except Exception as e:
            logger.warning(f"[Orchestrator] 호재 분석 실패 (무시): {e}")
            return {}

    # ── LLM #2: 리포트 서술 ───────────────────────────────────────────

    def _synthesize_report(
        self,
        target_date: date,
        top_candidates: List[Dict],
        budget_plan: Any,
        persona_data: Dict,
        top_n: int,
    ) -> Dict[str, Any]:
        """scored 상위 목록 → Slack Block Kit JSON 리포트."""
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
