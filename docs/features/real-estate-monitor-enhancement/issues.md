# 발생 이슈 기록 (Issues)

## 1. 테스트 실행 시 무한 대기 (Hang) 문제

### **문제 현상**
- `RealEstateAgent()` 객체를 초기화할 때 터미널이 응답하지 않고 무한 대기 상태에 빠짐.
- 특히 `arch -arm64 python3` 명령어로 로컬 테스트 스크립트를 실행할 때 두드러짐.

### **원인 파악**
1. **ChromaDB 연결 타임아웃**:
    - `RealEstateAgent`는 내부적으로 `ChromaRealEstateRepository`를 생성함.
    - 리포지토리는 초기화 시 `chromadb.HttpClient`를 통해 데이터베이스 연결 및 컬렉션 체크를 시도함.
    - 현재 `docker-compose.yml`에서 ChromaDB는 컨테이너 내부 8000번 포트를 사용하며, 호스트에는 8001번으로 바인딩되어 있음.
    - 로컬 호스트 환경에서 환경 변수가 제대로 설정되지 않은 채 테스트를 돌리면, 존재하지 않거나 응답하지 않는 내부 네트워크 주소로 계속 요청을 보내며 타임아웃이 발생할 때까지 대기함.
2. **라이브러리 초기화 지연**:
    - `chromadb` 라이브러리 자체가 무거운 편이며, Apple Silicon(ARM64) 환경에서 의존성 라이브러리 로드 시 일시적인 지연이 발생할 수 있음.

### **해결/우회 방안**
- **환경 변수 명시**: 로컬 테스트 시 `CHROMA_DB_HOST=127.0.0.1` 및 `CHROMA_DB_PORT=8001`을 명시적으로 주입해야 함.
- **Mocking 강화**: 실제 DB 연결이 필요 없는 유닛 테스트의 경우, `repository` 계층을 Mock 처리하여 DB 연결 시도 자체를 차단하도록 스크립트 수정.
- **Docker 내부 실행**: 가급적 `docker-compose exec api python ...` 명령을 통해 컨테이너 내부 환경(고정된 네트워크 환경)에서 테스트를 수행하는 것을 권장.

### **최종 해결 (2026-03-10)**
- **호스트 주소 고정**: `src/modules/real_estate/repository.py`에서 기본 호스트를 `localhost` 대신 `127.0.0.1`로 변경하여 macOS 환경의 IPv6 우선 순위로 인한 지연 문제 해결.
- **타입 에러 수정**: `src/modules/real_estate/service.py`에서 누락된 `date` 라이브러리 import를 추가하여 초기화 오류 수정.
- **검증 완료**: `reproduce_hang.py`, `tests/test_real_estate_monitor.py`, `tests/test_real_estate.py`를 통해 정상 동작 확인.

---

## 2. n8n 워크플로우 배포 및 수동 실행 이슈
- **문제 현상**: 
    - `n8n execute` CLI 명령어 실행 시 포트 충돌(5679)로 중단됨.
    - Webhook(POST) 호출 시 워크플로우가 활성 상태임에도 404 Not Found 반환.
- **원인 분석**:
    - **노드 버전 이슈**: 기존 템플릿의 `httpRequest` 노드가 v4.1이었으나, 현재 시스템에서 정상 동작하는 타 워크플로우는 v4.2를 사용 중이었음.
    - **구성 불일치**: `real_estate_news` 워크플로우와 달리 Slack 전송 시 `bodyParameters`가 아닌 `jsonBody`를 사용하여 데이터 전달 구조가 다름.
    - **네트워크 접근**: `api` 컨테이너에 `curl`이 없어 컨테이너 네트워크 간 수동 테스트 시 Python `httpx` 활용 필요.
- **조치 사항 (2026-03-10)**:
    - `real_estate_news`를 참고하여 `real_estate_monitor_slack.json` 템플릿 표준화 (v4.2 노드 사용, `bodyParameters` 적용).
    - 수동 실행을 위한 `Webhook` 노드(path: `real-estate-summary`) 추가 및 재배포 완료 (ID: `eUN3QsBDmx6Scqn3`).
- **남은 과제**:
    - 활성화된 Webhook이 n8n에 정상 등록되었는지 확인 후 최종 수동 트리거 테스트.
    - Slack 메시지의 블록 키트 레이아웃 최종 확인.
