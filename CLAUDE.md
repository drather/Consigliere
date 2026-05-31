# Consigliere — AI Agent Instructions

## 1. Golden Rule: 작업 시작 전 필독 순서

어떤 작업이든 시작 전 아래 파일을 순서대로 읽는다:

1. `docs/context/active_state.md` — 현재 무엇을 하고 있는가
2. `docs/master_plan.md` — 전체 방향과 절대 진실
3. `docs/context/history.md` — 과거 작업 이력 및 결정 배경
4. `docs/guidelines/architecture.md` — 계층구조·SOLID·DI 원칙 (필수)

---

## 2. 빠른 참조

| 주제 | 파일 |
|------|------|
| **아키텍처 원칙 (계층구조·SOLID·DI)** | [`docs/guidelines/architecture.md`](docs/guidelines/architecture.md) |
| 개발환경 (ARM64, Docker, 환경변수) | [`docs/guidelines/environment.md`](docs/guidelines/environment.md) |
| 인프라 구성 (컨테이너, 포트, 네트워크) | [`docs/guidelines/infra.md`](docs/guidelines/infra.md) |
| 코딩 가이드 (TDD, LLM, n8n, DI 패턴) | [`docs/guidelines/coding_guide.md`](docs/guidelines/coding_guide.md) |
| 작업 표준 절차 및 문서 작성 표준 | [`docs/guidelines/sop.md`](docs/guidelines/sop.md) |
| 멀티 에이전트 오케스트레이션 | [`docs/guidelines/orchestration.md`](docs/guidelines/orchestration.md) |

---

## 3. 핵심 원칙 요약

- **Layered Architecture 필수** — 계층 경계 준수. `docs/guidelines/architecture.md` 참조
- **No test, no code.** 테스트 먼저 작성 후 로직 구현 (TDD)
- **No code without a spec. No merge without a result doc.** SOP 4단계 필수
- **Phase 2.5 SOLID Review는 선택이 아닌 필수**
- **Zero Hardcoding** — 변경 가능한 값은 반드시 `config.yaml` / `.env`
- **ARM64 필수** — `arch -arm64 .venv/bin/python3.12` 형식으로만 실행
