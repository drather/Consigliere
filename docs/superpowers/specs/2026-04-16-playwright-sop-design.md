# Playwright E2E → SOP 통합 설계

**작성일:** 2026-04-16  
**브랜치:** `feature/e2e-real-estate-scenarios`  
**목적:** 기존 SOP에 Playwright 화면단 검증을 Phase 4 하드 블로킹 게이트로 통합

---

## 1. 배경 및 목표

### 배경

현재 SOP(Phase 0~4)는 Phase 2에서 TDD 기반 백엔드 단위 테스트를 의무화하고 있으나,
화면단(Streamlit UI) 검증 절차가 공식 흐름에 포함되어 있지 않다.

`tests/e2e/` 디렉토리와 `scripts/e2e_health_check.py`가 이미 존재하지만,
SOP와 연결되어 있지 않아 실행이 개발자의 기억에 의존한다.

### 목표

- **백엔드:** TDD (pytest) — Phase 2에서 검증
- **화면단:** Playwright E2E — Phase 4 머지 직전에 검증
- 모든 기능이 코드 레벨과 UI 레벨 양쪽에서 검증된 후에만 머지 허용

---

## 2. 워크플로우 변경

### 변경 전 Phase 4

```bash
git checkout master
git merge feature/{feature_name}
arch -arm64 .venv/bin/python3.12 -m pytest tests/ -v
git push origin master
```

### 변경 후 Phase 4

```
Phase 4-1: 백엔드 단위 테스트
  arch -arm64 .venv/bin/python3.12 -m pytest tests/ -v

Phase 4-2: E2E 화면단 검증 (하드 블로킹)
  arch -arm64 .venv/bin/python3.12 scripts/e2e_health_check.py
  → exit 0: 계속 진행
  → exit 1: 머지 중단, 실패 테스트 수정 후 재실행

Phase 4-3: 머지 및 푸시
  git checkout master
  git merge feature/{feature_name}
  git push origin master
```

---

## 3. E2E 면제 조건

화면 변경이 없는 작업(백엔드 리팩토링, DB 스키마 변경, n8n 워크플로우 수정, 문서 작업 등)은
`result.md`에 아래 섹션 기록 시 Phase 4-2 스킵 허용:

```markdown
## E2E 검증 면제

- **사유:** 화면단 변경 없음 (백엔드 리팩토링만 포함)
- **변경 범위:** src/modules/real_estate/repository.py
```

---

## 4. `e2e_health_check.py` 수정 사항

### 4-1. exit code 추가

| 조건 | exit code |
|------|-----------|
| 전체 PASS | 0 |
| 1개 이상 FAIL | 1 |

### 4-2. result.md 자동 섹션 append

스크립트 실행 완료 후 현재 피처의 `docs/features/{feature_name}/result.md`에 자동 append:

```markdown
## E2E 검증 결과

- **실행일시:** YYYY-MM-DD HH:MM
- **결과:** ✅ PASS (N/N) | ❌ FAIL (N/N, M개 실패)
- **리포트:** docs/e2e_health_report.md
- **실패 목록:** (FAIL인 경우만)
  - test_function_name_1
  - test_function_name_2
```

**예외 처리:**
- `result.md` 미존재 시: 경고 출력 후 `docs/e2e_health_report.md`에만 저장
- 피처명 탐지: `git branch --show-current`로 브랜치명에서 `feature/` 접두사 제거하여 디렉토리 탐색

---

## 5. SOP 문서(`sop.md`) 변경 사항

### Phase 4 섹션 교체

기존 Phase 4 블록을 아래로 교체:

```markdown
## Phase 4: Release

### 4-1. 백엔드 단위 테스트
```bash
arch -arm64 .venv/bin/python3.12 -m pytest tests/ -v
```

### 4-2. E2E 화면단 검증 (하드 블로킹)
```bash
arch -arm64 .venv/bin/python3.12 scripts/e2e_health_check.py
```

> exit 0 → 계속 진행  
> exit 1 → 머지 중단, 실패 테스트 수정 후 재실행

> **면제 조건:** 화면 변경 없는 작업은 `result.md`에 `## E2E 검증 면제` 섹션 + 사유 기록 시 스킵 허용

### 4-3. 머지 및 푸시
```bash
git checkout master
git merge feature/{feature_name}
git push origin master
```
```

### 문서 작성 표준 테이블에 행 추가

| 파일 | 내용 | 시점 |
|------|------|------|
| `result.md` | E2E 검증 결과 또는 면제 사유 | Phase 4-2 완료 시 자동 생성 |

---

## 6. 구현 범위 요약

| 대상 | 변경 내용 |
|------|-----------|
| `docs/guidelines/sop.md` | Phase 4 교체 + 문서 표준 테이블 행 추가 |
| `scripts/e2e_health_check.py` | exit code 추가 + result.md 자동 섹션 append |

---

## 7. 비고

- `e2e_health_check.py`의 pytest 실행, JSON 리포트 파싱, 마크다운 생성 로직은 기존 유지
- 신규 E2E 테스트 작성은 이 설계 범위 밖 (기존 `tests/e2e/` 흐름 그대로)
- git hook 방식은 우회 가능성 + 개발 흐름 방해로 채택하지 않음
