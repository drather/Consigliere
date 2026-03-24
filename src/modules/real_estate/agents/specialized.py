import re
import json
from typing import Dict, Any
from .base import BaseAgent


class ContextAnalystAgent(BaseAgent):
    """Single-call agent replacing MacroEconomistAgent + DataAnalystAgent (saves 1 LLM call)."""

    def run(self, context: Dict[str, Any]) -> Dict[str, str]:
        prompt = self._load_prompt("context_analyst", {
            "macro_data": json.dumps(context.get("macro_data", {}), ensure_ascii=False),
            "policy_context": json.dumps(context.get("policy_context", {}), ensure_ascii=False),
            "tx_data": json.dumps(context.get("tx_data", []), ensure_ascii=False, default=str),
            "interest_areas": json.dumps(context.get("interest_areas", []), ensure_ascii=False),
        })
        combined = self.llm.generate(prompt)

        # Split at the data-analyst section marker
        split_marker = "### 📈"
        if split_marker in combined:
            parts = combined.split(split_marker, 1)
            economist_insight = parts[0].strip()
            analyst_insight = split_marker + parts[1].strip()
        else:
            economist_insight = combined
            analyst_insight = combined

        return {"economist_insight": economist_insight, "analyst_insight": analyst_insight}


class CodeBasedValidator:
    """
    Rule-based validator replacing StrategyValidatorAgent LLM call (saves 1-2 LLM calls).
    Scans report text for price mentions that exceed the budget ceiling.
    """

    def run(self, context: Dict[str, Any]) -> Dict[str, Any]:
        budget_dict = context.get("budget_plan", {})
        report_json = context.get("generated_report", {})

        final_max_price = budget_dict.get("final_max_price", 0)
        max_억 = final_max_price / 100_000_000 if final_max_price else 999

        # Extract all mrkdwn text from report blocks
        all_text = ""
        for block in report_json.get("blocks", []):
            btype = block.get("type")
            if btype == "section":
                all_text += block.get("text", {}).get("text", "") + "\n"
            elif btype == "header":
                all_text += block.get("text", {}).get("text", "") + "\n"

        # Find price patterns like "12억", "12.5억"
        price_matches = re.findall(r'(\d+(?:\.\d+)?)\s*억', all_text)

        over_budget = []
        for p_str in price_matches:
            price_억 = float(p_str)
            # Only flag property-scale prices (>=3억) that exceed budget by >10%
            if price_억 >= 3 and max_억 > 0 and price_억 > max_억 * 1.1:
                over_budget.append(f"{p_str}억")

        # Separate hard violations (>10% over budget) from soft warnings (within 10%)
        hard_over = []
        soft_over = []
        for p_str in price_matches:
            price_억 = float(p_str)
            if price_억 >= 3 and max_억 > 0 and price_억 > max_억 * 1.1:
                hard_over.append(f"{p_str}억")
            elif price_억 >= 3 and max_억 > 0 and price_억 > max_억:
                soft_over.append(f"{p_str}억")

        if hard_over:
            feedback = (
                f"예산 한도 10% 초과 단지 발견: {', '.join(sorted(set(hard_over)))} "
                f"(한도: {max_억:.1f}억). 예산 이하 단지만 추천하십시오."
            )
            return {"status": "FAIL", "score": 50, "feedback": feedback}

        if soft_over:
            feedback = (
                f"예산 초과 가격 언급 발견: {', '.join(sorted(set(soft_over)))} "
                f"(한도: {max_억:.1f}억). 예산 이하 단지만 추천하십시오."
            )
            return {"status": "WARN", "score": 75, "feedback": feedback}

        return {"status": "PASS", "score": 95, "feedback": ""}


# Legacy agents — no longer used in main pipeline
class MacroEconomistAgent(BaseAgent):
    def run(self, context: Dict[str, Any]) -> str:
        prompt = self._load_prompt("macro_economist", {
            "macro_data": json.dumps(context.get("macro_data", {}), ensure_ascii=False),
            "policy_context": json.dumps(context.get("policy_context", {}), ensure_ascii=False)
        })
        return self.llm.generate(prompt)


class DataAnalystAgent(BaseAgent):
    def run(self, context: Dict[str, Any]) -> str:
        prompt = self._load_prompt("data_analyst", {
            "tx_data": json.dumps(context.get("tx_data", []), ensure_ascii=False, default=str),
            "interest_areas": json.dumps(context.get("interest_areas", []), ensure_ascii=False)
        })
        return self.llm.generate(prompt)


class StrategyValidatorAgent(BaseAgent):
    def run(self, context: Dict[str, Any]) -> Dict[str, Any]:
        prompt = self._load_prompt("strategy_validator", {
            "budget_plan": json.dumps(context.get("budget_plan", {}), ensure_ascii=False),
            "policy_context": json.dumps(context.get("policy_context", {}), ensure_ascii=False),
            "macro_data": json.dumps(context.get("macro_data", {}), ensure_ascii=False),
            "generated_report": json.dumps(context.get("generated_report", {}), ensure_ascii=False)
        })
        return self.llm.generate_json(prompt, max_tokens=1024)


class SynthesizerAgent(BaseAgent):
    def run(self, context: Dict[str, Any]) -> Dict[str, Any]:
        prompt = self._load_prompt("insight_parser", context)
        return self.llm.generate_json(prompt)
