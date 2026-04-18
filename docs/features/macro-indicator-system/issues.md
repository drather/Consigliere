# Issues & Decisions: 거시경제 지표 수집 시스템

**작성일:** 2026-04-18

---

## BUG-01: st.stop() 전역 스크립트 종료

- **증상:** Insight, Report Archive, 페르소나 탭이 모두 빈 화면
- **원인:** `with tab1:` 블록 내 `st.stop()` 호출 시 Streamlit이 스크립트 전체를 중단 — 후속 탭2/3/4 미렌더링
- **수정:** Tab1 내용을 `_render_apt_search_tab()` 헬퍼 함수로 추출, `st.stop()` → `return` 교체
- **학습:** Streamlit에서 `st.stop()`은 함수 스코프가 아닌 전역 스코프에서 동작

---

## BUG-02: BOK_API_KEY Docker 컨테이너 미주입

- **증상:** 수집 Job 실행 후 기준금리(1개)만 데이터 수집
- **원인:** `docker-compose restart`는 env_file을 재적용하지 않음 → sample 키로 폴백
- **수정:** `docker-compose up -d --force-recreate api`로 컨테이너 재생성
- **예방책:** 환경변수 변경 시 반드시 `--force-recreate` 사용

---

## BUG-03: BOKClient 분기(Q) 날짜 포맷 오류

- **증상:** 가계신용, GDP 지표 수집 시 0건 반환
- **원인:** BOK ECOS Q frequency 기간 형식이 `YYYYQ#` (예: `2023Q1`)인데 코드에서 `%Y%m` 형식(`202301`) 사용
- **수정:** `bok_client.py`에 Q 분기 처리 분기 추가
  ```python
  elif frequency == "Q":
      start_date = f"{start_dt.year}Q{(start_dt.month - 1) // 3 + 1}"
  ```

---

## BUG-04: BOK stat_code 5개 오류

| 지표 | 원래 코드 | 수정 코드 | 사유 |
|------|-----------|-----------|------|
| M2 | 101Y001 | 161Y007 | 신지표 계열로 이전됨 |
| 가계신용 | 600Y001/? | 151Y001/1000000 | 코드 변경, item_code 확정 |
| CPI | 902Y009 | 901Y009 | 국제 비교 통계 → 국내 통계로 수정 |
| GDP | 200Y001/10101 | 200Y102/10211 | 주요지표 분기표에서 전년동기비 항목 |
| COFIX | 121Y013 | - (비활성화) | BOK ECOS 미제공 (은행연합회 발표) |

---

## DECISION-01: 공유 모듈 구조

- **결정:** `src/modules/macro/`를 도메인 중립 공유 패키지로 신설
- **배경:** real_estate, finance 등 여러 도메인에서 거시경제 지표 재사용 필요
- **트레이드오프:** 단기 복잡도 증가 vs. 장기 중복 제거

## DECISION-02: COFIX 제외

- **결정:** COFIX 지표 is_active=False 비활성화
- **배경:** COFIX는 전국은행연합회 발표 지표로 BOK ECOS API 미제공 확인
- **대안:** 예금은행 주택담보대출 금리(id=2)가 유사 역할 수행

## DECISION-03: 십억원 → 조원 표시

- **결정:** 대시보드에서 `십억원` 단위 지표는 `조원`으로 변환 표시 (/ 1000)
- **배경:** 4,099,505.7십억원 표시는 가독성 저하
- **표시:** 4,100조원, 1,979조원
