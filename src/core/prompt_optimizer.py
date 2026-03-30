"""
PromptTokenOptimizer — LLM 입력 토큰 절감 유틸리티.

모든 메서드는 static — 상태 없음, 인스턴스화 불필요.
실 사용 지점: Orchestrator / Processor에서 _call_llm 호출 전에 적용.
"""
import json
from typing import Any, Dict, List, Set

_BUDGET_SLIM_KEYS = {"final_max_price", "estimated_loan", "estimated_taxes", "reasoning"}
_POLICY_CONTEXT_SLIM_KEYS = {"standard_year", "ltv", "dsr", "news_summary"}
_EMPTY = (None, "", [], {})


class PromptTokenOptimizer:
    """LLM 입력 토큰 수를 줄이기 위한 정적 유틸리티 모음."""

    @staticmethod
    def compact_json(data: Any) -> str:
        """공백 없는 컴팩트 JSON 직렬화. 한글 보존."""
        return json.dumps(data, ensure_ascii=False, separators=(',', ':'))

    @staticmethod
    def drop_empty(data: Dict) -> Dict:
        """None, 빈 문자열, 빈 리스트, 빈 dict인 키 제거.
        0과 False는 의미 있는 값이므로 보존.
        """
        return {k: v for k, v in data.items() if v not in _EMPTY}

    @staticmethod
    def slim_list(items: List[Dict], fields: Set[str]) -> List[Dict]:
        """각 항목에서 *fields*에 해당하는 키만 유지하고 빈 값 제거."""
        return [
            {k: v for k, v in item.items() if k in fields and v not in _EMPTY}
            for item in items
        ]

    @staticmethod
    def slim_budget(budget_dict: Dict) -> Dict:
        """예산 핵심 필드만 추출 (LTV/DSR 중간 계산값 제거)."""
        return {
            k: v for k, v in budget_dict.items()
            if k in _BUDGET_SLIM_KEYS and v not in _EMPTY
        }

    @staticmethod
    def slim_policy_context(policy_context: Dict) -> Dict:
        """정책 컨텍스트 핵심 필드만 추출 (ltv, dsr, standard_year, news_summary)."""
        return {k: policy_context[k] for k in _POLICY_CONTEXT_SLIM_KEYS if k in policy_context}

    @staticmethod
    def truncate(text: str, max_chars: int) -> str:
        """*text*를 최대 *max_chars* 글자로 자른다."""
        return text[:max_chars]
