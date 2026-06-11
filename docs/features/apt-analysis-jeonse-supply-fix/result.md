# Result

**완료일:** 2026-06-11

## 변경 내용

- `src/modules/real_estate/jeonse/repository.py`: `get_by_apt_name(apt_name, district_code)` 신규 추가
- `src/modules/real_estate/jeonse/client.py`: `_parse()` XML 태그 한글 → 실제 영문 태그로 수정
  (`아파트`→`aptNm`, `보증금액`→`deposit`, `월세금액`→`monthlyRent`, `전용면적`→`excluUseAr`,
  `년/월/일`→`dealYear/dealMonth/dealDay`, `층`→`floor`)
- `src/modules/real_estate/apt_analysis/orchestrator.py`
  - `_calc_jeonse_ratio`: `get_by_complex` → `get_by_apt_name`, 원→만원 단위 변환 추가
  - `__init__`: `news_service`, `prompt_loader` 옵션 파라미터 추가
  - `_get_supply_risk`: `SupplyRiskAnalyzer(supply_repo, news_service, llm, prompt_loader)` 전체 의존성 전달
- `src/api/dependencies.py`: Apt Analysis 블록을 Daily Report Orchestrator 섹션 뒤로 이동,
  `geocoder=_geocoder_service`, `news_service=_news_service`, `prompt_loader=_prompt_loader` 주입

## 신규/수정 테스트

- `tests/modules/real_estate/jeonse/test_jeonse_repository.py`: `get_by_apt_name` 2개 추가 (9/9 pass)
- `tests/modules/real_estate/jeonse/test_jeonse_client.py`: 신규 파일, 실제 API 응답 형식 기반 2개 (2/2 pass)
- `tests/modules/real_estate/apt_analysis/test_apt_analysis_orchestrator.py`: jeonse/supply-risk 관련
  fixture·assertion 수정 + supply-risk 신규 2개 (13/13 pass)

## 테스트 결과

```
arch -arm64 .venv/bin/python3.12 -m pytest tests/ -q --ignore=tests/test_job4_enhancements.py
889 passed, 7 failed (career/dashboard/insight/tab5 — 본 변경과 무관, stash 비교로 pre-existing 확인)
```
(`tests/test_job4_enhancements.py`는 직전 커밋 `9ba9c13`에서 제거된 `CodeBasedValidator` import로
collection 단계에서 실패 — 본 작업과 무관한 기존 결함)

## 데이터 / 운영 반영

- `POST /jobs/jeonse/collect` 실행 (호스트 venv, `data/real_estate.db` 직접 기록):
  `jeonse_transactions` 0건 → 8,180건
- `docker restart consigliere_api` — 코드 변경 반영 (정상 기동 확인)

## E2E 검증

`POST /jobs/apt/analyze {"complex_code":"A10025850","send_slack":false}` (헬리오시티)

| 필드 | 수정 전 | 수정 후 |
|---|---|---|
| `jeonse_ratio` | `null` | `37.9` |
| `supply_risk_summary` | `null` | `"반경 3km 공급 0세대 () — 안전"` |

## E2E 화면단 검증 면제

**사유:** 백엔드(orchestrator/repository/client/DI) 수정만 포함, Streamlit 화면 변경 없음.
**변경 범위:** `src/modules/real_estate/jeonse/`, `src/modules/real_estate/apt_analysis/orchestrator.py`,
`src/api/dependencies.py`

## 후속: WR-007 운영 파이프라인 검증 (2026-06-11)

**목적:** 코드 수정 사항이 실제 운영 스케줄(WR-007, n8n `EbHtr48rdQJn1Emn`, 매주 일요일 05:00 KST)에서도
정상 동작하는지 확인.

**제약:** n8n 공개 REST API는 cron(`scheduleTrigger`) 기반 워크플로우의 ad-hoc "지금 실행"을
지원하지 않음 (`POST /workflows/{id}/run` → `405 Method Not Allowed`). 따라서 WR-007이 호출하는
두 엔드포인트를 동일 순서로 직접 호출해 파이프라인 로직을 검증.

| 호출 | 응답 | 결과 |
|---|---|---|
| `POST /jobs/jeonse/collect` | `{"year_month":"202606","district_count":71,"saved_count":0}` (HTTP 200) | 정상 — 동일 월 데이터 기수집(8,180건)으로 dedup, 신규 0건은 정상 |
| `POST /jobs/supply/collect` | `{"fetched_count":500,"saved_count":11}` (HTTP 200) | 정상 — `supply_schedule` 500 → 511건 |

두 호출 모두 200 OK → WR-007의 Slack 에러 알림 분기는 트리거되지 않음 (정상 경로).
**결론:** WR-007은 다음 실행(매주 일요일 05:00 KST)부터 실데이터를 정상 수집한다.
