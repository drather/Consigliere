# POI 입지 점수 DB 저장 연결 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** `DailyReportOrchestrator`가 LocationScore를 계산한 직후 `LocationRepository.upsert_score()`를 호출해 DB에 저장하여, 대시보드 단지 클릭 시 실거주/투자 점수 카드가 정상 표시되도록 한다.

**Architecture:** `DailyReportOrchestrator.__init__`에 `LocationRepository` 인스턴스를 `self._loc_repo`로 초기화하고, 기존 Step 4 scorer 루프에서 `scorer.score(c)` 호출 직후 `self._loc_repo.upsert_score(loc_score)`를 추가한다. `report_orchestrator.py`에 이미 존재하는 동일한 패턴을 `daily_report_orchestrator.py`에도 적용하는 것이 전부다.

**Tech Stack:** Python 3.12, SQLite, pytest, unittest.mock

---

## 파일 구조

```
수정:
  src/modules/real_estate/daily_report/daily_report_orchestrator.py
    - import LocationRepository 추가 (line 20 근처)
    - __init__에 self._loc_repo = LocationRepository(self._db_path) 추가 (line 151 근처)
    - Step 4 scorer 루프: upsert_score 호출 추가 (line 204 근처)

신규:
  tests/modules/real_estate/daily_report/test_daily_report_orchestrator_location.py
    - DailyReportOrchestrator가 generate() 시 upsert_score()를 호출하는지 검증
    - LocationRepository를 mock으로 주입해 DB 의존성 없이 단위 테스트

참고 (수정 없음):
  src/modules/real_estate/location/location_repository.py  (LocationRepository.upsert_score 구현)
  src/modules/real_estate/location/location_scorer.py      (LocationScore dataclass, LocationScorer)
  tests/modules/real_estate/daily_report/test_daily_report_orchestrator.py  (기존 테스트 패턴 참고)
```

---

## Task 1: 실패하는 테스트 작성 (TDD Red)

**Files:**
- Create: `tests/modules/real_estate/daily_report/test_daily_report_orchestrator_location.py`

- [ ] **Step 1: 테스트 파일 작성**

`DailyReportOrchestrator`가 `generate()` 실행 시 `LocationRepository.upsert_score()`를 한 번 이상 호출하는지 검증한다.
기존 `test_daily_report_orchestrator.py`의 `_make_aggregated`, `_make_orchestrator` 헬퍼를 참고하되, `_loc_repo`를 mock으로 교체해 DB 없이 검증한다.

```python
# tests/modules/real_estate/daily_report/test_daily_report_orchestrator_location.py
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../../../src"))

from datetime import date
from unittest.mock import MagicMock, patch, call

from modules.real_estate.daily_report.daily_report_orchestrator import DailyReportOrchestrator


def _make_candidate(name: str = "래미안") -> dict:
    return {
        "apt_master_id": 1,
        "apt_name": name,
        "district_code": "11680",
        "sigungu": "강남구",
        "complex_code": "CC001",
        "recent_tx_count": 3,
        "avg_recent_price": 280_000_000,
        "price_change_pct": 2.5,
        "exclusive_area": 84.0,
        "household_count": 1200,
        "composite_score": 0.8,
        "road_address": None,
        "pnu": None,
        "_recent_tx_points": [],
    }


def _make_orchestrator(tmp_path) -> DailyReportOrchestrator:
    mock_llm = MagicMock()
    mock_llm.generate_json.return_value = {
        "market_bullets": ["강남권 거래 활발"],
        "candidate_insights": [
            {
                "apt_name": "래미안",
                "trading_bullets": [],
                "characteristics_bullets": [],
                "strategy_bullets": [],
            }
        ],
    }
    mock_prompt_loader = MagicMock()
    mock_prompt_loader.load.return_value = ({"task_type": "REAL_ESTATE_ANALYSIS"}, "prompt text")
    mock_aggregator = MagicMock()
    mock_aggregator.aggregate.return_value = [_make_candidate()]
    mock_repo = MagicMock()
    mock_repo.save.return_value = str(tmp_path / "daily.md")

    return DailyReportOrchestrator(
        llm=mock_llm,
        prompt_loader=mock_prompt_loader,
        aggregator=mock_aggregator,
        report_repo=mock_repo,
        db_path=str(tmp_path / "re.db"),
    )


class TestLocationScorePersistence:
    def test_upsert_score_called_after_scoring(self, tmp_path):
        """generate() 실행 후 LocationRepository.upsert_score가 최소 1회 호출되어야 한다."""
        orch = _make_orchestrator(tmp_path)
        mock_loc_repo = MagicMock()
        orch._loc_repo = mock_loc_repo

        orch.generate(
            target_date=date(2026, 5, 27),
            days=3,
            top_k=5,
            persona={},
            macro_summary="기준금리: 3.5%",
        )

        mock_loc_repo.upsert_score.assert_called()

    def test_upsert_score_called_once_per_candidate(self, tmp_path):
        """후보 단지 수만큼 upsert_score가 호출되어야 한다."""
        orch = _make_orchestrator(tmp_path)
        # 후보 3개로 설정
        orch._aggregator.aggregate.return_value = [
            _make_candidate("래미안"),
            _make_candidate("자이"),
            _make_candidate("힐스테이트"),
        ]
        mock_loc_repo = MagicMock()
        orch._loc_repo = mock_loc_repo

        orch.generate(
            target_date=date(2026, 5, 27),
            days=3,
            top_k=5,
            persona={},
            macro_summary="",
        )

        assert mock_loc_repo.upsert_score.call_count == 3

    def test_upsert_score_receives_location_score_object(self, tmp_path):
        """upsert_score에 전달되는 인자가 complex_code 속성을 가진 LocationScore여야 한다."""
        from modules.real_estate.location.location_scorer import LocationScore

        orch = _make_orchestrator(tmp_path)
        mock_loc_repo = MagicMock()
        orch._loc_repo = mock_loc_repo

        orch.generate(
            target_date=date(2026, 5, 27),
            days=3,
            top_k=5,
            persona={},
            macro_summary="",
        )

        # upsert_score가 호출됐다면, 첫 번째 호출의 인자 확인
        if mock_loc_repo.upsert_score.called:
            arg = mock_loc_repo.upsert_score.call_args_list[0].args[0]
            assert isinstance(arg, LocationScore)
            assert hasattr(arg, "complex_code")
            assert hasattr(arg, "residential_total")
            assert hasattr(arg, "investment_total")

    def test_loc_repo_initialized_in_constructor(self, tmp_path):
        """DailyReportOrchestrator가 생성될 때 _loc_repo 속성이 존재해야 한다."""
        orch = _make_orchestrator(tmp_path)
        assert hasattr(orch, "_loc_repo")

    def test_upsert_failure_does_not_break_report(self, tmp_path):
        """upsert_score가 예외를 던져도 generate()는 DailyReport를 정상 반환해야 한다."""
        from modules.real_estate.daily_report.models import DailyReport

        orch = _make_orchestrator(tmp_path)
        mock_loc_repo = MagicMock()
        mock_loc_repo.upsert_score.side_effect = Exception("DB 오류")
        orch._loc_repo = mock_loc_repo

        result = orch.generate(
            target_date=date(2026, 5, 27),
            days=3,
            top_k=5,
            persona={},
            macro_summary="",
        )

        assert isinstance(result, DailyReport)
```

- [ ] **Step 2: 테스트 실패 확인**

```bash
cd /Users/kks/Desktop/Laboratory/Consigliere
arch -arm64 .venv/bin/python3.12 -m pytest tests/modules/real_estate/daily_report/test_daily_report_orchestrator_location.py -v
```

기대 결과:
```
FAILED test_upsert_score_called_after_scoring - AssertionError: Expected 'upsert_score' to have been called.
FAILED test_upsert_score_called_once_per_candidate - ...
FAILED test_upsert_score_receives_location_score_object - ...
FAILED test_loc_repo_initialized_in_constructor - AttributeError: 'DailyReportOrchestrator' object has no attribute '_loc_repo'
FAILED test_upsert_failure_does_not_break_report - ...
```

- [ ] **Step 3: 커밋 (Red 상태 보존)**

```bash
git add tests/modules/real_estate/daily_report/test_daily_report_orchestrator_location.py
git commit -m "test(location): DailyReportOrchestrator upsert_score 호출 검증 테스트 추가 (Red)"
```

---

## Task 2: 구현 — DailyReportOrchestrator에 LocationRepository 연결

**Files:**
- Modify: `src/modules/real_estate/daily_report/daily_report_orchestrator.py`

### Step 1: 현재 파일 상태 파악

```bash
grep -n "from modules.real_estate.location\|LocationRepository\|loc_repo\|upsert" \
  src/modules/real_estate/daily_report/daily_report_orchestrator.py
```

기대 결과: 아무것도 출력되지 않아야 한다 (현재 없음).

- [ ] **Step 2: import 추가**

파일 상단의 `from modules.real_estate.location.location_scorer import LocationScorer` 줄 (line 20 근처) 바로 아래에 import 추가:

현재 파일 내용 (확인 후 정확한 위치 찾기):
```python
from modules.real_estate.location.location_scorer import LocationScorer
```

이 줄 바로 뒤에 다음 줄 추가:
```python
from modules.real_estate.location.location_repository import LocationRepository
```

- [ ] **Step 3: `__init__`에 `_loc_repo` 초기화 추가**

`__init__` 생성자 마지막 줄 (`self._supply_analyzer = supply_analyzer`) 바로 뒤에 추가:

현재 마지막 줄:
```python
        self._supply_analyzer = supply_analyzer
```

추가 후:
```python
        self._supply_analyzer = supply_analyzer
        self._loc_repo = LocationRepository(self._db_path)
```

- [ ] **Step 4: Step 4 scorer 루프에 `upsert_score` 추가**

현재 코드 (line 199~206):
```python
        # Step 4. LocationScorer 실행 — evidence 포함 DimensionResult 생성
        scorer = _load_scorer()
        if scorer:
            for c in candidates:
                try:
                    c["_location_score"] = scorer.score(c)
                except Exception as e:
                    logger.warning("[DailyOrchestrator] scorer.score 실패 %s: %s", c.get("apt_name"), e)
```

이 블록을 아래로 교체:
```python
        # Step 4. LocationScorer 실행 — evidence 포함 DimensionResult 생성
        scorer = _load_scorer()
        if scorer:
            for c in candidates:
                try:
                    loc_score = scorer.score(c)
                    c["_location_score"] = loc_score
                    self._loc_repo.upsert_score(loc_score)
                except Exception as e:
                    logger.warning("[DailyOrchestrator] scorer.score 실패 %s: %s", c.get("apt_name"), e)
```

변경점: `scorer.score(c)`의 반환값을 `loc_score` 변수에 저장하고, `c["_location_score"]`에 할당한 뒤 `self._loc_repo.upsert_score(loc_score)` 호출 추가.

- [ ] **Step 5: 테스트 통과 확인**

```bash
arch -arm64 .venv/bin/python3.12 -m pytest tests/modules/real_estate/daily_report/test_daily_report_orchestrator_location.py -v
```

기대 결과:
```
PASSED test_upsert_score_called_after_scoring
PASSED test_upsert_score_called_once_per_candidate
PASSED test_upsert_score_receives_location_score_object
PASSED test_loc_repo_initialized_in_constructor
PASSED test_upsert_failure_does_not_break_report
5 passed in ...
```

- [ ] **Step 6: 기존 테스트 회귀 없음 확인**

```bash
arch -arm64 .venv/bin/python3.12 -m pytest tests/modules/real_estate/daily_report/ -v
```

기대 결과: 기존 테스트 포함 전부 PASS

- [ ] **Step 7: location 패키지 테스트 회귀 없음 확인**

```bash
arch -arm64 .venv/bin/python3.12 -m pytest tests/modules/real_estate/location/ -v
```

기대 결과: 63 passed

- [ ] **Step 8: 커밋 (Green)**

```bash
git add src/modules/real_estate/daily_report/daily_report_orchestrator.py
git commit -m "feat(location): DailyReportOrchestrator → LocationRepository upsert_score 연결"
```

---

## Task 3: 전체 테스트 + SOLID Review

**Files:**
- 수정 없음 (검증만)

- [ ] **Step 1: 전체 단위 테스트 실행**

```bash
arch -arm64 .venv/bin/python3.12 -m pytest tests/ -v --ignore=tests/e2e -x
```

기대 결과: 전체 PASS (기존 통과 수 + 신규 5개)

- [ ] **Step 2: SOLID Review 체크리스트**

| 항목 | 확인 |
|------|------|
| SRP: `DailyReportOrchestrator`가 점수 저장 책임도 갖게 됐지만, 이는 기존 `report_orchestrator.py`와 동일한 패턴 | ✅ |
| OCP: `LocationRepository` 인터페이스 변경 없음 | ✅ |
| DIP: `LocationRepository` concrete class 직접 주입이지만, `_loc_repo` 속성 교체로 테스트 가능 | ✅ |
| Zero Hardcoding: `db_path`는 생성자 파라미터로 config에서 주입됨 | ✅ |
| 에러 처리: `upsert_score` 실패가 기존 try/except 블록 내에 있어 리포트 생성을 중단시키지 않음 | ✅ |

---

## Task 4: SOP 문서 작성

**Files:**
- Create: `docs/features/poi-location-db-persist/spec.md`
- Create: `docs/features/poi-location-db-persist/progress.md`
- Create: `docs/features/poi-location-db-persist/result.md`

- [ ] **Step 1: 피처 문서 디렉토리 생성**

```bash
mkdir -p docs/features/poi-location-db-persist
```

- [ ] **Step 2: spec.md 작성**

```bash
cat > docs/features/poi-location-db-persist/spec.md << 'EOF'
# POI 입지 점수 DB 저장 연결

**작성일:** 2026-05-27  
**브랜치:** feature/poi-location-db-persist

## 목표

`DailyReportOrchestrator.generate()` 실행 시 LocationScore가 `location_scores` 테이블에 저장되어
대시보드 단지 클릭 시 실거주/투자 점수 카드가 정상 표시되도록 한다.

## 배경

- `location/` 패키지 및 `LocationScorer`는 구현 완료 (63 tests PASS)
- `report_orchestrator.py`에는 `upsert_score()` 호출이 존재하지만
- `daily_report_orchestrator.py`에는 누락 → 대시보드 항상 "리포트 생성 후 표시됩니다" 표시

## 변경 내용

수정 파일: `src/modules/real_estate/daily_report/daily_report_orchestrator.py`
1. `LocationRepository` import 추가
2. `__init__`에 `self._loc_repo = LocationRepository(self._db_path)` 추가
3. Step 4 scorer 루프에 `self._loc_repo.upsert_score(loc_score)` 추가

## 아키텍처

`report_orchestrator.py`와 동일한 패턴 적용:
```
scorer.score(c) → loc_score → c["_location_score"]
                            → loc_repo.upsert_score(loc_score) → location_scores 테이블
```

## 데이터 모델

`location_scores` 테이블 (기존 구조 그대로):
- complex_code TEXT (PK)
- residential_total INTEGER
- residential_results TEXT (JSON)
- investment_total INTEGER
- investment_results TEXT (JSON)
- scored_at TEXT
EOF
```

- [ ] **Step 3: progress.md 작성**

```bash
cat > docs/features/poi-location-db-persist/progress.md << 'EOF'
# Progress

## Task 1: 실패하는 테스트 작성
- [x] 테스트 파일 작성
- [x] 실패 확인
- [x] 커밋 (Red)

## Task 2: 구현
- [x] import 추가
- [x] __init__ _loc_repo 초기화
- [x] upsert_score 호출 추가
- [x] 테스트 통과 확인
- [x] 회귀 테스트 확인
- [x] 커밋 (Green)

## Task 3: 전체 테스트 + SOLID Review
- [x] 전체 테스트 PASS

## Task 4: SOP 문서
- [x] spec.md
- [x] progress.md
- [ ] result.md
EOF
```

- [ ] **Step 4: result.md 작성**

전체 테스트 실행 결과를 확인한 후 아래를 기록한다:

```bash
arch -arm64 .venv/bin/python3.12 -m pytest tests/ --ignore=tests/e2e -q 2>&1 | tail -5
```

위 출력 결과를 `result.md`에 붙여넣는다:

```bash
cat > docs/features/poi-location-db-persist/result.md << 'EOF'
# Result

## 변경 내용

- `daily_report_orchestrator.py` 3줄 수정:
  1. `LocationRepository` import 추가
  2. `self._loc_repo = LocationRepository(self._db_path)` 생성자 초기화
  3. Step 4 scorer 루프에 `self._loc_repo.upsert_score(loc_score)` 추가

## 테스트 결과

<!-- 아래에 pytest 출력 붙여넣기 -->
```
[테스트 결과 붙여넣기]
```

## E2E 검증 면제

- **사유:** 화면단 변경 없음 (대시보드 `views/real_estate.py`에 이미 `loc_score` 표시 코드 구현됨)
- **변경 범위:** `src/modules/real_estate/daily_report/daily_report_orchestrator.py` 백엔드 로직만

## 검증 방법

Job4 실행 후 대시보드 단지 클릭 → 실거주/투자 점수 카드 표시 확인 (기존 "리포트 생성 후 표시됩니다" 메시지 해소)
EOF
```

- [ ] **Step 5: history.md 업데이트**

`docs/context/history.md` 상단에 아래 항목 추가:

```markdown
## 2026-05-27: POI 입지 점수 DB 저장 연결

- **Feature:** `feature/poi-location-db-persist` → master 머지
- **배경:** `DailyReportOrchestrator`에서 `LocationScorer.score()` 계산 후 `LocationRepository.upsert_score()` 미호출 → 대시보드 항상 "리포트 생성 후 표시됩니다" 표시
- **변경:** `daily_report_orchestrator.py` 3줄 수정 — import, `__init__` 초기화, upsert 호출
- **테스트:** 신규 5개 (기존 회귀 없음)
- **성과:** Job4 실행 후 `location_scores` 테이블에 단지별 점수 저장, 대시보드 점수 카드 정상 표시
```

- [ ] **Step 6: active_state.md 업데이트**

`docs/context/active_state.md`의 `## 현재 포커스` 섹션을 아래로 교체:

```markdown
## 현재 포커스
- **Branch:** `master`
- **Status:** ✅ POI 입지 점수 DB 저장 연결 완료 (2026-05-27)
  - DailyReportOrchestrator → LocationRepository.upsert_score() 연결
  - location_scores 테이블에 단지별 실거주/투자 점수 저장
  - 대시보드 단지 클릭 시 점수 카드 정상 표시
```

- [ ] **Step 7: 문서 커밋**

```bash
git add docs/features/poi-location-db-persist/ docs/context/history.md docs/context/active_state.md
git commit -m "docs(sop): poi-location-db-persist 피처 문서 + context 업데이트"
```

---

## Task 5: 브랜치 머지

- [ ] **Step 1: 브랜치 생성 여부 확인**

```bash
git branch | grep poi-location
```

브랜치가 없다면 (master에서 직접 작업한 경우) 이 태스크 스킵.

브랜치가 있다면 아래 실행:

```bash
git checkout master
git merge feature/poi-location-db-persist
git push origin master
```

---

## 완료 체크리스트

- [ ] `test_daily_report_orchestrator_location.py` 5개 테스트 PASS
- [ ] 기존 `tests/modules/real_estate/daily_report/` 전체 PASS
- [ ] `tests/modules/real_estate/location/` 63개 PASS
- [ ] 전체 `tests/ --ignore=tests/e2e` PASS
- [ ] `docs/features/poi-location-db-persist/` 문서 3종 완비
- [ ] `history.md`, `active_state.md` 업데이트
