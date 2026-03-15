# Specification: Architecture Refactoring & Quality Improvement

## 1. 개요 (Overview)
본 문서는 Consigliere 시스템의 전반적인 아키텍처 개선, 결합도 낮추기, 확장성 증대 및 클린 코드(SOLID) 관점에서의 리팩토링 방향성을 정의합니다. 이는 `architecture_review.md` 에서 논의된 이슈들을 해결하기 위한 구체적인 기술 명세입니다.

## 2. 목표 (Goals)
1.  **의존성 주입(Dependency Injection) 기반 아키텍처 전환**: 서비스 클래스들이 구체적인 외부 인프라스트럭처 모델(DB, Slack)에 직접 의존하지 않도록 변경합니다. (DIP 원칙 준수)
2.  **API 라우팅 구조 개선**: 단일 `main.py`에 집중된 엔드포인트를 도메인별(Finance, Real Estate, Automation, Notify) 라우터로 분리하여 유지보수성을 높입니다. (SRP 윈칙 준수)
3.  **중앙 집중식 로깅 체계 구축**: 파편화된 로그 파일을 일원화하고 관리 가능한 파일 로그 체계를 구축합니다.
4.  **자동화 테스트(Test Automation) 전략 적용**: 리팩토링 과정 중 발생할 수 있는 기능 훼손(Regression)을 방지하기 위한 단위(Unit) 및 통합(Integration) 테스트 기반을 마련합니다.
5.  **프로젝트 구조 위생 파악**: 산발적으로 존재하는 유틸리티/테스트 스크립트 도구화 및 AI 지침서 세분화.

## 3. 구조적 변경 사항 (Architecture Changes)

### 3.1. API 라우터 분리 (FastAPI)
-   `src/api/routers/` 구조 신설
    -   `finance.py`: `/agent/finance/*`, `/dashboard/finance/*` 라우팅
    -   `real_estate.py`: `/agent/real_estate/*`, `/dashboard/real-estate/*` 라우팅
    -   `automation.py`: `/agent/automation/*` (n8n 연동 등) 라우팅
    -   `notify.py`: `/notify/slack` 등 알림 관련 라우팅
    -   `system.py`: 루트(`/`) 헬스체크 등 일반 엔드포인트
-   `src/main.py`: 최소한의 FastAPI Application 생성 및 `include_router`만을 담당합니다.

### 3.2. 의존성 역전 및 주입 (Dependency Injection)
-   **대상 클래스**: `RealEstateAgent`, `FinanceAgent` 등 `src/modules/...` 산하의 코어 비즈니스 로직.
-   **구현 방향**:
    -   `__init__` 에 필요한 의존성을 인터페이스 형태로 전달받습니다. (예: `repository: StorageProvider`, `llm_client: LLMClient`, `notifier: Sender`)
    -   `main.py` 혹은 `dependencies.py` (FastAPI `Depends()`) 에서 컨테이너 역할을 하며 의존성 인스턴스를 주입합니다.
    -   이를 통해 테스트 수행 시 Mock Object를 주입하여 쉽게 검증할 수 있도록 변경합니다.

### 3.3. 멀티 LLM 지원 아키텍처 (LLM Backend Abstraction)
-   **현재 이슈**: `src/core/llm.py` 내의 `LLMClient` 가 `google.generativeai` (Gemini)에 강하게 결합되어 있어, Claude 등 다른 모델로의 전환이 어렵습니다.
-   **구현 방향**:
    -   `BaseLLMClient` 인터페이스(추상 클래스)를 정의하고, 필수 메서드(`generate`, `generate_json`)를 선언합니다.
    -   `GeminiClient` 와 `ClaudeClient` 가 각각 위 인터페이스를 상속받아 구현하도록 분리합니다.
    -   환경 설정(예: `.env`의 `LLM_PROVIDER=claude`)에 따라 팩토리(Factory) 패턴을 사용하여 동적으로 생성된 객체를 Agent에 주입(DI)합니다.

### 3.4. 로깅 체계 (Centralized Logging)
-   **로그 수집 경로**: `logs/` 디렉토리 신설 (Git-ignored)
-   **로거 설정**: `src/core/logger.py` 에 기본 애플리케이션 싱글톤 로거 객체를 세팅합니다.
    -   레벨, 포매팅(Time, Module, Level, Message) 적용 가이드 수립.
    -   모든 `print()` 함수를 로거의 `info()`, `warning()`, `error()` 콘솔/파일 양립형 출력으로 교체.

### 3.5. 디렉토리 구조 최적화 및 문서 관리
-   루트의 `run_server.py`, `deploy_slack_router.py`, `test_slack.py` 등 관리되지 않는 실행 스크립트들을 `scripts/` 밑으로 재정렬합니다.
-   `Dockerfile`은 추후 필요시 서비스별 Multi-stage 빌드 구조로 전환하기 좋게 `build/` 디렉토리에 레퍼런스 작성을 고려하거나 주소화합니다. (우선 현 로컬 상태에서는 로깅/코드 개선 주력)
-   `.gemini_instructions.md`의 내용을 `docs/guidelines/sw_development.md`, `infrastructure_env.md`, `workflow_sop.md` 로 기능 분할합니다.

## 4. 검증 계획 (Verification Plan)

-   **모듈별 단위 테스트 작성**: `tests/` 폴더 내에 의존성 주입된 Agent 객체의 Mock-Unit 테스트 코드를 구축하여 1차적으로 비즈니스 로직의 이상유무 파악.
-   **API 통합 테스트 보완**: `TestClient` 를 통해 분리된 라우팅 체계 하에서 각 리포트 생성, 슬랙 전송 엔드포인트 등이 기존과 동일하게 JSON 200 반환하는지 증명합니다.
-   **로깅 출력 검증**: 모든 서비스 가동 및 API 호출 시, 지정된 `logs/system.log` 계열의 파일에 데이터가 정상 포맷으로 남는지 확인합니다.
