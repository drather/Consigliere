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

## Phase 3: Documentation & Review
1. **Record Issues:** Log any bugs/fixes in `docs/features/{feature_name}/issues.md`. Use findings from debugging sessions.
2. **Update Snapshot:** CRITICAL. Update `docs/system_snapshot/` if any structural changes were made.
3. **Finalize:** Write `docs/features/{feature_name}/result.md` (API Usage, Summary).
   - **Proof of Work:** ALWAYS merge the content of your `walkthrough.md` here. **Include visual verification (screenshots, recordings)** of the UI and test results. Use relative paths for images stored in the feature directory.
4. **Update History:** Add a summary entry to `docs/context/history.md`.

## Phase 4: Release
1. **Merge:** Switch to `master` and merge the feature branch natively via `git merge`.
2. **Verify:** Run all tests on `master`.
3. **Push:** `git push origin master`.
