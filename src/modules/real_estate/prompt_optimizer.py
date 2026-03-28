import json
from typing import Any, Dict, List, Set

_BUDGET_SLIM_KEYS = {"final_max_price", "estimated_loan", "estimated_taxes", "reasoning"}
_POLICY_CONTEXT_SLIM_KEYS = {"standard_year", "ltv", "dsr", "news_summary"}
_EMPTY = (None, "", [], {})


class PromptTokenOptimizer:
    """
    Utility for reducing LLM input token count before prompt injection.

    All methods are static — no state, no instantiation required.
    Apply centrally in InsightOrchestrator before building base_variables.
    """

    @staticmethod
    def compact_json(data: Any) -> str:
        """Serialize to compact JSON: no whitespace, Korean characters preserved."""
        return json.dumps(data, ensure_ascii=False, separators=(',', ':'))

    @staticmethod
    def drop_empty(data: Dict) -> Dict:
        """Remove keys whose value is None, empty string, empty list, or empty dict.

        NOTE: 0 and False are intentionally preserved as meaningful values.
        """
        return {k: v for k, v in data.items() if v not in _EMPTY}

    @staticmethod
    def slim_list(items: List[Dict], fields: Set[str]) -> List[Dict]:
        """Keep only *fields* per item and strip empty values from each."""
        return [
            {k: v for k, v in item.items() if k in fields and v not in _EMPTY}
            for item in items
        ]

    @staticmethod
    def slim_budget(budget_dict: Dict) -> Dict:
        """Extract key budget fields only (drops intermediate LTV/DSR price candidates)."""
        return {
            k: v for k, v in budget_dict.items()
            if k in _BUDGET_SLIM_KEYS and v not in _EMPTY
        }

    @staticmethod
    def slim_policy_context(policy_context: Dict) -> Dict:
        """Extract key policy fields (ltv, dsr, standard_year, news_summary)."""
        return {k: policy_context[k] for k in _POLICY_CONTEXT_SLIM_KEYS if k in policy_context}

    @staticmethod
    def truncate(text: str, max_chars: int) -> str:
        """Truncate *text* to at most *max_chars* characters."""
        return text[:max_chars]
