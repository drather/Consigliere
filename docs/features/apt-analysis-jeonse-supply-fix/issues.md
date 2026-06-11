# Issues & Decisions

## [결정] SupplyRiskAnalyzer 의존성 주입 방식

**배경:** `_get_supply_risk()`에서 `news_service`/`llm`/`prompt_loader` 누락으로 항상 `TypeError` → `None`.
**결정:** `dependencies.py`의 기존 싱글톤(`_news_service`, `_prompt_loader`, `LLMFactory.create()` → `self._llm`)을
`AptAnalysisOrchestrator`에 옵셔널 파라미터로 주입해 재사용. 신규 인스턴스 생성 없음.
**제약:** `_apt_orchestrator` 정의 위치를 `_prompt_loader`/`_daily_llm`/`_geocoder_service` 정의 이후로 이동해야 함
(기존에는 그 이전에 정의되어 있었음).

## [결정] 전세가율 조회 방식 변경 (get_by_complex → get_by_apt_name)

**배경:** `jeonse_transactions.complex_code`는 `JeonseClient`가 채우지 않아 항상 NULL.
`get_by_complex(complex_code)`는 구조적으로 항상 빈 리스트 반환.
**결정:** 신규 `JeonseRepository.get_by_apt_name(apt_name, district_code)` 추가, `_calc_jeonse_ratio`에서 사용.
**부수 수정:** 단위 변환 — `price_history[].price`(원) → 만원으로 나눠 `jeonse.deposit`(만원)과 비교.
**영향 없음:** `get_by_complex()`는 기존 테스트 유지 위해 그대로 둠 (다른 호출처 없음, 향후 정리 가능).

## [버그] JeonseClient._parse() 필드명 한/영 불일치 — 운영 데이터 0건의 진짜 원인

**문제:** 국토부 `RTMSDataSvcAptRent` API는 `aptNm`/`dealYear`/`dealMonth`/`dealDay`/`deposit`/
`monthlyRent`/`excluUseAr`/`floor` (영문 camelCase) 태그로 응답하는데, `_parse()`는
`아파트`/`년`/`월`/`일`/`보증금액`/`월세금액`/`전용면적`/`층` (한글) 태그를 조회 → 모든 `<item>`이
`apt_name=""`, `deposit=0`이 되어 필터링됨 → `jeonse_transactions` 0건.
**수정:** 태그명을 실제 API 응답 기준 영문으로 교체. TDD로 실제 응답 샘플 XML 기반 테스트 추가
(`tests/modules/real_estate/jeonse/test_jeonse_client.py`, 신규 — 기존에 테스트 없었음).
**영향:** 위 1, 2번 코드 수정만으로는 운영 환경에서 `jeonse_ratio`가 여전히 `None`이었을 것.
이 버그가 "전세가율이 항상 None"의 1차 원인이고, 1/2번은 데이터가 있었어도 발생했을 2차 원인.

## 데이터 수집 결과

`POST /jobs/jeonse/collect` (year_month=202606, 71개 구) → fetched 8,410건, saved 8,180건
(중복 제외). `data/real_estate.db.jeonse_transactions`: 0 → 8,180건.

## E2E 검증 면제 사유 (해당 없음)

화면(Streamlit) 변경 없음 — `POST /jobs/apt/analyze` API 응답으로 검증 완료
(`A10025850` 헬리오시티: `jeonse_ratio=37.9`, `supply_risk_summary="반경 3km 공급 0세대 () — 안전"`).
