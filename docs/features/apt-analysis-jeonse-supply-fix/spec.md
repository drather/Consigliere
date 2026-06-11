# Spec: 전세가율/공급리스크 None 버그 수정

**작성일:** 2026-06-11

## 배경

`POST /jobs/apt/analyze` 결과에서 `jeonse_ratio`, `supply_risk_summary`가 항상 `None`으로 반환됨.
`docs/master_plan.md` 기준 부동산 매물 분석 핵심 지표(전세가율, 공급 리스크)가 동작하지 않는 구조적 결함.

## 근본 원인 (Phase 1 조사 결과)

1. **`AptAnalysisOrchestrator._get_supply_risk()`**
   - `SupplyRiskAnalyzer(supply_repo=...)` 1개 인자만 전달 → 생성자가 요구하는
     `news_service`/`llm`/`prompt_loader` 누락 → `TypeError` → except에서 `None` 반환.

2. **`AptAnalysisOrchestrator._calc_jeonse_ratio()`**
   - `jeonse_repo.get_by_complex(complex_code)` 호출 → `jeonse_transactions.complex_code`는
     `JeonseClient`가 항상 NULL로 저장하므로 결과가 항상 빈 리스트.
   - 단위 불일치: `price_history`의 `price`는 원(KRW), `jeonse.deposit`은 만원 — 변환 누락.

3. **`JeonseClient._parse()` (운영 데이터 0건의 근본 원인)**
   - 국토부 `RTMSDataSvcAptRent` API 실응답 XML 태그는 영문(`aptNm`, `dealYear`, `deposit` 등)인데
     파서는 한글 태그(`아파트`, `년`, `보증금액` 등)를 조회 → 모든 item이 매칭 실패 →
     `jeonse_transactions` 테이블 0건.

## 수정 범위

- `JeonseRepository.get_by_apt_name(apt_name, district_code)` 신규 추가
- `AptAnalysisOrchestrator._calc_jeonse_ratio()`: `get_by_apt_name` 사용 + 원→만원 단위 변환
- `AptAnalysisOrchestrator.__init__`: `news_service`, `prompt_loader` 옵션 파라미터 추가
- `AptAnalysisOrchestrator._get_supply_risk()`: `SupplyRiskAnalyzer` 생성자에 4개 의존성 모두 전달
- `JeonseClient._parse()`: XML 태그를 실제 API 응답(영문) 기준으로 수정
- `src/api/dependencies.py`: `_apt_orchestrator`를 `_geocoder_service`/`_prompt_loader`/`_daily_llm`
  정의 이후로 이동, `geocoder`/`news_service`/`prompt_loader` 주입

## 데이터 영향

- `POST /jobs/jeonse/collect` 1회 실행 → `jeonse_transactions` 0건 → 8,180건 (71개 구, 2026-06)
