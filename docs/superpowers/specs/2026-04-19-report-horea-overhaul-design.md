# Design: 부동산 리포트 호재 분석 고도화 & 가독성 개선

**Date:** 2026-04-19  
**Branch:** `feature/report-generation-overhaul`  
**관련 이슈:** ISSUE-01, ISSUE-02, ISSUE-03 (issues.md)

---

## 1. 배경 & 목표

Job4 첫 실행 결과 세 가지 이슈 식별:

| 이슈 | 현상 | 근본 원인 |
|------|------|-----------|
| ISSUE-01 | 동일 단지가 다른 이름으로 2개 출현 | dedup key에 apt_name 정규화 미적용 |
| ISSUE-02 | 세대수 미확인 → 환금성 20점 고정 | `_lookup_apt_details()` normalize 없이 조회 |
| ISSUE-03 | 가격상승가능성 전체 10점 | Python 키워드 매칭 한계 + 복합 지명 미매칭 + 호재 없는 날 최솟값 부여 |

추가 요구사항:
- 리포트 출력 형식: 문단 줄글 → 항목별 개조식 bullet + 각 기준 점수 표시

---

## 2. 데이터 흐름 (변경 후)

```
[Job2 — 신규 추가]
  NaverNewsClient → articles (title, url, description, pub_date)
    ├─ LLM news_analyst → {date}_News.md          (기존 유지)
    └─ articles 리스트 그대로 → {date}_News_articles.json  (신규, 추가 LLM 비용 없음)

[Job4 — 변경]
  generate_report():
    ① tx_repo 조회 후 dedup: _normalize_name(apt_name) 적용        ← ISSUE-01
    ② _lookup_apt_details(): apt_name normalize 후 조회             ← ISSUE-02
    ③ _extract_horea_data(): 복합 지명(예: "성남시 분당구") 분리 매칭  ← ISSUE-03
    ④ _load_stored_news_articles(date) → articles_json 로드         ← ISSUE-03

  InsightOrchestrator.generate_strategy():
    Step 1: CandidateFilter (기존)
    Step 2: _validate_horea(interest_areas, news_articles)           ← 신규 LLM 호출
            → horea_scores: {area: {score, verdict, reasoning}}
    Step 3: ScoringEngine.score_all(horea_scores=horea_scores)       ← 파라미터 변경
    Step 4: _synthesize_report(horea_assessments 추가)               ← 개조식 + 점수 표시
```

---

## 3. 컴포넌트별 변경 상세

### 3-1. ISSUE-01: dedup 정규화 (`service.py`)

**위치:** `generate_report()` Step 5 (dedup loop)

```python
# 변경 전
key = f"{tx.get('apt_name')}_{tx.get('exclusive_area')}..."

# 변경 후
from .transaction_repository import _normalize_name
key = f"{_normalize_name(tx.get('apt_name', ''))}_{tx.get('exclusive_area')}..."
```

---

### 3-2. ISSUE-02: `_lookup_apt_details()` 정규화 (`service.py`)

```python
def _lookup_apt_details(self, apt_name: str, district_code: str):
    apt_name = _normalize_name(apt_name)   # ← 추가
    entry = self.apt_master_repo.get_by_name_district(apt_name, district_code)
    ...
```

**추가 원칙:** 아파트 디테일 데이터(공동주택 기본정보 API)와 apt_master 데이터는
데이터 원천이 달라 매핑이 불가능한 단지가 존재한다. 디테일 데이터 부재는
"데이터 없음"이므로 최솟값이 아닌 **중립값**으로 처리한다.

---

### 3-3. ISSUE-03-A: 복합 지명 매칭 (`service.py`)

```python
def _area_matches(area: str, text: str) -> bool:
    """전체 지명 또는 공백 분리 토큰(2자 이상) 중 하나라도 포함되면 True."""
    if area in text:
        return True
    return any(token in text for token in area.split() if len(token) >= 2)
```

`_extract_horea_data()` 내 `area not in sent` → `not _area_matches(area, sent)` 으로 교체.

---

### 3-4. ISSUE-03-B: Job2 구조화 JSON 저장 (`news/service.py`)

`generate_daily_report()` 내 `_save_report()` 호출 직전:

```python
self._save_articles_json(articles, today)
```

저장 형식: `data/real_estate/news/{date}_News_articles.json`

```json
{
  "date": "2026-04-19",
  "articles": [
    {
      "title": "강남구 재건축 조합설립 인가",
      "url": "https://...",
      "description": "강남구 일대 정비사업...",
      "pub_date": "Sat, 19 Apr 2026 09:00:00 +0900"
    }
  ]
}
```

---

### 3-5. ISSUE-03-C: `horea_validator.md` 프롬프트 (신규)

**파일:** `src/modules/real_estate/prompts/horea_validator.md`

```
입력 변수: today_date, interest_areas, articles_json

출력 JSON:
{
  "horea_assessments": {
    "강남구":     {"score": 75, "verdict": "ACTIVE", "reasoning": "2026-04-19 기사 — 강남구 재건축 조합설립 인가. 단기 가격 상승 요인."},
    "성남시 분당구": {"score": 0,  "verdict": "NONE",   "reasoning": "분당구 관련 호재 기사 없음."},
    "송파구":     {"score": 30, "verdict": "DATED",  "reasoning": "GTX 언급 있으나 2024년 착공 예정 기사 — 현재 유효성 낮음."}
  }
}
```

verdict 규칙:
- `ACTIVE`: 최근 6개월 이내 & 실질적 가격 상승 영향 예상 → score 31–100
- `DATED`: 기사가 과거 계획·예정 중심 → score ≤ 30
- `NONE`: 관련 기사 없음 → score = 0

---

### 3-6. ISSUE-03-D: `InsightOrchestrator` horea_validator 단계 추가

```python
def generate_strategy(self, ..., news_articles=None):
    # Step 1: CandidateFilter (기존)
    filtered = CandidateFilter(preference_rules).apply(candidates)

    # Step 2: horea_validator LLM (신규)
    interest_areas = persona_data.get("user", {}).get("interest_areas", [])
    horea_scores = self._validate_horea(interest_areas, news_articles)

    # Step 3: ScoringEngine (horea_scores 주입)
    engine = ScoringEngine(weights=priority_weights, config=scoring_config)
    scored = engine.score_all(filtered, horea_scores=horea_scores)

    # Step 4: report_synthesizer (기존 + horea_assessments 추가)
    return self._synthesize_report(..., horea_assessments=horea_scores)
```

---

### 3-7. `ScoringEngine` 중립값 처리 (`scoring.py`)

데이터 부재 시 최솟값 부여 대신 중립값 사용 원칙을 전 기준에 적용:

| 기준 | 기존 (데이터 없음) | 변경 후 |
|------|-------------------|---------|
| `household_count` 없음 | `_LOW = 20` | `neutral = 50` |
| `reconstruction_potential = UNKNOWN` & horea 없음 | `10` | `neutral = 50` |
| `nearest_stations = []` (area_intel 미매핑) | `_LOW = 20` | `neutral = 50` |
| `school_zone_notes` 없음 | `_LOW = 20` | `neutral = 50` |

`neutral = 50` 값은 `config.yaml → scoring.data_absent_neutral: 50` 으로 config화.

**`ScoringEngine.__init__()` 추가:**
```python
self.neutral = config.get("data_absent_neutral", 50)
self.recon_map["UNKNOWN"] = self.neutral  # UNKNOWN → config neutral로 override
```

**용어 명확화:**
- `horea_data`: 기존 Python `_extract_horea_data()` 출력 → `horea_text` 생성에 계속 사용
- `horea_scores`: 신규 LLM `horea_validator` 출력 → ScoringEngine 가중치에 사용

**horea 점수 반영 방식:**

```python
def _score_price_potential(self, c, horea_scores=None):
    potential = c.get("reconstruction_potential", "UNKNOWN")
    base = self.recon_map.get(potential, self.neutral)   # UNKNOWN → neutral(50)

    if c.get("gtx_benefit"):
        base = min(100, base + 30)

    if horea_scores:
        district_name = c.get("district_name", "")
        for area_key, assessment in horea_scores.items():
            if area_key in district_name or district_name in area_key:
                score = assessment.get("score", 0)
                boost = int(score * 0.4)          # 100 → +40, 50 → +20, 0 → 0
                base = min(100, base + boost)
                break

    return base
```

---

### 3-8. `report_synthesizer.md` 개조식 + 점수 표시

**변경 내용:**
- 단지별 서술: 문단 줄글 → `-` bullet 개조식
- 각 기준 점수 `[N점]` 표시
- `price_potential`에 verdict + reasoning sub-bullet 추가
- `horea_assessments` JSON을 입력 변수로 추가

**출력 예시:**
```
## 1위. 반포자이 (77.5점)
- 가격: 13.2억 (예산 대비 -3%)
- 출퇴근: 삼성역 12분 (9호선) [100점]
- 환금성: 1,200세대 [100점]
- 생활편의: 도보 5분 내 역 2개 [100점]
- 학군: 반포초 인근 [60점]
- 가격상승가능성: 재건축 진행 중 [75점 / ACTIVE]
  └ 근거: 2026-04-17 — 서초구 정비구역 지정 고시
- 종합: 환금성·출퇴근 우수, 단기 가격 상승 가능성 높음
```

---

## 4. 에러 처리

| 상황 | 처리 |
|------|------|
| `{date}_News_articles.json` 없음 | `horea_validator` 스킵 → `horea_scores=None` → 중립값 |
| `horea_validator` LLM 실패 | `try/except` → `horea_scores=None`, `logger.warning` |
| `horea_assessments` 일부 지역 누락 | 해당 지역 score 없음 → 중립값 |
| `_lookup_apt_details` normalize 후도 미매칭 | 세대수 `None` → `_score_liquidity` 중립값(50) |
| 아파트 디테일 데이터 원천 미매핑 | 데이터 없음 = 중립(50), 최솟값(20) 부여 금지 |

---

## 5. 테스트 전략 (TDD)

### 신규 테스트 파일 3개

**`tests/unit/test_horea_validator.py`**
- horea_validator LLM mock → ACTIVE / DATED / NONE 각 케이스 검증
- `news_articles=None` → `horea_scores=None` 반환
- `today_date` 기준 6개월 초과 기사 → `DATED` verdict

**`tests/unit/test_scoring_neutral_defaults.py`**
- `household_count=None` → `_score_liquidity()` = 50
- `reconstruction_potential="UNKNOWN"` + `horea_scores=None` → `_score_price_potential()` = 50
- `horea_scores={"강남구": {"score": 75}}` + 강남구 단지 → base + 30 boost
- `nearest_stations=None` → `_score_living_convenience()` = 50

**`tests/unit/test_service_fixes.py`**
- `"이매촌(청구)"` / `"이매촌청구"` dedup 시 동일 key 생성
- `_lookup_apt_details("이매촌(청구)", "41135")` → normalize 후 조회
- `_extract_horea_data("성남시 분당구", "분당구 재건축 추진...")` → 매칭 성공
- `_extract_horea_data("성남시 분당구", "강남 GTX...")` → 미매칭

### 기존 테스트 수정

- `test_orchestrator_single_llm.py` → `generate_strategy()` `news_articles` 파라미터 추가
- `test_generate_report_sqlite.py` → `horea_scores` 반영 확인

---

## 6. 변경 파일 목록

| 파일 | 종류 | 내용 |
|------|------|------|
| `src/modules/real_estate/service.py` | 수정 | dedup normalize, _lookup normalize, _extract_horea compound fix, _load_stored_news_articles |
| `src/modules/real_estate/news/service.py` | 수정 | _save_articles_json 추가 |
| `src/modules/real_estate/insight_orchestrator.py` | 수정 | _validate_horea LLM 단계 추가, horea_scores 주입 |
| `src/modules/real_estate/scoring.py` | 수정 | horea_scores 파라미터, 중립값 처리 전반 |
| `src/modules/real_estate/prompts/horea_validator.md` | 신규 | horea validation 프롬프트 |
| `src/modules/real_estate/prompts/report_synthesizer.md` | 수정 | 개조식 + 점수 표시 + horea_assessments 변수 |
| `config.yaml` | 수정 | `scoring.data_absent_neutral: 50` 추가 |
| `docs/features/report-generation-overhaul/issues.md` | 수정 | ISSUE-01~03 해결 방향 업데이트 |
| `docs/features/report-generation-overhaul/progress.md` | 수정 | Phase 3.5 이슈 완료 체크 |

---

## 7. SOP 문서 계획

- `docs/features/report-generation-overhaul/result.md` — 구현 완료 후 작성
- `docs/context/history.md` — 브랜치 완료 시 업데이트
- `docs/context/active_state.md` — 구현 착수 시 업데이트
