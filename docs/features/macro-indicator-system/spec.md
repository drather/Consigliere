# Spec: 거시경제 지표 수집 시스템

**작성일:** 2026-04-18  
**브랜치:** feature/macro-indicator-system  
**참조:** docs/master_plan.md

---

## 목표

BOK ECOS(한국은행 경제통계시스템) API를 통해 거시경제 지표를 SQLite DB에 영구 저장·수집·조회하는 공유 macro 모듈을 구축한다. 기존 `real_estate/macro/` 코드를 이 모듈로 통합하고, 대시보드 Insight 탭에 카테고리별 지표 현황을 표시한다.

---

## 아키텍처

```
src/modules/macro/          ← 도메인 중립 공유 패키지
    models.py               ← MacroIndicatorDef, MacroRecord 데이터클래스
    repository.py           ← SQLite CRUD (data/macro.db)
    bok_client.py           ← BOK ECOS API 클라이언트
    service.py              ← MacroCollectionService 오케스트레이션

src/api/routers/macro.py    ← /jobs/macro/collect, /dashboard/macro/*
src/api/dependencies.py     ← MacroCollectionService DI 등록

src/dashboard/views/real_estate.py  ← Insight 탭 거시경제 서브탭 확장
src/dashboard/api_client.py         ← get_macro_latest(), get_macro_indicator_history()
```

### 데이터 흐름

```
BOK ECOS API → BOKClient → MacroCollectionService → MacroRepository → macro.db
                                                                          ↓
Dashboard ← DashboardClient ← FastAPI /dashboard/macro/* ← MacroRepository
```

---

## 데이터 모델

### MacroIndicatorDef
| 필드 | 타입 | 설명 |
|------|------|------|
| code | str | BOK stat_code (예: "722Y001") |
| item_code | str | BOK item_code (예: "0101000") |
| frequency | str | M/Q/A/D |
| collect_every_days | int | 수집 주기 |
| domain | str | real_estate / common |
| category | str | 금리 / 주택시장 / 물가 / 유동성 / 경기 |

### MacroRecord
| 필드 | 타입 | 설명 |
|------|------|------|
| indicator_id | int | FK → macro_indicator_definitions |
| period | str | BOK 발표 기준 기간 (예: "202503", "2025Q4") |
| value | float | 수치 |
| collected_at | str | 실제 수집 일시 (ISO) |

---

## 수집 지표 (8개 활성)

| # | 지표명 | stat_code | item_code | freq | domain | category |
|---|--------|-----------|-----------|------|--------|----------|
| 1 | 한국은행 기준금리 | 722Y001 | 0101000 | M | common | 금리 |
| 2 | 예금은행 주택담보대출 금리 | 121Y002 | BEABAA2 | M | real_estate | 금리 |
| 3 | M2 통화량(기말, 계절조정) | 161Y007 | BBGS00 | M | common | 유동성 |
| 4 | 가계신용 총량 | 151Y001 | 1000000 | Q | common | 유동성 |
| 5 | 주택매매가격지수(전국) | 901Y062 | P63A | M | real_estate | 주택시장 |
| 6 | 전세가격지수(전국) | 901Y063 | P64A | M | real_estate | 주택시장 |
| 7 | 소비자물가지수(CPI) | 901Y009 | 0 | M | common | 물가 |
| 8 | 실질GDP 성장률(전년동기비) | 200Y102 | 10211 | Q | common | 경기 |

> COFIX(121Y013): BOK ECOS 미제공 — is_active=False
