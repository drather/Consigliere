# Issues: 커리어 Daily Report

## 발견된 이슈 및 해결 내역

---

### ISSUE-001: ARM64 아키텍처 ImportError
- **증상:** `arch -arm64` 없이 pytest 실행 시 `ImportError: dlopen(pydantic_core... incompatible architecture (have 'arm64', need 'x86_64')` 발생
- **원인:** `.venv/bin/activate` 활성화만으로는 ARM64 강제 실행이 안 됨. 시스템 Python이 x86_64로 해석
- **해결:** 모든 Python 실행을 `arch -arm64 .venv/bin/python3.12` 또는 `arch -arm64 .venv/bin/pip`으로 통일
- **예방:** `.claude_instructions.md`, `.gemini_instructions.md`에 ARM64 실행 규칙 명문화

---

### ISSUE-002: `with patch()` 컨텍스트 매니저로 CareerAgent 모킹 실패
- **증상:** `AttributeError: module 'modules.career' has no attribute 'service'`
- **원인:** `CareerAgent.__init__`이 LLMClient, PromptLoader 등 외부 의존성을 직접 생성 → 테스트에서 `__init__` 우회가 어려움
- **해결:** `object.__new__(CareerAgent)`로 `__init__` 완전 우회 후 인스턴스 속성 직접 주입, `types.MethodType`으로 메서드 바인딩
- **예방:** 다음 모듈부터 DIP 적용 — 생성자에 인터페이스 주입 받도록 설계

---

### ISSUE-003: SOLID Review에서 35개 개선 포인트 식별
- **HIGH (즉시 수정):**
  - LLM Processor 3종: try/except 없어 파이프라인 전체 크래시 위험 → 수정 완료
  - HackerNewsCollector `_fetch_ids()`: 예외 전파 → try/except 추가 완료
  - WantedCollector `resp.json()` 파싱 오류 미처리 → 수정 완료
- **MEDIUM (이번 스프린트 수정):**
  - SRP: PersonaManager가 CareerAgent 내부에 혼재 → `persona_manager.py`로 분리 완료
  - WeeklyReporter/MonthlyReporter: 예외 전파 → fallback 반환값 추가 완료
  - HistoryTracker: JSON 파싱 오류 개별 파일 skip 처리 완료
  - CareerConfig: YAML 파싱 오류 처리 완료
- **LOW (다음 스프린트):**
  - 이모지 하드코딩 (DailyReporter, CareerPresenter)
  - OCP: BaseProcessor 추상화
  - DIP: LLMClient → ILLMClient 인터페이스화

---

### ISSUE-004: bs4 (beautifulsoup4) 미설치
- **증상:** `ModuleNotFoundError: No module named 'bs4'`
- **해결:** `arch -arm64 .venv/bin/pip install beautifulsoup4`

---

### ISSUE-005: 원격 브랜치 push 거부 (non-fast-forward)
- **증상:** `README.md` 변경이 원격에만 존재해 push 거부
- **해결:** `git pull origin master --no-rebase` → merge commit 생성 후 push 성공

---

## 미해결 이슈 (다음 스프린트)

| ID | 내용 | 우선순위 |
|----|------|----------|
| LOW-001 | 이모지 하드코딩 → 상수화 또는 config 외부화 | LOW |
| LOW-002 | BaseProcessor 추상화 (OCP 강화) | LOW |
| LOW-003 | ILLMClient 인터페이스 도입 (DIP 완성) | LOW |
| LOW-004 | 실거래 n8n 워크플로우 E2E 통합 테스트 미수행 | MEDIUM |
| LOW-005 | API 엔드포인트 E2E 테스트 미수행 | MEDIUM |
