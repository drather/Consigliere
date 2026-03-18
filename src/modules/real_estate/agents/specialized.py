import json
from typing import Dict, Any
from .base import BaseAgent

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
