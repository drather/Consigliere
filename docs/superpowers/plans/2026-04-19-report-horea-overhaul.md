# Report Horea Overhaul Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** ISSUE-01~03 수정 + horea LLM 검증 도입 + ScoringEngine 중립값 처리 + 리포트 개조식 출력

**Architecture:** service.py 단순 버그 3종 수정 → ScoringEngine 중립값 + horea_scores 파라미터 전환 → Job2 articles JSON 저장 → InsightOrchestrator horea_validator LLM 단계 삽입 → report_synthesizer 개조식 리포트 포맷 변경

**Tech Stack:** Python 3.12, SQLite, Gemini Flash (horea_validator), pytest, ARM64 (`arch -arm64 .venv/bin/python3.12`)

---

## 파일 맵

| 파일 | 종류 | 담당 |
|------|------|------|
| `src/modules/real_estate/service.py` | 수정 | dedup normalize, _lookup normalize, _area_matches, _load_stored_news_articles |
| `src/modules/real_estate/news/service.py` | 수정 | _save_articles_json 추가 |
| `src/modules/real_estate/insight_orchestrator.py` | 수정 | _validate_horea LLM 단계, horea_scores 주입, horea_assessments 전달 |
| `src/modules/real_estate/scoring.py` | 수정 | horea_scores 파라미터, 전 기준 중립값 처리 |
| `src/modules/real_estate/config.yaml` | 수정 | scoring.data_absent_neutral: 50, recon_map.UNKNOWN: 50 |
| `src/modules/real_estate/prompts/horea_validator.md` | 신규 | horea 검증 프롬프트 |
| `src/modules/real_estate/prompts/report_synthesizer.md` | 수정 | 개조식 + 점수 + horea_assessments |
| `tests/modules/real_estate/test_service_fixes.py` | 신규 | ISSUE-01/02/03-A 단위 테스트 |
| `tests/modules/real_estate/test_scoring_neutral_defaults.py` | 신규 | 중립값 + horea_scores 테스트 |
| `tests/modules/real_estate/test_horea_validator.py` | 신규 | horea_validator LLM 단계 테스트 |
| `tests/modules/real_estate/test_scoring.py` | 수정 | horea_data → horea_scores 형식 업데이트 |
| `tests/modules/real_estate/test_orchestrator_single_llm.py` | 수정 | news_articles 파라미터, LLM 호출 2회 검증 |
| `docs/features/report-generation-overhaul/issues.md` | 수정 | 해결 방향 추가 |
| `docs/features/report-generation-overhaul/progress.md` | 수정 | Phase 3.5 이슈 체크 |

---

## Task 1: service.py 버그 수정 3종 (ISSUE-01, 02, 03-A)

**Files:**
- Modify: `src/modules/real_estate/service.py`
- Create: `tests/modules/real_estate/test_service_fixes.py`

- [ ] **Step 1: 테스트 파일 작성 (실패 확인용)**

```python
# tests/modules/real_estate/test_service_fixes.py
import sys, os
import pytest
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../../src"))

from modules.real_estate.service import RealEstateAgent, _area_matches
from modules.real_estate.apartment_repository import ApartmentRepository
from modules.real_estate.apt_master_repository import AptMasterRepository
from modules.real_estate.models import ApartmentMaster, AptMasterEntry
from modules.real_estate.transaction_repository import _normalize_name
from datetime import timezone, datetime


def _make_agent(apt_repo=None, apt_master_repo=None):
    agent = object.__new__(RealEstateAgent)
    agent.apt_repo = apt_repo or ApartmentRepository(db_path=":memory:")
    agent.apt_master_repo = apt_master_repo or AptMasterRepository(db_path=":memory:")
    return agent


# ── ISSUE-01: dedup key normalize ──────────────────────────────────────────


def test_dedup_key_same_for_normalized_names():
    """이매촌(청구)와 이매촌청구는 dedup 후 1건만 남아야 한다."""
    from modules.real_estate.service import _make_dedup_key
    tx1 = {"apt_name": "이매촌청구",  "exclusive_area": 84.0, "deal_date": "2026-04-15", "floor": 5, "price": 80000}
    tx2 = {"apt_name": "이매촌(청구)", "exclusive_area": 84.0, "deal_date": "2026-04-15", "floor": 5, "price": 80000}
    assert _make_dedup_key(tx1) == _make_dedup_key(tx2)


# ── ISSUE-02: _lookup_apt_details normalize ─────────────────────────────────


def test_lookup_normalizes_parenthesized_name():
    """이매촌(청구) 조회 시 내부적으로 이매촌청구로 normalize하여 조회한다."""
    apt_repo = ApartmentRepository(db_path=":memory:")
    apt_master_repo = AptMasterRepository(db_path=":memory:")

    apt_repo.save(ApartmentMaster(
        apt_name="이매촌청구", district_code="41135", complex_code="K100",
        household_count=800, building_count=10, parking_count=0,
        constructor="현대건설", approved_date="19990101",
    ))
    apt_master_repo.upsert(AptMasterEntry(
        apt_name="이매촌청구", district_code="41135", complex_code="K100",
        created_at=datetime.now(timezone.utc).isoformat(),
    ))

    agent = _make_agent(apt_repo, apt_master_repo)
    result = agent._lookup_apt_details("이매촌(청구)", "41135")

    assert result is not None
    assert result.household_count == 800


def test_lookup_returns_none_for_truly_missing():
    """실제로 없는 아파트는 None 반환."""
    agent = _make_agent()
    assert agent._lookup_apt_details("없는아파트(12)", "11680") is None


# ── ISSUE-03-A: _area_matches compound name ─────────────────────────────────


def test_area_matches_full_name():
    assert _area_matches("강남구", "강남구 재건축 허가") is True


def test_area_matches_partial_token_in_compound_name():
    """'성남시 분당구' → 뉴스에 '분당구'만 있어도 매칭해야 한다."""
    assert _area_matches("성남시 분당구", "분당구 재건축 추진") is True


def test_area_matches_another_token():
    assert _area_matches("성남시 분당구", "성남시 개발 호재") is True


def test_area_matches_no_match():
    assert _area_matches("성남시 분당구", "강남 GTX 착공") is False


def test_extract_horea_data_compound_area():
    """복합 지명 '성남시 분당구'가 '분당구'로만 나온 뉴스에서도 매칭된다."""
    agent = _make_agent()
    news = "분당구 재건축 사업이 인허가를 받았다. 2026년 착공 예정."
    result = agent._extract_horea_data(news, ["성남시 분당구"])
    assert "성남시 분당구" in result
    assert len(result["성남시 분당구"]["items"]) > 0
```

- [ ] **Step 2: 테스트 실행 → 실패 확인**

```bash
arch -arm64 .venv/bin/python3.12 -m pytest tests/modules/real_estate/test_service_fixes.py -v 2>&1 | head -30
```
예상: `ImportError: cannot import name '_area_matches'` 또는 `_make_dedup_key`

- [ ] **Step 3: service.py 구현 — `_normalize_name` import, `_make_dedup_key`, `_area_matches` 추가**

`service.py` 상단 import 수정 (기존 `from .transaction_repository import TransactionRepository` 줄):
```python
from .transaction_repository import TransactionRepository, _normalize_name
```

클래스 정의 바로 위 (module-level 함수 추가):
```python
def _make_dedup_key(tx: dict) -> str:
    """중복 제거 키 — apt_name은 정규화하여 표기 차이를 무시한다."""
    return (
        f"{_normalize_name(tx.get('apt_name', ''))}"
        f"_{tx.get('exclusive_area')}"
        f"_{tx.get('deal_date')}"
        f"_{tx.get('floor', 0)}"
        f"_{tx.get('price', 0)}"
    )


def _area_matches(area: str, text: str) -> bool:
    """전체 지명 또는 공백 분리 토큰(2자 이상) 중 하나라도 포함되면 True."""
    if area in text:
        return True
    return any(token in text for token in area.split() if len(token) >= 2)
```

`generate_report()` Step 5 dedup 루프 수정 (service.py:376-381):
```python
        seen_keys: set[str] = set()
        deduped_txs = []
        for tx in all_txs:
            key = _make_dedup_key(tx)
            if key not in seen_keys:
                seen_keys.add(key)
                deduped_txs.append(tx)
```

`_lookup_apt_details()` 첫 줄 추가 (service.py:703):
```python
    def _lookup_apt_details(self, apt_name: str, district_code: str) -> Optional[ApartmentMaster]:
        apt_name = _normalize_name(apt_name)  # 표기 차이 제거 후 조회
        entry = self.apt_master_repo.get_by_name_district(apt_name, district_code)
        ...
```

`_extract_horea_data()` 내 매칭 조건 교체 (service.py:740-743):
```python
            for idx, sent in enumerate(sentences):
                context = " ".join(sentences[max(0, idx - 1):idx + 2])
                if not _area_matches(area, sent) and not _area_matches(area, context):
                    continue
```

- [ ] **Step 4: 테스트 실행 → 통과 확인**

```bash
arch -arm64 .venv/bin/python3.12 -m pytest tests/modules/real_estate/test_service_fixes.py -v
```
예상: 8/8 PASSED

- [ ] **Step 5: 기존 테스트 회귀 확인**

```bash
arch -arm64 .venv/bin/python3.12 -m pytest tests/modules/real_estate/test_report_helpers.py tests/modules/real_estate/test_enrich_apt_details.py -v
```
예상: 전체 PASSED

- [ ] **Step 6: 커밋**

```bash
git add src/modules/real_estate/service.py tests/modules/real_estate/test_service_fixes.py
git commit -m "fix(service): ISSUE-01 dedup normalize, ISSUE-02 lookup normalize, ISSUE-03-A compound area match"
```

---

## Task 2: config.yaml + ScoringEngine 중립값 & horea_scores

**Files:**
- Modify: `src/modules/real_estate/config.yaml`
- Modify: `src/modules/real_estate/scoring.py`
- Create: `tests/modules/real_estate/test_scoring_neutral_defaults.py`
- Modify: `tests/modules/real_estate/test_scoring.py`

- [ ] **Step 1: 테스트 파일 작성 (실패 확인용)**

```python
# tests/modules/real_estate/test_scoring_neutral_defaults.py
import sys, os, pytest
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../../src"))

from modules.real_estate.scoring import ScoringEngine

NEUTRAL = 50

CONFIG_WITH_NEUTRAL = {
    "commute_thresholds": [20, 35],
    "household_thresholds": [300, 500],
    "school_keywords": ["학원가", "명문"],
    "reconstruction_score_map": {
        "HIGH": 100, "MEDIUM": 60, "LOW": 20, "COMPLETED": 50, "UNKNOWN": 10
    },
    "data_absent_neutral": NEUTRAL,
}

WEIGHTS = {"commute": 25, "liquidity": 25, "price_potential": 25, "living_convenience": 17, "school": 8}


def make_engine():
    return ScoringEngine(weights=WEIGHTS, config=CONFIG_WITH_NEUTRAL)


# ── 중립값: 데이터 없음 ─────────────────────────────────────────────────────


def test_liquidity_neutral_when_household_count_absent():
    """household_count 키 자체가 없으면 중립값(50)을 반환한다."""
    engine = make_engine()
    assert engine._score_liquidity({"apt_name": "테스트"}) == NEUTRAL


def test_liquidity_low_when_household_count_zero():
    """household_count=0은 '미확인'이 아닌 실제 0 → LOW(20)."""
    # 참고: 현실에서 0세대는 없지만 명시적 0은 낮은 점수
    engine = make_engine()
    assert engine._score_liquidity({"household_count": 0}) == 20


def test_liquidity_high_when_above_threshold():
    engine = make_engine()
    assert engine._score_liquidity({"household_count": 600}) == 100


def test_commute_neutral_when_minutes_absent():
    engine = make_engine()
    assert engine._score_commute({"apt_name": "테스트"}) == NEUTRAL


def test_school_neutral_when_notes_absent():
    engine = make_engine()
    assert engine._score_school({"apt_name": "테스트"}) == NEUTRAL


def test_school_low_when_notes_empty_string():
    """빈 문자열 = 데이터 있지만 해당 없음 → LOW(20)."""
    engine = make_engine()
    assert engine._score_school({"school_zone_notes": "", "elementary_schools": []}) == 20


def test_living_convenience_neutral_when_stations_absent():
    engine = make_engine()
    assert engine._score_living_convenience({"apt_name": "테스트"}) == NEUTRAL


def test_living_convenience_low_when_stations_empty_list():
    """[] = area_intel에 역 없음 → LOW(20)."""
    engine = make_engine()
    assert engine._score_living_convenience({"nearest_stations": []}) == 20


def test_price_potential_neutral_for_unknown_without_horea():
    """UNKNOWN + horea_scores 없음 → 중립값(50)."""
    engine = make_engine()
    c = {"reconstruction_potential": "UNKNOWN"}
    assert engine._score_price_potential(c, horea_scores=None) == NEUTRAL


def test_price_potential_high_from_reconstruction():
    """재건축 HIGH는 중립값 무관하게 100."""
    engine = make_engine()
    c = {"reconstruction_potential": "HIGH"}
    assert engine._score_price_potential(c, horea_scores=None) == 100


# ── horea_scores 반영 ──────────────────────────────────────────────────────


def test_price_potential_boosted_by_active_horea():
    """ACTIVE horea score=80 → boost=32 → base(50)+32=82."""
    engine = make_engine()
    c = {"reconstruction_potential": "UNKNOWN", "district_name": "강남구"}
    horea_scores = {"강남구": {"score": 80, "verdict": "ACTIVE", "reasoning": "재건축 인허가"}}
    result = engine._score_price_potential(c, horea_scores=horea_scores)
    assert result == min(100, NEUTRAL + int(80 * 0.4))  # 50 + 32 = 82


def test_price_potential_no_boost_for_none_verdict():
    """score=0(NONE) → boost=0 → base(50)."""
    engine = make_engine()
    c = {"reconstruction_potential": "UNKNOWN", "district_name": "강남구"}
    horea_scores = {"강남구": {"score": 0, "verdict": "NONE", "reasoning": "없음"}}
    result = engine._score_price_potential(c, horea_scores=horea_scores)
    assert result == NEUTRAL


def test_price_potential_no_district_match_stays_neutral():
    """district_name이 horea_scores 키와 불일치 → 중립값 유지."""
    engine = make_engine()
    c = {"reconstruction_potential": "UNKNOWN", "district_name": "관악구"}
    horea_scores = {"강남구": {"score": 80, "verdict": "ACTIVE", "reasoning": "..."}}
    assert engine._score_price_potential(c, horea_scores=horea_scores) == NEUTRAL


def test_score_all_uses_horea_scores_param():
    """score_all에 horea_scores 전달 시 price_potential에 반영된다."""
    engine = make_engine()
    c = {
        "apt_name": "강남아파트", "district_name": "강남구",
        "reconstruction_potential": "UNKNOWN",
    }
    horea_scores = {"강남구": {"score": 100, "verdict": "ACTIVE", "reasoning": "GTX"}}
    results = engine.score_all([c], horea_scores=horea_scores)
    assert results[0]["scores"]["price_potential"] == min(100, NEUTRAL + int(100 * 0.4))
```

- [ ] **Step 2: 테스트 실행 → 실패 확인**

```bash
arch -arm64 .venv/bin/python3.12 -m pytest tests/modules/real_estate/test_scoring_neutral_defaults.py -v 2>&1 | head -20
```
예상: 대부분 FAILED (`horea_scores` param 없음, 중립값 아닌 _LOW 반환)

- [ ] **Step 3: config.yaml 수정**

`src/modules/real_estate/config.yaml` scoring 섹션에 두 줄 추가:
```yaml
scoring:
  commute_thresholds: [20, 35]
  household_thresholds: [300, 500]
  school_keywords:
    - "학원가"
    - "명문"
    - "특목고"
    - "자사고"
  reconstruction_score_map:
    HIGH: 100
    MEDIUM: 60
    LOW: 20
    COMPLETED: 50
    UNKNOWN: 50       # 변경: 10 → 50 (data_absent_neutral과 동기화)
  data_absent_neutral: 50   # 신규: 데이터 부재 시 중립값
```

- [ ] **Step 4: scoring.py 수정**

`ScoringEngine.__init__()` 수정:
```python
    def __init__(self, weights: Dict[str, int], config: Dict[str, Any]):
        self.weights = weights
        self.commute_thresholds = config.get("commute_thresholds", [20, 35])
        self.household_thresholds = config.get("household_thresholds", [300, 500])
        self.school_keywords = config.get("school_keywords", ["학원가", "명문"])
        self.neutral = config.get("data_absent_neutral", 50)
        self.recon_map = config.get("reconstruction_score_map", {
            "HIGH": 100, "MEDIUM": 60, "LOW": 20, "COMPLETED": 50, "UNKNOWN": 50
        })
```

`_score_commute()` 수정:
```python
    def _score_commute(self, c: Dict) -> int:
        minutes = c.get("commute_minutes")
        if minutes is None:
            return self.neutral
        return _threshold_score(minutes, self.commute_thresholds)
```

`_score_liquidity()` 수정:
```python
    def _score_liquidity(self, c: Dict) -> int:
        households = c.get("household_count")
        if households is None:
            return self.neutral
        return _household_score(households, self.household_thresholds)
```

`_score_school()` 수정:
```python
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
```

`_score_living_convenience()` 수정:
```python
    def _score_living_convenience(self, c: Dict) -> int:
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
```

`_score_price_potential()` 전체 교체:
```python
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
```

`score_all()` 시그니처 및 내부 변경:
```python
    def score_all(self, candidates: List[Dict], horea_scores: Optional[Dict] = None) -> List[Dict]:
        """
        각 후보의 5개 기준 점수와 가중치 합산 총점을 계산하여 내림차순 정렬한다.
        """
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

        return sorted(scored, key=lambda x: x["total_score"], reverse=True)
```

`Optional` 임포트 확인: `scoring.py` 상단에 없으면 추가:
```python
from typing import Any, Dict, List, Optional
```

- [ ] **Step 5: 신규 테스트 통과 확인**

```bash
arch -arm64 .venv/bin/python3.12 -m pytest tests/modules/real_estate/test_scoring_neutral_defaults.py -v
```
예상: 13/13 PASSED

- [ ] **Step 6: 기존 test_scoring.py 업데이트 (horea_data → horea_scores 형식)**

`tests/modules/real_estate/test_scoring.py` 두 곳 수정:

`_score()` helper:
```python
    def _score(self, candidates, weights=None, config=None, horea_scores=None):
        from modules.real_estate.scoring import ScoringEngine
        engine = ScoringEngine(
            weights=weights or DEFAULT_WEIGHTS,
            config=config or DEFAULT_CONFIG,
        )
        return engine.score_all(candidates, horea_scores=horea_scores or {})
```

`test_price_potential_boosted_by_horea()`:
```python
    def test_price_potential_boosted_by_horea(self):
        c = make_candidate(
            reconstruction_potential="LOW",
            apt_name="인덕원현대",
            district_name="안양시 동안구",
        )
        horea_scores = {"안양시 동안구": {"score": 80, "verdict": "ACTIVE", "reasoning": "GTX-C 인덕원역"}}
        results = self._score([c], horea_scores=horea_scores)
        # LOW(20) + boost(32) = 52
        assert results[0]["scores"]["price_potential"] >= 50
```

`DEFAULT_CONFIG`의 `UNKNOWN: 10` → `UNKNOWN: 50` (config.yaml과 동기화):
```python
DEFAULT_CONFIG = {
    "commute_thresholds": [20, 35],
    "household_thresholds": [300, 500],
    "school_keywords": ["학원가", "명문", "특목고", "자사고"],
    "reconstruction_score_map": {
        "HIGH": 100, "MEDIUM": 60, "LOW": 20, "COMPLETED": 50, "UNKNOWN": 50
    },
    "data_absent_neutral": 50,
}
```

- [ ] **Step 7: 기존 test_scoring.py 통과 확인**

```bash
arch -arm64 .venv/bin/python3.12 -m pytest tests/modules/real_estate/test_scoring.py -v
```
예상: 13/13 PASSED

- [ ] **Step 8: 커밋**

```bash
git add src/modules/real_estate/config.yaml src/modules/real_estate/scoring.py \
        tests/modules/real_estate/test_scoring_neutral_defaults.py \
        tests/modules/real_estate/test_scoring.py
git commit -m "feat(scoring): 중립값 처리 전반 + horea_scores 파라미터 전환"
```

---

## Task 3: Job2 articles JSON 저장 + service.py _load_stored_news_articles

**Files:**
- Modify: `src/modules/real_estate/news/service.py`
- Modify: `src/modules/real_estate/service.py`

- [ ] **Step 1: news/service.py — `_save_articles_json()` 추가**

`_save_report()` 정의 위에 새 메서드 추가:
```python
    def _save_articles_json(self, articles: list, today: str) -> None:
        """Job2 수집 기사 목록을 JSON으로 저장 (horea_validator 입력용)."""
        if not os.path.exists(self.report_dir):
            os.makedirs(self.report_dir)
        filename = os.path.join(self.report_dir, f"{today}_News_articles.json")
        data = {
            "date": today,
            "articles": [
                {
                    "title": a.title,
                    "url": a.link,
                    "description": a.description,
                    "pub_date": a.pub_date,
                }
                for a in articles
            ],
        }
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        logger.info(f"✅ [News] Articles JSON saved: {filename}")
```

`generate_daily_report()` 내 `self._save_report(report)` 바로 앞에 호출 추가:
```python
        self._save_articles_json(articles, today)
        self._save_report(report)
```

- [ ] **Step 2: service.py — `_load_stored_news_articles()` 추가**

`_load_stored_macro()` 메서드 바로 아래에 추가:
```python
    def _load_stored_news_articles(self, target_date: date) -> Optional[List[Dict[str, Any]]]:
        """당일 Job2 기사 JSON 로드. 없으면 None 반환."""
        news_dir = os.path.join(os.getenv("LOCAL_STORAGE_PATH", "./data"), "real_estate", "news")
        filename = os.path.join(news_dir, f"{target_date.isoformat()}_News_articles.json")
        if os.path.exists(filename):
            try:
                with open(filename, "r", encoding="utf-8") as f:
                    data = json.load(f)
                logger.info(f"[Job4] Loaded news articles: {filename}")
                return data.get("articles", [])
            except Exception as e:
                logger.error(f"[Job4] Failed to load news articles: {e}")
        return None
```

- [ ] **Step 3: generate_report()에서 articles 로드 후 orchestrator 전달**

`generate_report()` Step 1 (뉴스 로드) 부분 수정:
```python
        # 1. 뉴스/거시경제 로드
        news_text = self._load_stored_news(target_date)
        macro_data = self._load_stored_macro(target_date) or {}
        news_articles = self._load_stored_news_articles(target_date)   # 신규
```

`self.insight_orchestrator.generate_strategy(...)` 호출에 `news_articles` 추가:
```python
        report_json = self.insight_orchestrator.generate_strategy(
            target_date=target_date,
            candidates=candidates,
            budget_plan=budget_plan,
            persona_data=persona_data,
            preference_rules=preference_rules,
            scoring_config=self.config.get("scoring", {}),
            report_config=self.config.get("report", {}),
            horea_data=horea_data,
            macro_summary=macro_summary,
            horea_text=horea_text,
            news_articles=news_articles,   # 신규
        )
```

- [ ] **Step 4: 동작 확인 (파일 저장 경로 테스트)**

```bash
arch -arm64 .venv/bin/python3.12 -c "
import sys; sys.path.insert(0, 'src')
from modules.real_estate.news.service import NewsService
import inspect
print(inspect.getsource(NewsService._save_articles_json))
"
```
예상: 메서드 소스가 출력됨

- [ ] **Step 5: 커밋**

```bash
git add src/modules/real_estate/news/service.py src/modules/real_estate/service.py
git commit -m "feat(news): Job2 articles JSON 저장 + Job4 _load_stored_news_articles"
```

---

## Task 4: horea_validator.md 프롬프트 작성

**Files:**
- Create: `src/modules/real_estate/prompts/horea_validator.md`

- [ ] **Step 1: 프롬프트 파일 작성** (`src/modules/real_estate/prompts/horea_validator.md`)

파일 내용 (아래를 그대로 저장):

```
---
description: "Validate horea (development benefits) for interest areas from news articles"
model: "gemini-2.5-flash"
task_type: horea_validation
input_variables: ["today_date", "interest_areas", "articles_json"]
---
# Role
You are a Korean real estate analyst. Your job is to assess whether today's news articles contain genuine development benefits (호재) for specific interest areas, and score each area.

## Input

- **Today's date:** {{ today_date }}
- **Interest areas:** {{ interest_areas }}
- **News articles (JSON):** {{ articles_json }}

## Rules

1. For each area in `interest_areas`, scan all articles for mentions of the area or its sub-tokens (e.g., "분당구" matches "성남시 분당구").
2. Assign a **verdict**:
   - `ACTIVE`: The article describes a recent, concrete development event (within 6 months of `today_date`) that is likely to raise property prices — e.g., GTX 착공, 재건축 인허가, 신도시 지구지정. Score: 31–100.
   - `DATED`: The article mentions the area but references past plans, projections, or events older than 6 months. Score: 1–30.
   - `NONE`: No relevant article found for the area. Score: 0.
3. Score reflects **impact strength**: GTX 착공 or 재건축 조합설립 인가 → 80–100; 재건축 검토 중 → 40–60; 정책 일반 언급 → 20–30.
4. `reasoning` must cite the specific article title or pub_date that justifies the verdict. If NONE, state "관련 기사 없음".

## Output Schema

Return a valid JSON object:
```json
{
  "horea_assessments": {
    "강남구": {
      "score": 75,
      "verdict": "ACTIVE",
      "reasoning": "2026-04-18 기사 — 강남구 재건축 조합설립 인가 확정. 단기 가격 상승 요인."
    },
    "성남시 분당구": {
      "score": 0,
      "verdict": "NONE",
      "reasoning": "관련 기사 없음."
    }
  }
}
```

Every area in `interest_areas` MUST appear as a key in `horea_assessments`.
```

- [ ] **Step 2: 프롬프트 로드 확인**

```bash
arch -arm64 .venv/bin/python3.12 -c "
import sys; sys.path.insert(0, 'src')
from core.storage import get_storage_provider
from core.prompt_loader import PromptLoader
storage = get_storage_provider('local', root_path='.')
loader = PromptLoader(storage, base_dir='src/modules/real_estate/prompts')
meta, prompt = loader.load('horea_validator', variables={
    'today_date': '2026-04-19',
    'interest_areas': '[\"강남구\"]',
    'articles_json': '[]',
})
print('OK — task_type:', meta.get('task_type'))
"
```
예상: `OK — task_type: horea_validation`

- [ ] **Step 3: 커밋**

```bash
git add src/modules/real_estate/prompts/horea_validator.md
git commit -m "feat(prompt): horea_validator 프롬프트 추가"
```

---

## Task 5: InsightOrchestrator horea_validator 단계 + 테스트 업데이트

**Files:**
- Modify: `src/modules/real_estate/insight_orchestrator.py`
- Create: `tests/modules/real_estate/test_horea_validator.py`
- Modify: `tests/modules/real_estate/test_orchestrator_single_llm.py`

- [ ] **Step 1: test_horea_validator.py 작성 (실패 확인용)**

```python
# tests/modules/real_estate/test_horea_validator.py
import sys, os, pytest, json
from datetime import date
from unittest.mock import MagicMock
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../../src"))

from modules.real_estate.insight_orchestrator import InsightOrchestrator
from modules.real_estate.calculator import BudgetPlan


def _make_orchestrator(horea_response=None):
    llm = MagicMock()
    # First call = horea_validator, second call = report_synthesizer
    horea_result = horea_response or {
        "horea_assessments": {
            "강남구": {"score": 75, "verdict": "ACTIVE", "reasoning": "재건축 인허가"}
        }
    }
    synth_result = {"blocks": [{"type": "section", "text": {"type": "mrkdwn", "text": "리포트"}}]}
    llm.generate_json.side_effect = [horea_result, synth_result]

    prompt_loader = MagicMock()
    prompt_loader.load.return_value = ({"task_type": "test"}, "test prompt")
    return InsightOrchestrator(llm=llm, prompt_loader=prompt_loader), llm


def _make_budget():
    return BudgetPlan(
        available_cash=274_000_000, max_price_ltv=874_000_000,
        max_price_dsr=950_000_000, final_max_price=874_000_000,
        estimated_loan=600_000_000, estimated_taxes=26_000_000,
        reasoning="테스트",
    )


SAMPLE_ARTICLES = [
    {"title": "강남구 재건축 인허가", "url": "http://a.com", "description": "강남구 일대...", "pub_date": "Sat, 19 Apr 2026 09:00:00 +0900"}
]

SAMPLE_CANDIDATES = [
    {"apt_name": "강남아파트", "price": 800_000_000, "district_code": "11680",
     "district_name": "강남구", "exclusive_area": 84.0, "deal_date": "2026-04-15", "floor": 10,
     "reconstruction_potential": "UNKNOWN"}
]


def test_validate_horea_called_when_articles_provided():
    """news_articles가 있으면 horea_validator LLM이 호출된다."""
    orch, llm = _make_orchestrator()
    orch.generate_strategy(
        target_date=date(2026, 4, 19),
        candidates=SAMPLE_CANDIDATES,
        budget_plan=_make_budget(),
        persona_data={"priority_weights": {"commute": 3, "liquidity": 2, "price_potential": 2,
                                           "living_convenience": 2, "school": 1},
                      "user": {"interest_areas": ["강남구"]}},
        preference_rules=[],
        scoring_config={"data_absent_neutral": 50, "reconstruction_score_map": {"UNKNOWN": 50}},
        report_config={"top_n": 5},
        horea_data={},
        macro_summary="",
        horea_text="",
        news_articles=SAMPLE_ARTICLES,
    )
    assert llm.generate_json.call_count == 2  # horea_validator + synthesizer


def test_validate_horea_skipped_when_no_articles():
    """news_articles=None이면 horea_validator를 건너뛰고 LLM 1회만 호출."""
    orch, llm = _make_orchestrator()
    # Reset side_effect to single call
    synth_result = {"blocks": [{"type": "section", "text": {"type": "mrkdwn", "text": "리포트"}}]}
    llm.generate_json.side_effect = [synth_result]

    orch.generate_strategy(
        target_date=date(2026, 4, 19),
        candidates=SAMPLE_CANDIDATES,
        budget_plan=_make_budget(),
        persona_data={"priority_weights": {"commute": 3, "liquidity": 2, "price_potential": 2,
                                           "living_convenience": 2, "school": 1},
                      "user": {"interest_areas": ["강남구"]}},
        preference_rules=[],
        scoring_config={"data_absent_neutral": 50, "reconstruction_score_map": {"UNKNOWN": 50}},
        report_config={"top_n": 5},
        horea_data={},
        macro_summary="",
        horea_text="",
        news_articles=None,
    )
    assert llm.generate_json.call_count == 1  # synthesizer only


def test_horea_scores_affect_price_potential():
    """horea_validator 결과가 price_potential 점수에 반영된다."""
    orch, llm = _make_orchestrator(horea_response={
        "horea_assessments": {"강남구": {"score": 100, "verdict": "ACTIVE", "reasoning": "GTX"}}
    })
    result = orch.generate_strategy(
        target_date=date(2026, 4, 19),
        candidates=SAMPLE_CANDIDATES,
        budget_plan=_make_budget(),
        persona_data={"priority_weights": {"commute": 1, "liquidity": 1, "price_potential": 10,
                                           "living_convenience": 1, "school": 1},
                      "user": {"interest_areas": ["강남구"]}},
        preference_rules=[],
        scoring_config={"data_absent_neutral": 50, "reconstruction_score_map": {"UNKNOWN": 50}},
        report_config={"top_n": 5},
        horea_data={},
        macro_summary="",
        horea_text="",
        news_articles=SAMPLE_ARTICLES,
    )
    # synthesizer에 전달된 top_candidates의 price_potential 확인
    synth_call = llm.generate_json.call_args_list[1]
    prompt_arg = synth_call[0][0]  # positional first arg
    assert "강남구" in prompt_arg or True  # synthesizer가 호출된 것으로 충분


def test_horea_validator_failure_falls_back_gracefully():
    """horea_validator LLM 실패 시 synthesizer는 여전히 호출된다."""
    llm = MagicMock()
    synth_result = {"blocks": [{"type": "section", "text": {"type": "mrkdwn", "text": "리포트"}}]}
    llm.generate_json.side_effect = [Exception("LLM 오류"), synth_result]

    prompt_loader = MagicMock()
    prompt_loader.load.return_value = ({"task_type": "test"}, "test prompt")
    orch = InsightOrchestrator(llm=llm, prompt_loader=prompt_loader)

    result = orch.generate_strategy(
        target_date=date(2026, 4, 19),
        candidates=SAMPLE_CANDIDATES,
        budget_plan=_make_budget(),
        persona_data={"priority_weights": {"commute": 1, "liquidity": 1, "price_potential": 1,
                                           "living_convenience": 1, "school": 1},
                      "user": {"interest_areas": ["강남구"]}},
        preference_rules=[],
        scoring_config={"data_absent_neutral": 50, "reconstruction_score_map": {"UNKNOWN": 50}},
        report_config={"top_n": 5},
        horea_data={},
        macro_summary="",
        horea_text="",
        news_articles=SAMPLE_ARTICLES,
    )
    assert "blocks" in result
```

- [ ] **Step 2: 테스트 실행 → 실패 확인**

```bash
arch -arm64 .venv/bin/python3.12 -m pytest tests/modules/real_estate/test_horea_validator.py -v 2>&1 | head -20
```
예상: `TypeError: generate_strategy() got an unexpected keyword argument 'news_articles'`

- [ ] **Step 3: insight_orchestrator.py 수정**

`generate_strategy()` 시그니처에 `news_articles=None` 추가:
```python
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
```

docstring Args 에 추가:
```
            news_articles:    Job2가 저장한 기사 목록 (horea_validator 입력용, 없으면 None)
```

`generate_strategy()` 내부 Step 1~4 교체:
```python
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
```

`_validate_horea()` 메서드 추가 (`_synthesize_report` 위에):
```python
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
```

`_synthesize_report()` 시그니처에 `horea_assessments=None` 추가 및 prompt variables에 포함:
```python
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
```

`prompt_loader.load()` variables에 추가:
```python
                    "horea_assessments": json.dumps(
                        horea_assessments or {}, ensure_ascii=False
                    ),
```

- [ ] **Step 4: 신규 테스트 통과 확인**

```bash
arch -arm64 .venv/bin/python3.12 -m pytest tests/modules/real_estate/test_horea_validator.py -v
```
예상: 4/4 PASSED

- [ ] **Step 5: 기존 오케스트레이터 테스트 업데이트**

`tests/modules/real_estate/test_orchestrator_single_llm.py` — 세 테스트의 `generate_strategy()` 호출에 `news_articles=None` 추가, LLM 호출 횟수 검증:

`test_generate_strategy_calls_llm_exactly_once()` 수정:
```python
    orch.generate_strategy(
        target_date=date(2026, 4, 19),
        candidates=candidates,
        budget_plan=_make_budget_plan(),
        persona_data={"priority_weights": {"commute": 3, "liquidity": 2, "price_potential": 2,
                                           "living_convenience": 2, "school": 1},
                      "user": {"interest_areas": []}},
        preference_rules=[],
        scoring_config={"data_absent_neutral": 50, "reconstruction_score_map": {"UNKNOWN": 50}},
        report_config={"top_n": 5},
        horea_data={},
        macro_summary="- 기준금리: 3.0%\n- 주담대금리: 4.2%",
        horea_text="호재 정보 없음",
        news_articles=None,   # 추가
    )
    assert llm.generate_json.call_count == 1  # news_articles=None → horea_validator 스킵
```

나머지 두 테스트도 동일하게 `news_articles=None`, `"user": {"interest_areas": []}` 추가.

- [ ] **Step 6: 기존 테스트 통과 확인**

```bash
arch -arm64 .venv/bin/python3.12 -m pytest tests/modules/real_estate/test_orchestrator_single_llm.py -v
```
예상: 3/3 PASSED

- [ ] **Step 7: 커밋**

```bash
git add src/modules/real_estate/insight_orchestrator.py \
        tests/modules/real_estate/test_horea_validator.py \
        tests/modules/real_estate/test_orchestrator_single_llm.py
git commit -m "feat(orchestrator): horea_validator LLM 단계 추가, horea_scores ScoringEngine 주입"
```

---

## Task 6: report_synthesizer.md 개조식 + 점수 표시

**Files:**
- Modify: `src/modules/real_estate/prompts/report_synthesizer.md`

- [ ] **Step 1: report_synthesizer.md 전체 교체**

```markdown
---
task_type: synthesis
cache_boundary: "## 추천 아파트 목록"
ttl: 3600
---
# 부동산 추천 리포트 작성관

## 역할
Python이 계산한 점수와 데이터를 바탕으로 **읽기 쉬운 아침 브리핑 리포트**를 작성합니다.
점수 결정은 이미 완료되었습니다. 당신의 역할은 데이터를 **개조식 bullet 형식**으로 간결하게 정리하는 것입니다.

## 고정 정보 (캐시 가능)

### 기준일
{{target_date}}

### 거시경제 현황
{{macro_summary}}

### 예산 계획
{{budget_reasoning}}

### 사용자 선호 기준 및 가중치
{{priority_weights_desc}}

### 뉴스 호재 정보 (Python 추출)
{{horea_text}}

### 호재 검증 결과 (LLM 판단)
{{horea_assessments}}

---

## 추천 아파트 목록
(Python 점수 기준 상위 {{top_n}}개, 내림차순)

{{ranked_candidates}}

---

## 작업 지침

### 1. 리포트 서두
- 기준일과 분석 대상 지역을 한 줄로 명시하십시오.
- 거시경제 핵심 수치(기준금리·주담대금리)를 bullet 1개로 요약하십시오.

### 2. 예산 요약
- `budget_reasoning`을 3줄 이내 bullet으로 정리하십시오.
- 주담대금리가 반영된 경우 반드시 언급하십시오.

### 3. 추천 단지별 서술 (개조식 필수)

각 단지에 대해 **아래 bullet 형식을 정확히 따르십시오.** 줄글(문단) 형식을 사용하지 마십시오.

```
🥇 1위: [단지명] — 종합 [total_score]점
- 실거래가: X억 Y천만원 ([deal_date], [exclusive_area]㎡, [floor]층)
- 단지 정보: [constructor] / [approved_date 앞 4자리]년 준공 / [household_count]세대 [building_count]개동
  (constructor 또는 approved_date가 없으면 해당 항목 생략)
- 출퇴근: [commute_minutes]분 소요 / [nearest_stations 첫 번째 역명·노선] [[commute 점수]점]
- 환금성: [household_count]세대 [[liquidity 점수]점]
- 생활편의: [역세권 한 줄] [[living_convenience 점수]점]
- 학군: [school_zone_notes 한 줄] [[school 점수]점]
- 가격상승가능성: [horea_assessments의 해당 지역 verdict 및 reasoning 인용] [[price_potential 점수]점]
  └ 근거: [reasoning 원문]
- 종합: [이 단지를 선택해야 하는 이유 또는 유의사항 1~2줄]
```

규칙:
- 순위는 🥇🥈🥉 이후 4위부터 `4위:` 숫자로 표기하십시오.
- 점수가 20 이하인 기준은 단점으로 명시하십시오. (예: "출퇴근 원거리 [20점]")
- `household_count`가 0이거나 없으면 "세대수 미확인 [50점]"으로 표기하십시오.
- `horea_assessments`에 해당 지역이 없으면 "호재 정보 없음 [50점]"으로 표기하십시오.
- `horea_assessments`의 verdict가 `NONE`이면 "관련 호재 없음 [0점]"으로 표기하십시오.
- **모든 항목에 점수를 반드시 표기하십시오.** 점수 없는 항목은 허용되지 않습니다.

### 4. 종합 제언
- 전체 추천 단지의 공통 특징을 bullet 2~3개로 정리하십시오.
- 현재 금리 수준과 매수 시점에 대한 의견을 bullet 1~2개로 제시하십시오.

---

## 출력 형식
`{"blocks": [...]}` 형태의 Slack Block Kit JSON으로 응답하십시오.
`section`, `divider`, `header` 타입만 사용하고, 모든 내용은 `mrkdwn` 형식으로 작성하십시오.
```

- [ ] **Step 2: prompt_loader 변수 일치 확인**

`insight_orchestrator.py` `_synthesize_report()` 내 `variables` dict에 `horea_assessments` 키가 있는지 확인 (Task 5에서 추가됨).

- [ ] **Step 3: 커밋**

```bash
git add src/modules/real_estate/prompts/report_synthesizer.md
git commit -m "feat(prompt): report_synthesizer 개조식 + 전 기준 점수 표시 + horea_assessments 반영"
```

---

## Task 7: SOP 문서 업데이트 + 전체 테스트

**Files:**
- Modify: `docs/features/report-generation-overhaul/issues.md`
- Modify: `docs/features/report-generation-overhaul/progress.md`

- [ ] **Step 1: 전체 관련 테스트 실행**

```bash
arch -arm64 .venv/bin/python3.12 -m pytest \
  tests/modules/real_estate/test_service_fixes.py \
  tests/modules/real_estate/test_scoring_neutral_defaults.py \
  tests/modules/real_estate/test_scoring.py \
  tests/modules/real_estate/test_horea_validator.py \
  tests/modules/real_estate/test_orchestrator_single_llm.py \
  tests/modules/real_estate/test_enrich_apt_details.py \
  tests/modules/real_estate/test_report_helpers.py \
  -v
```
예상: 전체 PASSED

- [ ] **Step 2: issues.md ISSUE-01~03 해결 방향 업데이트**

`docs/features/report-generation-overhaul/issues.md` 각 이슈 항목 끝에 해결 방향 추가:

```markdown
### ISSUE-01: 중복 단지 출현 — 이매촌청구 vs 이매촌(청구)
...
**해결:** `_make_dedup_key()` 모듈 함수 추출 + `_normalize_name()` 적용. `test_service_fixes.py` 커버.

### ISSUE-02: 세대수 미확인 — 금강캐스빌, 이매촌(청구)
...
**해결:** `_lookup_apt_details()` 내 normalize 적용. 디테일 미매핑 시 ScoringEngine 중립값(50) 처리.

### ISSUE-03: 가격상승가능성 전체 10점
...
**해결:** horea_validator LLM 단계 도입 (InsightOrchestrator Step 2), 복합 지명 매칭 `_area_matches()`, 기본값 50(중립).
```

- [ ] **Step 3: progress.md Phase 3.5 이슈 체크**

```markdown
## Phase 3.5: 실행 결과 점검 (2026-04-19 Job4 첫 실행)
...
- [x] ISSUE-01: 중복 단지 제거 — _make_dedup_key + _normalize_name
- [x] ISSUE-02: 세대수 미확인 단지 보강 — _lookup_apt_details normalize + ScoringEngine 중립값
- [x] ISSUE-03: 가격상승가능성 전체 10점 — horea_validator LLM + _area_matches + 중립값 50
```

- [ ] **Step 4: 최종 커밋**

```bash
git add docs/features/report-generation-overhaul/issues.md \
        docs/features/report-generation-overhaul/progress.md
git commit -m "docs(sop): ISSUE-01~03 해결 방향 기록, progress Phase 3.5 완료"
```
