# Multi-Agent Orchestration Protocol

**Last Updated:** 2026-03-31

개발 작업 요청이 오면 아래 3-Agent 프로토콜을 따른다.
각 Agent의 상세 지시문은 `.claude/agents/` 하위 파일을 참조한다.

---

## 언제 적용하는가

아래 유형의 요청이 오면 반드시 이 프로토콜을 따른다:
- 새 기능 구현 ("~를 추가해줘", "~를 만들어줘")
- 버그 수정 ("~가 안돼", "~를 고쳐줘")
- 리팩토링 ("~를 개선해줘", "~로 바꿔줘")

단순 질문, 파일 읽기, 설명 요청은 해당하지 않는다.

---

## 3-Agent 흐름

```
사용자 요청
    ↓
[1] PlannerAgent      (.claude/agents/planner.md)
    → spec.md 작성, 구현 범위 확정
    ↓
[2] CoderAgent        (.claude/agents/coder.md)
    → TDD 구현, pytest 실행
    ↓
[3] ValidatorAgent    (.claude/agents/validator.md)
    → 스펙 대조 + SOLID 체크
    ↓
  Pass? ──No──→ CoderAgent에 피드백 전달 (최대 3회)
    ↓ Yes
  문서 업데이트 (result.md, history.md, active_state.md)
```

---

## Orchestrator 실행 규칙

### Step 1 — PlannerAgent 호출
```
Agent(subagent_type="general-purpose") 로 호출
프롬프트: .claude/agents/planner.md 내용 + 사용자 요청 + 현재 컨텍스트
결과물: spec.md 경로 반환
```

### Step 2 — CoderAgent 호출
```
Agent(subagent_type="general-purpose") 로 호출
프롬프트: .claude/agents/coder.md 내용 + spec.md 내용
결과물: 구현 파일 목록 + pytest 결과 반환
```
- pytest 실패 시 CoderAgent 내에서 자체 수정 루프 (최대 3회)
- 3회 후에도 실패 시 ValidatorAgent 호출 없이 Orchestrator에 실패 보고

### Step 3 — ValidatorAgent 호출
```
Agent(subagent_type="general-purpose") 로 호출
프롬프트: .claude/agents/validator.md 내용 + spec.md + 구현 결과
결과물: PASS / FAIL + 피드백 항목 목록
```

### Step 4 — 루프 또는 완료
- **PASS:** result.md 작성 → history.md 업데이트 → active_state.md 업데이트
- **FAIL:** 피드백을 CoderAgent에 전달 후 Step 2부터 재실행
- **최대 반복:** 3회. 3회 후에도 FAIL이면 사용자에게 보고 후 중단

---

## Agent 간 데이터 전달 구조

```
PlannerAgent 출력
├── spec_path: "docs/features/{name}/spec.md"
├── feature_name: str
└── scope: [파일 경로 목록]

CoderAgent 출력
├── implemented_files: [파일 경로 목록]
├── test_files: [테스트 파일 경로 목록]
├── pytest_result: PASS | FAIL
└── pytest_output: str

ValidatorAgent 출력
├── verdict: PASS | FAIL
├── solid_issues: [str]
├── spec_gaps: [str]
└── feedback: str  ← CoderAgent 재호출 시 전달
```
