# Workflow SOP (Standard Operating Procedure)

Follow this exact cycle for every new feature or major refactor:

## Phase 0: Preparation
1. **Update Context:** Update `docs/context/active_state.md` with the new focus.
2. **Check Infrastructure:** Ensure Docker services are running (`docker-compose up -d`).
3. **Branching:** Create a feature branch: `git checkout -b feature/{feature_name}`.
4. **Setup Docs:** Create directory `docs/features/{feature_name}/`.

## Phase 1: Planning (Spec First)
1. **Write Spec:** Create `docs/features/{feature_name}/spec.md`. Define goals, architecture, and data models. MUST refer to `docs/master_plan.md`. 
   - **Artifact Sync:** If you created an `implementation_plan.md` during planning, merge its technical details and proposed changes into this spec.
2. **Init Log:** Create `docs/features/{feature_name}/progress.md` with a To-Do list.
3. **Commit:** Commit the plan before writing code.

## Phase 2: Implementation (TDD)
1. **Code:** Implement the feature in `src/modules/{domain}/` or apply refactoring changes.
2. **Test:** Write unit/integration tests in `tests/`.
3. **Verify:** Ensure tests pass (e.g., `pytest`).
4. **Log:** Update `progress.md` as tasks are completed.

## Phase 2.5: SOLID Review & Refactoring (MANDATORY)
구현이 완료되면 **반드시 아래 체크리스트를 검토**하고, 미충족 항목은 즉시 리팩토링합니다.

### ✅ SOLID 원칙 준수 체크리스트
- [ ] **SRP (단일 책임):** 각 클래스/함수가 하나의 책임만 갖는가? God Class가 없는가?
- [ ] **OCP (개방-폐쇄):** 새 기능을 추가할 때 기존 코드를 수정하지 않아도 되는가? (예: 새 에이전트 = 새 클래스)
- [ ] **DIP (의존성 역전):** 구체 클래스가 아닌 추상 인터페이스(`BaseAgent` 등)에 의존하는가?

### ✅ 코드 품질 체크리스트
- [ ] **Zero Hardcoding:** 모든 변경 가능한 값(API 코드, 금리, 임계값 등)이 `config.yaml` 또는 `.env`에 있는가?
- [ ] **재사용성:** 구현된 서비스/함수가 다른 도메인 모듈에서도 재사용 가능한 구조인가?
- [ ] **테스트 가능성:** 의존성이 주입 가능하여 각 컴포넌트를 독립적으로 테스트할 수 있는가?
- [ ] **에러 처리:** 외부 API 호출 및 LLM 응답에 모두 예외 처리가 되어 있는가?

### ✅ 리팩토링 후 회귀 테스트
1. 기존 테스트 전체 재실행: `pytest`
2. Docker 재기동 후 E2E 확인: `docker compose restart api`
3. API 엔드포인트 직접 호출로 기능 무결성 확인

## Phase 3: Documentation & Review
1. **Record Issues:** Log any bugs/fixes in `docs/features/{feature_name}/issues.md`. Use findings from debugging sessions.
2. **Update Snapshot:** CRITICAL. Update `docs/system_snapshot/` if any structural changes were made.
3. **Finalize:** Write `docs/features/{feature_name}/result.md` (API Usage, Summary).
   - **Proof of Work:** ALWAYS merge the content of your `walkthrough.md` here. **Include visual verification (screenshots, recordings)** of the UI and test results. Use relative paths for images stored in the feature directory.
4. **Update History:** Add a summary entry to `docs/context/history.md`.

## Phase 4: Release
1. **Merge:** Switch to `master` and merge the feature branch natively via `git merge`.
2. **Verify:** Run all tests on `master`.
3. **Push:** `git push origin master`
.
