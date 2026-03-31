# Coding Guide

**Last Updated:** 2026-03-31

## 1. 언어 규칙

| 대상 | 언어 |
|------|------|
| 기술 문서 (spec, progress, result, history) | **한글** |
| 코드 & 주석 | **English** |
| 사용자 대면 메시지 (Slack 리포트 등) | **한국어** |

---

## 2. SOLID 원칙 (필수)

모든 도메인 모듈에 의무 적용. **Phase 2.5 SOLID Review는 선택이 아닌 필수.**

| 원칙 | 규칙 |
|------|------|
| **SRP** | 각 클래스는 하나의 책임만. God Class 금지. |
| **OCP** | 새 에이전트/모듈은 Base 클래스 상속으로 추가. 기존 코드 수정 금지. |
| **DIP** | 구체 클래스가 아닌 추상 인터페이스(`BaseAgent` 등)에 의존. |
| **Zero Hardcoding** | API 코드, 금리, 지역코드 등 변경 가능한 값은 반드시 `config.yaml` 또는 `.env` 관리. |
| **Composability** | 모든 서비스는 독립적으로 테스트 가능하고 다른 모듈에서 재사용 가능하게 설계. |

---

## 3. TDD (Test-Driven Development) — 필수

> **"No test, no code."** 테스트 없이 로직을 먼저 구현하는 것은 금지.

**사이클:** Red (실패 테스트 작성) → Green (최소 구현) → Refactor

**테스트 파일 위치:**
```
tests/
├── modules/
│   ├── career/
│   ├── real_estate/
│   └── finance/
├── api/
└── conftest.py
```

**실행:**
```bash
# 전체
arch -arm64 .venv/bin/python3.12 -m pytest tests/ -v

# 특정 모듈
arch -arm64 .venv/bin/python3.12 -m pytest tests/modules/career/ -v
```

---

## 4. LLM 사용 규칙

- **Import:** `from core.llm import LLMClient` — LLM SDK 직접 import 금지
- **JSON 생성:** 반드시 `llm.generate_json(prompt)` 사용. `eval()` 절대 금지.
- **TaskType 라우팅:**
  - `TaskType.EXTRACTION` → haiku (빠른 추출)
  - `TaskType.ANALYSIS` / `TaskType.SYNTHESIS` → sonnet (깊은 분석)
- **캐싱:** 반복 호출이 예상되는 경우 `CachedLLMClient` 사용 (Decorator 패턴)
- **Prompt Caching:** 프롬프트 파일에 `cache_boundary` frontmatter로 캐시 경계 지정

---

## 5. n8n 워크플로우 규칙

- **절대 금지:** n8n JSON을 스크래치부터 작성 — 스키마 오류 원인
- **템플릿 사용:** `src/n8n/templates/`의 기존 템플릿 기반으로 수정
- **배포:** `scripts/deploy_workflows.py` 사용 (멱등성 보장, 자동 활성화)
- **등록 의무:** 신규 워크플로우는 반드시 `docs/workflows_registry.md`에 등록
