# Progress: 실거래가 중심 아파트 마스터 재설계

**브랜치:** `feature/transaction-first-master`  
**시작일:** 2026-04-14  
**상태:** 🔵 Phase 1 완료 (Spec 작성)

---

## Phase 0: Preparation ✅

- [x] `docs/context/active_state.md` 업데이트
- [x] 브랜치 생성: `feature/transaction-first-master`
- [x] 문서 디렉토리 생성: `docs/features/transaction-first-master/`

---

## Phase 1: Planning ✅

- [x] `spec.md` 작성 — 아키텍처, 데이터 모델, 마이그레이션 전략
- [x] `progress.md` 생성
- [x] Phase 1 커밋

---

## Phase 2: Implementation (TDD)

### 2-A. 데이터 레이어

- [ ] `AptMasterRepository` 테스트 작성 (Red)
  - [ ] `build_from_transactions()` — transactions에서 apt_master 초기 구축
  - [ ] `search()` — apt_name, sido, sigungu 필터
  - [ ] `get_distinct_sidos()`, `get_distinct_sigungus()`
  - [ ] `get_by_id()`, `get_by_name_district()`
- [ ] `AptMasterRepository` 구현 (Green)
- [ ] `TransactionRepository` — `apt_master_id` FK 지원 추가
  - [ ] `get_by_apt_master_id()` 테스트 + 구현

### 2-B. 마이그레이션 스크립트

- [ ] `scripts/migrate_to_transaction_first.py` 작성
  - [ ] Step 1: `apt_master` 테이블 생성 및 transactions에서 초기 적재
  - [ ] Step 2: `complex_code` 매핑 (기존 apt → apt_details)
  - [ ] Step 3: `apartments` → `apt_details` rename
  - [ ] Step 4: `transactions.apt_master_id` FK 추가 및 채우기
  - [ ] `--dry-run` 옵션 지원
- [ ] 마이그레이션 실행 및 검증

### 2-C. API 레이어

- [ ] `GET /dashboard/real-estate/apt-master` 엔드포인트
  - [ ] 필터: apt_name, sido, sigungu, limit
  - [ ] 응답: apt_master + apt_details (있는 경우) 조인
- [ ] `AptMasterRepository` DI 등록 (`api/dependencies.py`)

### 2-D. 대시보드 레이어

- [ ] `real_estate.py` Tab1 — `AptMasterRepository` 기반으로 교체
  - [ ] 검색 필터: apt_name, sido, sigungu (세대수/건설사 필터는 apt_details optional)
  - [ ] 단지 목록 테이블 렌더링
  - [ ] `_render_apt_detail_panel` — apt_master_id 기반 거래 조회
  - [ ] 상세정보 패널: apt_details 있으면 표시, 없으면 "상세정보 없음"
  - [ ] district+fuzzy fallback 제거
- [ ] 지도 뷰 — apt_master 기반으로 교체

---

## Phase 2.5: SOLID Review

- [ ] SRP 검토: AptMasterRepository / AptDetailsRepository 분리 여부
- [ ] OCP 검토: 상세정보 소스 추가 확장성
- [ ] DIP 검토: dashboard가 구체 repo가 아닌 Protocol에 의존
- [ ] Zero Hardcoding 검토: DB 경로 config.yaml
- [ ] 회귀 테스트 전체 통과

---

## Phase 3: Documentation

- [ ] `issues.md` 작성 — 마이그레이션 중 발생한 이슈
- [ ] `result.md` 작성 — 전후 비교, 스크린샷
- [ ] `docs/context/history.md` 업데이트
- [ ] `docs/context/active_state.md` 완료 처리

---

## Phase 4: Release

- [ ] master 브랜치 머지
- [ ] 전체 테스트 통과
- [ ] push
