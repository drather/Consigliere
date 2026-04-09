# Progress: 아파트 마스터 DB 구축

**브랜치:** `feature/apartment-master-db`

## Phase 0 — Preparation
- [x] `active_state.md` 업데이트
- [x] `git checkout -b feature/apartment-master-db`
- [x] `docs/features/apartment-master-db/` 생성

## Phase 1 — Planning
- [x] `spec.md` 작성
- [x] `progress.md` 생성
- [ ] 문서 커밋

## Phase 2 — Implementation (TDD)
- [ ] `tests/modules/real_estate/test_apartment_master.py` 작성 (Red)
- [ ] `models.py` — `ApartmentMaster` dataclass
- [ ] `apartment_master/__init__.py`
- [ ] `apartment_master/repository.py` — SQLite CRUD
- [ ] `apartment_master/client.py` — 공공 API 클라이언트
- [ ] `apartment_master/service.py` — build_initial + get_or_fetch
- [ ] `service.py` — RealEstateAgent 주입 + `_enrich_transactions()` 확장
- [ ] `routers/real_estate.py` — 신규 엔드포인트
- [ ] `config.yaml` + `.env.example` 업데이트
- [ ] 전체 테스트 통과 확인

## Phase 2.5 — SOLID Review
- [ ] SRP 확인
- [ ] OCP 확인 (새 API 추가 시 client.py만 수정)
- [ ] DIP 확인 (Protocol 기반 주입)
- [ ] Zero Hardcoding 확인

## Phase 3 — Documentation
- [ ] `issues.md`
- [ ] `result.md`
- [ ] `history.md` 업데이트
- [ ] `active_state.md` 업데이트

## Phase 4 — Release
- [ ] master 머지
- [ ] 전체 테스트 통과
- [ ] push
