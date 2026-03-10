# 기능 명세서 (Spec): 부동산 실거래가 모니터링 고도화 (Real Estate Monitoring Enhancement)

## 개요 (Overview)
이 기능은 기존에 구축된 부동산 실거래가 모니터링 워크플로우를 고도화하는 작업입니다. 현재는 단순하게 거래 데이터를 가져와 시스템 로컬에 저장하고 대시보드에만 표출하고 있습니다.
이번 업데이트를 통해 **수도권 전일자 실거래 내역**을 요약하고, 해당 매물의 위치를 직관적으로 파악할 수 있도록 **지도 링크(네이버 또는 카카오맵)**를 첨부하여 매일 아침 **Slack 채널로 알림을 전송**하는 자동화 파이프라인을 구축합니다.

## 목표 (Goals)
1.  **워크플로우 자동화 (n8n)**: 매일 지정된 시간(예: 08:00 KST)에 자동으로 동작하는 `real_estate_monitor_slack.json` 워크플로우 생성.
2.  **데이터 수집 및 정제 (FastAPI)**: 국토교통부 API 등을 활용하여 '전일자'의 '수도권' 아파트 실거래가 데이터를 추출 및 필터링.
3.  **지도 연동 (Map Integration)**: 슬랙 메시지에서 바로 위치를 확인할 수 있게 아파트 명칭/지역 정보를 조합한 지도 검색 URL 제공.
4.  **슬랙 알림 전송**: 이전 단계에서 완성된 `/notify/slack` 엔드포인트를 재사용하거나, n8n의 HTTP Request 노드를 활용하여 포맷팅된 결과(Markdown 형식 혹은 Slack Block Kit)를 전송.

## 시스템 아키텍처 (Architecture)

1.  **n8n 자동화 워크플로우 (`src/n8n/templates/real_estate_monitor_slack.json`)**:
    *   **트리거 (Trigger)**: Schedule Node를 사용 (cron: `0 8 * * *`).
    *   **데이터 요약 생성**: 시스템 내부의 FastAPI 엔드포인트 호출.
        *   *(설계 결정)*: n8n 내부에서 자바스크립트로 복잡하게 데이터를 구성하고 가공하는 대신, 데이터 핸들링에 강점을 가진 Python(FastAPI) 쪽에 전일자 통합 요약 리포트를 생성하는 API(`GET /api/v1/real_estate/daily_summary`)를 신설하여 호출합니다.
    *   **알림 발송 (Notification)**: HTTP Request Node를 이용해 백엔드의 `/notify/slack` 엔드포인트로 포맷팅된 payload를 전송.

2.  **FastAPI 백엔드 로직 (`src/modules/real_estate/`)**:
    *   **Service**: 기존 `RealEstateService`를 확장하여 `get_daily_summary(date)` 메서드 추가 작성.
    *   **지도 링크 생성 (Map URL Generation)**: 건별 거래 데이터에 네이버/카카오 지도 검색 링크 부착 (예: `https://map.naver.com/v5/search/{아파트_명칭}+{법정동}`).
    *   **Endpoint**: `GET /api/v1/real_estate/daily_summary` 에서 슬랙 발송용 텍스트 반환.

## 사용자 확인 요청 항목 (User Review Required)
> [!IMPORTANT]
> 로직 구현 전, 아래 내용에 대한 선호도를 알려주시면 맞춤형으로 개발을 시작하겠습니다.
> 1.  **지도 링크 서비스**: [네이버 지도]와 [카카오맵] 중 선호하시는 서비스가 있으신가요?
> 2.  **슬랙 메시지 스타일**: [일반 마크다운 텍스트] 방식과 UI가 조금 더 깔끔한 [Slack Block Kit] 중 어느 것을 원하시나요?
> 3.  **데이터 필터링 조건**: 서울/수도권 하루치 전체 데이터는 양이 꽤 될 수 있습니다. 특정 필터링 조건 (예: 거래금액 O억 이상, 특정 구(district) 위주, 혹은 전체 데이터의 간략 요약본) 등 원하시는 필터가 명확히 있으신지 궁금합니다.

## 개발 계획 항목 (Proposed Changes)

### 코어 로직 및 API 신설
#### [MODIFY] src/modules/real_estate/service.py
- 지정된 날짜의 요약 보고서를 텍스트로 만들어주는 `get_daily_summary(target_date)` 메서드 추가.
- 각 매물 데이터 반복 시 지도 링크 생성 로직 반영.

#### [MODIFY] src/main.py (or router file)
- `GET /api/v1/real_estate/daily_summary` 라우트를 추가.

### n8n 워크플로우 템플릿 추가
#### [NEW] src/n8n/templates/real_estate_monitor_slack.json
- 스케줄링 노드 -> API 요약 리포트 GET 요청 노드 -> 슬랙 전송 노드로 이어지는 n8n JSON 파일 생성.

#### [MODIFY] docs/workflows_registry.md
- 생성된 신규 워크플로우를 레지스트리 문서에 등록.

## 검증 계획 (Verification Plan)

### 자동화 테스트 (Automated Tests)
- `pytest tests/test_real_estate.py` 테스트 케이스를 추가하여 요약 리포트와 지도 링크 생성 기능이 정상 구동하는지 검증.

### 수동 검증 (Manual Verification)
- FastAPI의 백그라운드 MCP 시스템(`deploy_workflow`)을 통해 n8n 컨테이너로 해당 템플릿 배포.
- 브라우저나 n8n API를 통해 워크플로우 강제 1회 실행 유도 (Manual Trigger).
- 지정된 슬랙 채널을 통해 정상적으로 포맷팅된 데이터와 살아있는(클릭 가능한) 지도 링크가 알림으로 오는지 핸드폰/PC에서 확인.
