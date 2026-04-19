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
