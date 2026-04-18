---
title: 부동산 인사이트 리포트 생성 기능 전면 점검 및 고도화
date: 2026-04-19
status: approved
---

# 부동산 인사이트 리포트 생성 기능 전면 점검 및 고도화

## 1. 배경 및 목표

### 배경
- 실거래가·아파트 상세정보·뉴스/정책팩트·거시경제 지표 수집 고도화 완료
- 기존 리포트 품질 문제: 점수 변별력 없음, 거시경제 미반영, 설명 복붙
- 핵심 원인: SQLite 전환 후 Job4가 여전히 ChromaDB 쿼리, apt_master enrich 미동작, macro 미전달
- LLM 호출 2회 구조가 월 2,000원(Gemini Flash 2.5) 예산에 비해 비효율적

### 목표
- 실거래가·거시경제·뉴스 데이터를 유기적으로 연결한 납득 가능한 리포트 생성
- LLM 호출 2회 → 1회로 통합하여 토큰 절감
- Slack 아침 브리핑 + 대시보드 Report Archive 히스토리 소비

---

## 2. 현재 문제 목록

| 문제 | 원인 코드 위치 |
|------|---------------|
| 점수 변별력 없음 (1~6위 57.5점) | `service.py:_enrich_transactions()` — `apt_master_service.get_or_fetch()` 실패로 세대수 없음 → 환금성 20점 고정 |
| 거시경제 미반영 | `service.py:generate_report()` — `_load_stored_macro()` 호출하나 `InsightOrchestrator`에 전달 안 함 |
| 설명 복붙 | `service.py:_enrich_transactions()` — area_intel 동 레벨 매칭 실패 → 구 평균 fallback |
| ChromaDB 쿼리 | `service.py:generate_report():365` — `self.repository.get_transactions()` 사용 중 |
| LLM 2회 호출 | `insight_orchestrator.py` — `_analyze_horea()` 별도 LLM 호출 |

---

## 3. 설계

### 3.1 후보 선정 파이프라인 (Python 전담)

```
[MacroRepository] 최신 주담대금리 조회
        ↓
[FinancialCalculator] persona 자산/소득 + 주담대금리 → 예산 ceiling
        ↓
[tx_repo SQLite] persona.interest_areas 지역 최근 N일 실거래 조회
        ↓
[가격 필터] budget_ceiling × 0.9 ≤ price ≤ budget_ceiling × 1.1
        ↓
[CandidateFilter] preference_rules.yaml 비선호 필터 (오피스텔 등)
        ↓
[apt_master_repo] 세대수 / 건설사 / 준공연도 enrich (SQLite 직접 조회)
        ↓
[area_intel] 역세권 / 출퇴근 / 학군 enrich (기존 유지)
        ↓
[ScoringEngine] persona priority_weights 기반 점수 계산
        ↓
상위 5개 선정 (top_n: 10 → 5)
```

### 3.2 LLM 단일 호출 구조

Python이 모든 데이터를 정리 → LLM은 자연어 서술만 담당.

**Python 준비물:**
1. `macro_summary`: 기준금리, 주담대금리, M2, CPI, 전세지수 등 최신값 포맷 텍스트
2. `horea_items`: 뉴스 텍스트에서 GTX·재건축·개발지구·학군변화 키워드 포함 문장 Python 추출
3. `budget_reasoning`: 자산 + 대출(주담대금리 반영) = 예산 천장 근거 서술
4. `top5_candidates`: 점수+세대수+건설사+준공+역세권 완전 포맷 JSON (상위 5개)

**LLM 1회 호출:**
- 입력: macro_summary + horea_items + budget_reasoning + top5_candidates
- 출력: Slack Block Kit JSON (`{"blocks": [...]}`)
- `horea_analyst` 프롬프트 및 LLM 호출 제거

### 3.3 변경 파일 목록

| 파일 | 변경 내용 |
|------|-----------|
| `src/modules/real_estate/service.py` | `generate_report()`: ChromaDB → `tx_repo` + macro/horea Python 포맷팅 추가 |
| `src/modules/real_estate/service.py` | `_enrich_transactions()`: `apt_master_service` → `apt_master_repo` 직접 조회 |
| `src/modules/real_estate/calculator.py` | `calculate_budget()`: `MacroRepository` 최신 주담대금리 주입 인터페이스 추가 |
| `src/modules/real_estate/insight_orchestrator.py` | `_analyze_horea()` 제거, `generate_strategy()` 시그니처에 `macro_summary`, `horea_items` 추가 |
| `src/modules/real_estate/prompts/report_synthesizer.md` | macro_summary, horea_items 섹션 추가, top_n 변수 5로 기본값 반영 |

### 3.4 대시보드

**변경 없음.** `📋 Report Archive` 탭(tab3)이 이미 완전 구현 상태.  
Job4가 올바른 포맷(`data/real_estate/reports/YYYY-MM-DD_Report.json`)으로 저장하면 자동 표시.

---

## 4. 비변경 범위

- `ScoringEngine` — 점수 계산 로직 유지
- `CandidateFilter` — preference_rules 필터 유지
- `area_intel` 매칭 로직 — 구조 유지 (동 레벨 매칭 실패 시 구 평균 fallback 허용)
- `fetch_transactions`, `fetch_news`, `fetch_macro_data` (Job1~3) — 변경 없음
- `run_insight_pipeline` 파이프라인 순서 — 변경 없음

---

## 5. 성공 기준

- [ ] 상위 5개 단지 점수가 서로 다른 값 (변별력 확인)
- [ ] 환금성 점수에 세대수가 반영됨 (20점 고정 탈피)
- [ ] 리포트에 기준금리/주담대금리 수치가 포함됨
- [ ] LLM 호출이 1회 (로그 확인)
- [ ] Report Archive 탭에서 생성된 리포트 조회 가능
