# 부동산 인사이트 리포트 생성 전면 점검 및 고도화

**Branch:** `feature/report-generation-overhaul`  
**작성일:** 2026-04-19  
**참조:** `docs/master_plan.md`, `docs/superpowers/specs/2026-04-19-report-generation-overhaul-design.md`

---

## 목표

실거래가·거시경제·뉴스 데이터를 유기적으로 연결한 리포트를 LLM 1회 호출로 생성한다.  
현재 발생 중인 데이터 소스 오류(ChromaDB 잔재), enrich 실패, 거시경제 미활용 문제를 모두 수정한다.

---

## 문제 목록

| # | 문제 | 원인 |
|---|------|------|
| 1 | 점수 변별력 없음 (1~6위 57.5점) | `apt_master_service.get_or_fetch()` enrich 실패 → 세대수 없음 |
| 2 | 거시경제 미반영 | `_load_stored_macro()` 결과가 Orchestrator에 전달 안 됨 |
| 3 | 설명 복붙 (1~6위 동일) | area_intel 동 레벨 매칭 실패 → 구 평균 fallback |
| 4 | ChromaDB 쿼리 | `generate_report()`가 `self.repository.get_transactions()` 사용 중 |
| 5 | LLM 2회 호출 낭비 | `_analyze_horea()` 별도 LLM 호출 |

---

## 아키텍처

### 후보 선정 파이프라인 (Python 전담)

```
MacroRepository → 최신 주담대금리 조회
FinancialCalculator → 예산 ceiling (자산 + DSR 기반 대출)
tx_repo SQLite → 관심 지역 최근 N일 실거래 조회
가격 필터 → budget_ceiling × 0.9 ~ × 1.1
CandidateFilter → preference_rules 비선호 제거
apt_master_repo → 세대수/건설사/준공연도 enrich (SQLite 직접 조회)
area_intel → 역세권/출퇴근/학군 enrich
ScoringEngine → 점수 계산 → 상위 5개
```

### LLM 단일 호출

Python 준비물 4종을 하나의 프롬프트에 주입:
1. `macro_summary`: 기준금리·주담대금리·M2·CPI·전세지수 최신값
2. `horea_items`: 뉴스 텍스트 Python 키워드 추출 (GTX·재건축·개발지구·학군)
3. `budget_reasoning`: 예산 산출 근거
4. `top5_candidates`: 점수+세대수+건설사+준공+역세권 포함 JSON

출력: Slack Block Kit JSON `{"blocks": [...]}`

---

## 변경 파일

| 파일 | 변경 내용 |
|------|-----------|
| `service.py` | `generate_report()`: ChromaDB → `tx_repo` + macro/horea Python 포맷팅 |
| `service.py` | `_enrich_transactions()`: `apt_master_service` → `apt_master_repo` 직접 조회 |
| `calculator.py` | `calculate_budget()`: `MacroRepository` 주담대금리 주입 인터페이스 추가 |
| `insight_orchestrator.py` | `_analyze_horea()` 제거, 시그니처에 `macro_summary`, `horea_items` 추가 |
| `prompts/report_synthesizer.md` | macro_summary, horea_items 섹션 추가 |

## 비변경 범위

- `ScoringEngine`, `CandidateFilter`, `area_intel` 매칭 로직
- Job1~3 수집 로직 (`fetch_transactions`, `fetch_news`, `fetch_macro_data`)
- `run_insight_pipeline` 순서
- 대시보드 (`📋 Report Archive` 탭 기존 활용)
