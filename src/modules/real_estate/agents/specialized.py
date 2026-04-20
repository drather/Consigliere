"""
specialized.py — 부동산 모듈 전용 에이전트

현재 파이프라인에서 사용되는 에이전트만 유지한다.
LLM 역할: 리포트 서술만 담당 (InsightOrchestrator._synthesize_report) — macro_summary/horea_text는 Python이 준비
필터링·점수계산은 CandidateFilter·ScoringEngine(Python 코드)이 담당한다.
"""
from typing import Dict, Any
from .base import BaseAgent


# Legacy agents — 파이프라인에서 더 이상 사용하지 않음
# InsightOrchestrator가 직접 llm.generate_json()을 호출하므로 에이전트 래퍼 불필요

class MacroEconomistAgent(BaseAgent):
    """Legacy — 미사용."""
    def run(self, context: Dict[str, Any]) -> str:
        raise NotImplementedError("MacroEconomistAgent는 더 이상 사용하지 않습니다.")


class DataAnalystAgent(BaseAgent):
    """Legacy — 미사용."""
    def run(self, context: Dict[str, Any]) -> str:
        raise NotImplementedError("DataAnalystAgent는 더 이상 사용하지 않습니다.")


class ContextAnalystAgent(BaseAgent):
    """Legacy — 미사용. horea 분석은 Python 키워드 매칭으로 대체됨."""
    def run(self, context: Dict[str, Any]) -> Dict[str, str]:
        raise NotImplementedError("ContextAnalystAgent는 더 이상 사용하지 않습니다.")


class SynthesizerAgent(BaseAgent):
    """Legacy — 미사용. InsightOrchestrator._synthesize_report()로 대체."""
    def run(self, context: Dict[str, Any]) -> Dict[str, Any]:
        raise NotImplementedError("SynthesizerAgent는 더 이상 사용하지 않습니다.")


# ReportValidator 완전 제거 — Python ScoringEngine이 역할 대체
# CodeBasedValidator alias도 제거
