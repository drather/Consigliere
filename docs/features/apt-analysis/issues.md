# Issues & Decisions

## [결정] SupplyRiskAnalyzer 의존성 처리

**배경:** `SupplyRiskAnalyzer.__init__`이 `news_service`, `llm`, `prompt_loader`, `supply_repo` 4개의 복잡한 의존성을 요구함.  
**결정:** `_get_supply_risk()` 내부에서 try/except로 감싸 실패 시 `None` 반환 (graceful degradation).  
**트레이드오프:** DIP 완전 준수보다 기능 안정성 우선. supply_risk가 없어도 나머지 분석은 정상 진행됨.

## [결정] GeocoderService 의존성 주입

**배경:** `_get_supply_risk()` 내부에서 `GeocoderService`를 inline 생성 — DIP 위반.  
**결정:** `geocoder=None` 옵셔널 파라미터로 생성자에 추가. None이면 내부에서 env var로 생성.  
**효과:** 테스트에서 mock geocoder 주입 가능.

## [결정] LLM CLI subprocess 방식

**배경:** API 기반 LLM 사용 시 비용 발생.  
**결정:** `ClaudeCodeClient`(`claude --print`), `GeminiCliClient`(`gemini`)를 subprocess로 호출.  
**트레이드오프:** Docker 컨테이너에서 호스트 바이너리를 볼륨 마운트해야 함. CLI 미설치 시 "분석 실패" graceful degradation.

## [결정] API 라우트 네이밍

**배경:** 기존 라우트는 `/real-estate/` prefix 사용. 신규 라우트는 `/apt/` prefix.  
**결정:** 짧고 직관적인 `/apt/` 유지. 향후 cleanup 시 통일 검토.

## [결정] progress.md Task 10 완료 기준

**배경:** 개발이 master에서 직접 진행됨 (feature branch 없음).  
**결정:** push와 SOP 문서 완성을 완료 기준으로 삼음.

## [버그 수정] formatter lazy import

**문제:** `format_slack`, `format_markdown`이 `analyze()` 메서드 내부에서 lazy import됨.  
**수정:** 모듈 상단으로 이동하여 의존성 가시성 확보.

## E2E 검증 면제

**사유:** 대시보드 버튼 변경은 Streamlit UI이므로 자동화 E2E 적용 어려움.  
**검증 방법:** 수동 검증 — Tab1 단지 선택 → 🔬 심층 분석 버튼 클릭 → 결과 expander 확인.
