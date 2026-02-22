# Project Consigliere: Master Plan & Architecture Vision

## 1. Project Overview & Vision (기획 의도)
Project Consigliere는 사용자의 다방면(부동산, 금융, 건강, 커리어 등)에 걸친 기억, 지식, 행동을 관리해 주는 
**개인화된 LLM 기반 비서 플랫폼**입니다. 단순 챗봇을 넘어, 사용자가 설정한 조건이나 주기에 따라 능동적으로 외부 데이터를 수집하고, 분석하여, 적절한 시점에 보고하거나 사용자의 행동(예: 가계부 입력)을 돕는 '자동화된 워크플로우' 중심의 시스템을 지향합니다.

### 1.1 Core Use Cases (예시)
- **[부동산] 능동적 모니터링**: 국토부 API를 통해 관심 지역의 부동산 실거래가를 주기적으로 조회하고, 지정된 시간에 사용자에게 카카오톡이나 메시지로 리포트를 전송.
- **[금융] 손쉬운 지출 관리**: 카드 사용 내역을 간단한 메시지 형태로 클라이언트 앱에 입력하면, LLM이 이를 분석하여 자동으로 가계부(Ledger)에 구조화된 데이터로 기록.
- **[사용자 정의 확장] "코스피 시황 보고"**: 사용자가 채팅을 통해 "코스피 100 중상위 10개 기업의 금일 종가를 매일 17시에 수집해서, 다음날 08시에 보고해줘"라고 요청하면, 시스템이 즉각적으로 해당 기능을 수행하는 파이썬 코드, UI 화면, n8n 워크플로우를 **자동 생성 및 배포**하여 새로운 기능을 플랫폼에 추가.

### 1.2 Ultimate Goal
사용자가 복잡한 코딩이나 설정 없이, 자연어 요청만으로 **원하는 지식(API 연동), 행동(자동화 스케줄링), 기억(DB 저장)** 시스템을 손쉽게 구축하고 관리할 수 있는 무한한 확장성의 개인 비서 플랫폼을 완성하는 것.

---

## 2. System Architecture (현재 도출된 구조)
초기 클라우드(GCP) 기반 설계에서 비용 문제로 인해 **로컬 Docker-Compose 기반의 마이크로서비스 아키텍처**로 전환되었습니다. 

### 2.1 Core Components
시스템은 크게 3개의 독립된 영역(컨테이너 및 클라이언트)으로 구성됩니다.

| Component | Technology | Role |
| :--- | :--- | :--- |
| **Client App** | Streamlit (CLI/Web) or Mobile App | 사용자와의 접점. 채팅 입력, 대시보드 확인, 명령 하달. |
| **Core Server** | FastAPI (Python) | 시스템의 두뇌(LLM/Gemini 연동). 클라이언트 요청 해석, 코드/명령어 생성, DB 읽기/쓰기, 워크플로우(n8n) 제어 도구(MCP) 제공. |
| **Automation Engine** | n8n (Node.js) | 백그라운드 작업 실행을 담당하는 심장. FastAPI가 짜준 각본(JSON)대로 정해진 시간에 작동하여 외부 API를 호출하거나 알림을 전송. |
| **Memory / Vector DB** | ChromaDB / Local Markdown | 사용자의 데이터, 과거 대화 이력, 생성된 시스템 프롬프트 등을 저장. |

### 2.2 System Flow (사용자 정의 기능 생성 시)

1. **[User Request]**: 클라이언트 앱에서 "매일 아침 8시에 날씨 요약 알려줘" 입력
2. **[LLM Processing (FastAPI)]**: 
   - Gemini가 사용자의 의도를 분석.
   - 워크플로우 템플릿(`src/n8n/templates/`)을 바탕으로 실행할 n8n용 JSON 스키마를 동적으로 생성.
3. **[Deployment (MCP 도구 호출)]**:
   - FastAPI 서버에 구현된 MCP(Model Context Protocol) 툴인 `deploy_workflow` 함수가 호출됨.
   - FastAPI가 n8n 컨테이너의 REST API로 통신하여 생성된 워크플로우 JSON을 밀어넣고(Push) 활성화.
4. **[Execution (n8n)]**:
   - n8n이 매일 아침 8시 크론(Cron) 스케줄러에 따라 외부 날씨 API를 찌르고, 그 결과를 사용자에게 전송.
5. **[Logging]**:
   - 생성된 워크플로우는 `docs/workflows_registry.md`에 기록되어, 향후 LLM이 시스템이 무슨 일을 하고 있는지 기억(Context)할 수 있게 함.

---

## 3. Directory & Context Management
시스템이 스스로를 이해하고 확장하기 위해, 파일과 컨텍스트의 관리가 매우 중요합니다.

- **`src/modules/`**: 도메인별(Finance, Real Estate, Automation 등) 핵심 비즈니스 로직.
- **`src/n8n/templates/`**: n8n 워크플로우의 뼈대가 되는 JSON 템플릿 파일 저장소. (LLM이 스크래치부터 JSON을 짜다 실수하는 것을 방지)
- **`docs/context/`**: 시스템의 최신 상태(`active_state.md`) 및 작업 이력(`history.md`)을 관리. LLM이 항상 가장 먼저 읽어야 하는 기억 장소.
- **`docs/system_snapshot/`**: 현재의 인프라, 백엔드 아키텍처, UI 구조를 실시간 문서로 유지 (`infrastructure.md`, `sw_architecture.md`, `ui_structure.md`).

---

## 4. Next Action Plan (현재 Focus와의 연결)
현재 우리는 위 기획을 달성하기 위한 **1단계: 워크플로우 자동화 연동** 작업(`feature/workflow-automation`)의 한가운데에 있습니다. 

**[완료된 사항]**
- 기능 기획(`spec.md`) 및 작업 목록(`progress.md`) 구성.
- n8n 템플릿 디렉토리 구성 완료.

**[진행 예정 사항 (Immediate Focus)]**
- **FastAPI에 MCP 라우터 구현**: Gemini(LLM)가 n8n의 API(컨테이너 `localhost:5678`)에 접근하여 워크플로우를 생성(`POST /workflows`), 활성화(`POST /workflows/{id}/activate`) 할 수 있는 Python 함수 도구들을 `src/modules/automation/` 에 작성해야 합니다.
- 해당 라우터를 통해 실제 워크플로우 하나를 주입하고 작동하는지 테스트(End-to-End)를 진행합니다.
