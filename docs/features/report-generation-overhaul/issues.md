# Issues & Decisions: 부동산 리포트 생성 전면 점검

**Branch:** `feature/report-generation-overhaul`
**Date:** 2026-04-19

---

## SOLID Review Results

### SRP (Single Responsibility Principle)

| Method | Assessment |
|--------|------------|
| `_lookup_apt_details()` | Single responsibility — 2-step SQLite lookup (apt_master → apt_repo). Reads one record, returns one result. ✓ |
| `_format_macro_summary()` | Formats a macro dict into a human-readable text block. No side effects. ✓ |
| `_extract_horea_data()` | Keyword matching only — filters transaction list by district name keywords. No I/O. ✓ |
| `generate_report()` | Orchestration coordinator — multiple concerns are appropriate for a coordinator method. Individual concerns (budget calc, enrichment, LLM call) are delegated to dedicated helpers. ✓ |

**Decision:** `generate_report()` is intentionally a thin coordinator; the internal complexity lives in called helpers. This is acceptable per SRP at the class level.

---

### OCP (Open/Closed Principle)

- `InsightOrchestrator` accepts `BaseLLMClient` and `PromptLoader` via constructor injection. Swapping LLM provider or prompt template requires no modification to orchestrator logic. ✓
- `ReportService` accepts `tx_repo`, `apt_repo`, `apt_master_repo`, and `macro_repo` via constructor. New data sources can be added without altering existing methods. ✓

---

### DIP (Dependency Inversion Principle)

- `_lookup_apt_details()` depends on `apt_master_repo` and `apt_repo` interfaces, not concrete implementations. ✓
- `InsightOrchestrator` depends on `BaseLLMClient` (abstract) and `PromptLoader` (interface). ✓
- `ReportService` depends on repository interfaces injected at construction time. ✓

---

### Zero Hardcoding

| Value | Location |
|-------|----------|
| `top_n` (5) | `config.yaml` → `report.top_n` ✓ |
| `recent_days` (7) | `config.yaml` → `report.recent_days` ✓ |
| `budget_band_ratio` (0.1) | `config.yaml` → `report.budget_band_ratio` ✓ |
| LTV/DSR defaults | `config.yaml` → `financial_defaults` ✓ |
| `interest_rate` default | `config.yaml` → `financial_defaults.interest_rate` ✓ |

**Note:** `budget_band_ratio` was previously hardcoded as a literal `0.1` in the price filter. Moved to config.yaml in this overhaul.

---

### Error Handling

| Location | Strategy |
|----------|----------|
| `_enrich_transactions()` | `try/except` per transaction with `logger.warning` — one enrichment failure does not abort the batch. ✓ |
| `_synthesize_report()` | `try/except` with fallback to empty report dict — LLM failure is non-fatal. ✓ |
| `generate_report()` district loop | `try/except` per district — one district failure does not abort other districts. ✓ |

---

## Key Decisions & Tradeoffs

### Decision 1: ChromaDB → tx_repo SQLite
- **Rationale:** ChromaDB vector search was used for candidate retrieval, but semantic similarity is not appropriate for recent-transaction lookup. SQLite `TransactionRepository` provides deterministic, date-bounded queries.
- **Tradeoff:** Loses fuzzy name matching. Mitigated by `apt_master_repo.get_by_name()` normalization.

### Decision 2: LLM 2회 → 1회 통합
- **Rationale:** `horea_analyst` was a separate LLM call producing near-duplicate content. Merging `macro_summary` and `horea_items` into a single `report_synthesizer` prompt reduces token cost ~50% and eliminates redundant round-trips.
- **Tradeoff:** Prompt is larger, but structured sections keep outputs deterministic.

### Decision 3: apt_master enrich via SQLite
- **Rationale:** `household_count` and other master fields were not being populated after ChromaDB removal. `apt_master_repo.get_by_name()` restores this data with proper normalization.
- **Tradeoff:** Name-based lookup can miss matches if normalization diverges. The existing `normalize_apt_name()` utility handles common variants.

### Decision 4: top_n 10 → 5
- **Rationale:** 10 recommendations per report produced verbose LLM output that degraded synthesis quality. 5 items yield tighter, more actionable reports.
- **Config path:** `config.yaml` → `report.top_n`

### Decision 5: Price ±10% filter (budget_band_ratio)
- **Rationale:** Without a price filter, candidates include properties far outside the user's budget, distorting scoring. A ±10% band keeps candidates relevant.
- **Config path:** `config.yaml` → `report.budget_band_ratio`

---

## 실행 결과 이슈 (2026-04-19 Job4 첫 실행 후 발견)

### ISSUE-01: 중복 단지 출현 — 이매촌청구 vs 이매촌(청구)
- **현상:** 3위와 4위가 동일 아파트의 다른 이름 표기로 각각 출현
- **원인:** 실거래가 원시 데이터에 동일 단지가 "이매촌청구"와 "이매촌(청구)" 두 가지 이름으로 등록됨. dedup 키는 `apt_name + area + date + floor + price` 조합이므로 이름이 다르면 별개 취급
- **해결:** `_make_dedup_key()` 모듈 함수 추출 + `_normalize_name()` 적용. `test_service_fixes.py` 커버.

### ISSUE-02: 세대수 미확인 — 금강캐스빌, 이매촌(청구)
- **현상:** 환금성 점수 20점 고정 (세대수 없음)
- **원인:** `apt_master_repo`에 해당 단지 complex_code 매핑이 없음 → `apt_repo.search()` fallback도 미매칭
- **해결:** `_lookup_apt_details()` 내 normalize 적용. 디테일 미매핑 시 ScoringEngine 중립값(50) 처리.

### ISSUE-03: 가격상승가능성 전체 10점
- **현상:** 4개 단지 모두 가격상승가능성 10점 (호재 없음)
- **원인 후보 1:** `_extract_horea_data()`의 `interest_areas`가 "송파구" 같은 구(區) 단위인데, 뉴스 문장에 구 이름이 직접 언급되지 않으면 매칭 실패
- **원인 후보 2:** 오늘 수집된 뉴스(`2026-04-19_News.md`)에 관심 지역 호재 키워드 자체가 없을 수 있음
- **해결:** horea_validator LLM 단계 도입 (InsightOrchestrator Step 2), 복합 지명 매칭 `_area_matches()`, 기본값 50(중립).

---

## LLM 할루시네이션 이슈 (2026-04-20 수정)

### ISSUE-04: LLM 점수 재계산 — 잘못된 기준 점수 출력
- **현상:** LLM이 `scores.liquidity=50`을 무시하고 `household_count=null`을 직접 읽어 20점으로 재계산; `reconstruction_potential=UNKNOWN` → 10점 재계산
- **원인:** `ranked_candidates` 변수로 raw JSON을 전달하면 LLM이 raw 필드 값을 읽어 점수를 직접 추론. LLM이 instruction보다 데이터에서 패턴을 인식하는 경향
- **해결:** `InsightOrchestrator._format_candidates_for_llm()` 도입. 후보 목록을 LLM에 전달하기 전에 `"출퇴근점수: 100점 (19분, 잠실역)"` 형태의 명시적 텍스트로 pre-format. raw JSON 제거.
- **효과:** LLM이 점수를 읽기만 하고 재계산 불가. `test_format_candidates_for_llm.py` 9개 테스트 커버.

### ISSUE-05: LLM 가격 단위 오변환 — "9억원" → "90000억원"
- **현상:** 가격 "9억원"이 "90000억원" (9경원)으로 출력됨
- **원인:** LLM이 "9억원"을 읽고 9억 = 90,000만원임을 인지 → 90,000을 추출 → "억원" 단위를 붙여 "90,000억원" 오변환. 한국 부동산 단위 혼동.
- **해결:** 가격 표기를 DB 원본 단위인 `"90,000만원"` 형식으로 유지. LLM에게 만원→억원 변환 지시 추가. LLM이 이미 "알고 있는" 숫자(90,000)와 일치시켜 재변환 불필요.

### ISSUE-06: nearest_stations dict raw 노출
- **현상:** 출퇴근 정보가 `{'name': '잠실역', 'line': '2호선·8호선', 'walk_minutes': 5}` Python dict repr으로 출력
- **원인:** `_format_candidates_for_llm()`에서 `stations[0]`을 직접 문자열화 — dict 타입이면 `repr()` 출력
- **해결:** `isinstance(s, dict)` 분기 → `name`/`line` 필드 추출 후 `"잠실역 (2호선·8호선)"` 형식으로 포맷

### ISSUE-07: LLM 후보 수 초과 출력 — 없는 4위 단지 생성
- **현상:** Python 파이프라인 결과 3개 단지 → LLM이 이매촌(청구)을 4위로 생성
- **원인:** apt_name 정규화 전 raw JSON에는 "이매촌청구"와 "이매촌(청구)" 두 표기가 존재 → LLM이 다른 단지로 인식해 별도 항목 생성
- **해결 1:** `_enrich_transactions()`에서 `tx["apt_name"] = detail.apt_name` 덮어쓰기로 apt_master 기준 이름으로 정규화
- **해결 2:** pre-format 텍스트 첫 줄에 `"총 N개 단지 (이 목록 외 단지는 절대 출력하지 마십시오)"` 명시
