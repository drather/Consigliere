# Issues: apt_master_utilization

## 버그 발견 및 결정 사항

### [BUG-01] `_enrich_transactions()` early return이 마스터 DB 조회를 차단

**발견:** Phase 2 TDD 테스트 작성 중
**현상:** `area_intel={}` 또는 `area_intel=None`이면 함수 맨 앞에서 `return txs`하여
아파트 마스터 DB 조회 블록(household_count, constructor, approved_date 부착)에 
도달하지 못함.
**결과:** `household_count=0`이 리포트 파이프라인 전체에 전파 → `_score_liquidity()` 항상 LOW(20점)

**수정:** 마스터 DB 조회 블록을 루프 상단으로 이동, area_intel 유무와 무관하게 항상 실행.
area_intel 없을 때 early continue로 area_intel 관련 로직만 스킵.

---

### [DECISION-01] Streamlit 탭에서 Repository 직접 임포트

**결정:** 대시보드에서 `ApartmentMasterRepository`를 API 경유 없이 직접 import.
**이유:** SQLite 파일이 동일 컨테이너에 있으므로 API 서버 경유는 불필요한 네트워크 오버헤드.
단, 향후 컨테이너 분리 시 FastAPI 엔드포인트 추가가 필요.

---

### [DECISION-02] `search()` limit 기본값 500

**결정:** 기본 500건 제한. `max_household=5000` 슬라이더 최대값도 5000으로 설정.
**이유:** Streamlit 테이블 렌더링 성능 고려. 메서드 파라미터로 노출되어 있으므로
추후 필요 시 호출자에서 변경 가능.

---

### [DECISION-03] `approved_date` 연도 필터: SUBSTR(approved_date, 1, 4)

**결정:** SQLite에서 `SUBSTR(approved_date, 1, 4) BETWEEN ? AND ?` 방식 사용.
**이유:** `approved_date` 필드가 `YYYYMMDD` 형식으로 저장되어 있어, 연도 4자리만
추출하면 문자열 비교로 범위 필터 가능.
