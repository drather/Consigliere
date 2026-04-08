"""
CandidateFilter — preference_rules.yaml 규칙을 Python 코드로 실행한다.

LLM 프롬프트로 필터링을 요청하는 방식 대신, 각 규칙을 코드로 직접 처리한다.
새 규칙 추가: preference_rules.yaml에 항목 작성 + 이 파일의 _RULE_HANDLERS에 핸들러 등록.
"""
from typing import Any, Callable, Dict, List
from core.logger import get_logger

logger = get_logger(__name__)


def _handle_apartment_only(candidates: List[Dict], rule: Dict) -> List[Dict]:
    """순수 아파트(단독 주거용)만 통과. 오피스텔·주상복합 제거."""
    excluded = {"오피스텔", "주상복합", "상업용"}
    return [
        c for c in candidates
        if c.get("building_type", "아파트") not in excluded
        and "오피스텔" not in c.get("apt_name", "")
    ]


def _handle_min_exclusive_area(candidates: List[Dict], rule: Dict) -> List[Dict]:
    """전용면적 min_area_sqm ㎡ 이상만 통과."""
    threshold = rule.get("min_area_sqm", 59)
    return [c for c in candidates if c.get("exclusive_area", 0) >= threshold]


def _handle_min_household_count(candidates: List[Dict], rule: Dict) -> List[Dict]:
    """세대수 min_households 이상만 통과. household_count가 없으면 통과시킨다 (데이터 미확인)."""
    threshold = rule.get("min_households", 500)
    return [
        c for c in candidates
        if c.get("household_count") is None or c.get("household_count", 0) == 0
        or c.get("household_count", 0) >= threshold
    ]


def _handle_within_commute(candidates: List[Dict], rule: Dict) -> List[Dict]:
    """commute_minutes가 max_commute_minutes 이하인 단지만 통과."""
    max_min = rule.get("max_commute_minutes", 30)
    return [
        c for c in candidates
        if c.get("commute_minutes") is None or c.get("commute_minutes") <= max_min
    ]


def _handle_reconstruction_only(candidates: List[Dict], rule: Dict) -> List[Dict]:
    """재건축 추진 단지(potential != UNKNOWN/None)만 통과."""
    valid = {"HIGH", "MEDIUM", "COMPLETED"}
    return [c for c in candidates if c.get("reconstruction_potential", "UNKNOWN") in valid]


def _handle_gtx_required(candidates: List[Dict], rule: Dict) -> List[Dict]:
    """GTX 수혜 단지만 통과."""
    return [c for c in candidates if c.get("gtx_benefit")]


# 규칙 ID → 핸들러 매핑 (새 규칙 추가 시 여기에만 등록)
_RULE_HANDLERS: Dict[str, Callable] = {
    "apartment_only": _handle_apartment_only,
    "min_exclusive_area": _handle_min_exclusive_area,
    "min_household_count": _handle_min_household_count,
    "within_30min_commute": _handle_within_commute,
    "reconstruction_candidate_only": _handle_reconstruction_only,
    "gtx_benefit_required": _handle_gtx_required,
}


class CandidateFilter:
    """
    preference_rules 목록을 받아 후보 아파트 리스트에 순차 적용한다.

    enabled=False 규칙은 건너뛴다.
    알 수 없는 rule id는 경고 후 건너뛴다.
    """

    def __init__(self, rules: List[Dict]):
        self.rules = [r for r in rules if r.get("enabled", False)]

    def apply(self, candidates: List[Dict]) -> List[Dict]:
        remaining = list(candidates)
        for rule in self.rules:
            rule_id = rule.get("id", "")
            handler = _RULE_HANDLERS.get(rule_id)
            if handler is None:
                logger.warning(f"[CandidateFilter] 알 수 없는 규칙 id={rule_id} — 건너뜀")
                continue
            before = len(remaining)
            remaining = handler(remaining, rule)
            logger.info(f"[CandidateFilter] rule={rule_id}: {before}→{len(remaining)}건")
        return remaining
