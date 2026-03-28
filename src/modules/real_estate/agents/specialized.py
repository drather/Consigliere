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
            "news_summary": context.get("news_summary", ""),
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


class ReportValidator:
    """
    Rule-based validator. Weighted scoring across 4 checks (100pts total).
    Score >= 90 → PASS, 75-89 → WARN, < 75 → FAIL (triggers retry).

    Weights:
      - Budget compliance       : 40pts
      - Scorecard 3-complex     : 25pts
      - commute_minutes citation : 20pts
      - policy_facts citation   : 15pts
    """

    def run(self, context: Dict[str, Any]) -> Dict[str, Any]:
        budget_dict = context.get("budget_plan", {})
        report_json = context.get("generated_report", {})
        policy_facts = context.get("policy_facts", [])

        # --- Extract all report text ---
        all_text = ""
        for block in report_json.get("blocks", []):
            btype = block.get("type")
            if btype == "section":
                all_text += block.get("text", {}).get("text", "") + "\n"
            elif btype == "header":
                all_text += block.get("text", {}).get("text", "") + "\n"

        score = 0
        issues = []

        # 1. Budget compliance (40pts)
        final_max_price = budget_dict.get("final_max_price", 0)
        max_억 = final_max_price / 100_000_000 if final_max_price else 999
        price_matches = re.findall(r'(\d+(?:\.\d+)?)\s*억', all_text)

        hard_over, soft_over = [], []
        for p_str in price_matches:
            price_억 = float(p_str)
            if price_억 >= 3 and max_억 < 999:
                if price_억 > max_억 * 1.1:
                    hard_over.append(f"{p_str}억")
                elif price_억 > max_억:
                    soft_over.append(f"{p_str}억")

        if hard_over:
            issues.append(
                f"예산 한도 10% 초과 단지: {', '.join(sorted(set(hard_over)))} (한도: {max_억:.1f}억). 예산 이하 단지만 추천하십시오."
            )
            # score += 0
        elif soft_over:
            issues.append(
                f"예산 초과 가격 언급: {', '.join(sorted(set(soft_over)))} (한도: {max_억:.1f}억). 예산 이하 단지만 추천하십시오."
            )
            score += 20
        else:
            score += 40

        # 2. Scorecard completeness — require min(3, available_complex_count) ranks
        available_count = context.get("available_complex_count", 3)
        required_ranks = min(3, max(1, available_count))

        rank_patterns = [
            (r'(🥇|1순위)', "1순위"),
            (r'(🥈|2순위)', "2순위"),
            (r'(🥉|3순위)', "3순위"),
        ]
        found_ranks = sum(1 for pattern, _ in rank_patterns if re.search(pattern, all_text))
        if found_ranks >= required_ranks:
            score += 25
        elif found_ranks >= required_ranks - 1 and required_ranks > 1:
            score += 15
            issues.append(f"스코어카드에 {required_ranks}순위 단지가 누락되었습니다. {'/'.join(f'{i}순위' for i in range(1, required_ranks + 1))} {required_ranks}개 단지를 모두 작성하십시오.")
        else:
            issues.append(f"스코어카드 단지가 부족합니다 (최소 {required_ranks}개 필요). {'/'.join(f'{i}순위' for i in range(1, required_ranks + 1))}를 모두 작성하십시오.")

        # 3. commute_minutes_to_samsung citation (20pts)
        if re.search(r'출퇴근편의성', all_text) and re.search(r'\d+분', all_text):
            score += 20
        else:
            issues.append("출퇴근편의성 항목에 commute_minutes_to_samsung(분 단위 수치)가 인용되지 않았습니다. 각 단지 스코어카드에 구체적인 출퇴근 시간을 명시하십시오.")

        # 4. policy_facts citation (15pts)
        if policy_facts:
            cited = False
            for fact in policy_facts:
                content = fact.get("content", "")
                # Extract meaningful terms: Korean 3+ syllables or alphanumeric 4+ chars
                terms = re.findall(r'[가-힣]{3,}|[a-zA-Z0-9]{4,}', content)
                if any(term in all_text for term in terms[:20]):
                    cited = True
                    break
            if cited:
                score += 15
            else:
                issues.append("policy_facts의 정책/개발 정보가 리포트에 인용되지 않았습니다. 전문가의 제언 섹션에 최신 정책 팩트를 반드시 인용하십시오.")
        else:
            score += 15  # policy_facts가 없는 경우 해당 항목 면제

        # --- Determine status ---
        feedback = " | ".join(issues)
        if score >= 90:
            return {"status": "PASS", "score": score, "feedback": ""}
        elif score >= 75:
            return {"status": "WARN", "score": score, "feedback": feedback}
        else:
            return {"status": "FAIL", "score": score, "feedback": feedback}


CodeBasedValidator = ReportValidator  # backward-compat alias


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
