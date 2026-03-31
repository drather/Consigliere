# Standard Operating Procedure (SOP)

**Last Updated:** 2026-03-31

> **"No code without a spec. No merge without a result doc."**

모든 피처/버그픽스/리팩토링은 아래 사이클을 반드시 따른다.

---

## Phase 0: Preparation

1. `docs/context/active_state.md` 업데이트 (현재 브랜치, 피처명, 상태)
2. Docker 서비스 상태 확인: `docker-compose up -d`
3. 피처 브랜치 생성: `git checkout -b feature/{feature_name}`
4. 문서 디렉토리 생성: `docs/features/{feature_name}/`

---

## Phase 1: Planning (Spec First)

1. `docs/features/{feature_name}/spec.md` 작성 (한글)
   - 목표, 아키텍처, 데이터 모델 정의
   - 반드시 `docs/master_plan.md` 참조
2. `docs/features/{feature_name}/progress.md` 생성 (할 일 목록)
3. 코드 작성 전 커밋

---

## Phase 2: Implementation (TDD)

1. **테스트 먼저:** `tests/modules/{domain}/test_*.py` 작성 (Red)
2. 최소 로직 구현 (Green)
3. 테스트 통과 확인: `arch -arm64 .venv/bin/python3.12 -m pytest tests/ -v`
4. `progress.md` 체크리스트 실시간 업데이트

---

## Phase 2.5: SOLID Review (MANDATORY ⭐)

구현 완료 후 **반드시** 아래 체크리스트를 검토하고, 미충족 항목은 즉시 리팩토링.

### SOLID 원칙
- [ ] **SRP:** 각 클래스/함수가 하나의 책임만 갖는가? God Class가 없는가?
- [ ] **OCP:** 새 기능 추가 시 기존 코드를 수정하지 않아도 되는가?
- [ ] **DIP:** 구체 클래스가 아닌 추상 인터페이스에 의존하는가?

### 코드 품질
- [ ] **Zero Hardcoding:** 변경 가능한 값이 모두 `config.yaml` / `.env`에 있는가?
- [ ] **재사용성:** 다른 도메인 모듈에서도 재사용 가능한 구조인가?
- [ ] **테스트 가능성:** 의존성 주입 가능하여 독립 테스트가 되는가?
- [ ] **에러 처리:** 외부 API 호출 및 LLM 응답에 예외 처리가 되어 있는가?

### 리팩토링 후 회귀 테스트
```bash
arch -arm64 .venv/bin/python3.12 -m pytest tests/ -v
docker compose restart api
```

---

## Phase 3: Documentation

1. `docs/features/{feature_name}/issues.md` — 버그/결정 사항 기록
2. `docs/system_snapshot/` 업데이트 (구조 변경 시 필수)
3. `docs/features/{feature_name}/result.md` 작성 — walkthrough, 스크린샷 포함
4. `docs/context/history.md`에 요약 항목 추가

---

## Phase 4: Release

```bash
git checkout master
git merge feature/{feature_name}
arch -arm64 .venv/bin/python3.12 -m pytest tests/ -v
git push origin master
```

---

## 문서 작성 표준

| 파일 | 내용 | 시점 |
|------|------|------|
| `spec.md` | 목표, 아키텍처, 데이터 모델 | Phase 1 시작 시 |
| `progress.md` | 할 일 체크리스트 | Phase 1 생성, Phase 2 실시간 업데이트 |
| `issues.md` | 버그, 의사결정, 트레이드오프 | Phase 2~3 |
| `result.md` | 구현 결과, walkthrough, 검증 증거 | Phase 3 완료 시 |
