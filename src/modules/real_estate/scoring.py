"""
ScoringEngine — 5개 기준으로 후보 아파트를 Python 수식으로 점수화한다.

LLM이 점수를 추정하던 방식 대신, area_intel 데이터와 horea_scores를 바탕으로
deterministic하게 계산한다. 모든 임계값은 config.yaml scoring 섹션에서 읽는다.
"""
from typing import Any, Dict, List, Optional
from core.logger import get_logger

logger = get_logger(__name__)

_HIGH = 100
_MEDIUM = 60
_LOW = 20


def _threshold_score(value: float, thresholds: List[int]) -> int:
    """[low_threshold, high_threshold] 기준으로 HIGH/MEDIUM/LOW 점수 반환."""
    low_t, high_t = thresholds[0], thresholds[1]
    if value <= low_t:
        return _HIGH
    if value <= high_t:
        return _MEDIUM
    return _LOW


def _household_score(value: float, thresholds: List[int]) -> int:
    """세대수는 클수록 좋다 (역방향 threshold)."""
    low_t, high_t = thresholds[0], thresholds[1]
    if value >= high_t:
        return _HIGH
    if value >= low_t:
        return _MEDIUM
    return _LOW


class ScoringEngine:
    """
    후보 아파트 목록에 가중치 점수를 계산한다.

    Args:
        weights: persona.priority_weights (commute, liquidity, price_potential,
                 living_convenience, school)
        config:  config.yaml scoring 섹션
    """

    def __init__(self, weights: Dict[str, int], config: Dict[str, Any]):
        self.weights = weights
        self.commute_thresholds = config.get("commute_thresholds", [20, 35])
        self.household_thresholds = config.get("household_thresholds", [300, 500])
        self.school_keywords = config.get("school_keywords", ["학원가", "명문"])
        self.neutral = config.get("data_absent_neutral", 50)
        self.recon_map = config.get("reconstruction_score_map", {
            "HIGH": 100, "MEDIUM": 60, "LOW": 20, "COMPLETED": 50, "UNKNOWN": 50
        })

    # ── 기준별 점수 계산 ──────────────────────────────────────────────

    def _score_commute(self, c: Dict) -> int:
        minutes = c.get("commute_minutes")
        if minutes is None:
            return self.neutral
        return _threshold_score(minutes, self.commute_thresholds)

    def _score_liquidity(self, c: Dict) -> int:
        households = c.get("household_count")
        if households is None:
            return self.neutral
        return _household_score(households, self.household_thresholds)

    def _score_school(self, c: Dict) -> int:
        notes = c.get("school_zone_notes")
        if notes is None:
            return self.neutral
        if any(kw in notes for kw in self.school_keywords):
            return _HIGH
        schools = c.get("elementary_schools", [])
        if schools:
            return _MEDIUM
        return _LOW

    def _score_living_convenience(self, c: Dict) -> int:
        """역 수 + 도보 5분 이내 역 존재 여부로 판단."""
        stations = c.get("nearest_stations")
        if stations is None:
            return self.neutral
        if not stations:
            return _LOW
        close_stations = [s for s in stations if s.get("walk_minutes", 99) <= 5]
        if len(close_stations) >= 2:
            return _HIGH
        if close_stations:
            return _MEDIUM
        return _LOW

    def _score_price_potential(self, c: Dict, horea_scores: Optional[Dict] = None) -> int:
        """재건축 잠재력 기본 점수 + horea_validator LLM 점수 부스트."""
        potential = c.get("reconstruction_potential", "UNKNOWN")
        base = self.recon_map.get(potential, self.neutral)

        if c.get("gtx_benefit"):
            base = min(100, base + 30)

        if horea_scores:
            district_name = c.get("district_name", "")
            for area_key, assessment in horea_scores.items():
                if area_key in district_name or district_name in area_key:
                    score = assessment.get("score", 0)
                    boost = int(score * 0.4)  # 100→+40, 50→+20, 0→0
                    base = min(100, base + boost)
                    break

        return base

    # ── 통합 점수 계산 ────────────────────────────────────────────────

    def score_all(self, candidates: List[Dict], horea_scores: Optional[Dict] = None) -> List[Dict]:
        """각 후보의 5개 기준 점수와 가중치 합산 총점을 계산하여 내림차순 정렬한다."""
        horea_scores = horea_scores or {}
        total_weight = sum(self.weights.values()) or 1

        scored = []
        for c in candidates:
            scores = {
                "commute": self._score_commute(c),
                "liquidity": self._score_liquidity(c),
                "school": self._score_school(c),
                "living_convenience": self._score_living_convenience(c),
                "price_potential": self._score_price_potential(c, horea_scores),
            }
            total = sum(
                scores[k] * self.weights.get(k, 0) / total_weight
                for k in scores
            )
            result = dict(c)
            result["scores"] = scores
            result["total_score"] = round(total, 1)
            scored.append(result)
            logger.debug(f"[Scoring] {c.get('apt_name')} → {total:.1f}점 {scores}")

        return sorted(scored, key=lambda x: x["total_score"], reverse=True)
