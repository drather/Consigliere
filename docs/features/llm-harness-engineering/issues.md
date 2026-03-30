# Issues: LLM Harness Engineering

## 해결된 이슈

### [I-1] Gemini 테스트 mock 방식
- **문제:** `GeminiClient.__init__` 내 `from google import genai`와 `_make_config` 내 `from google.genai import types`가 테스트 환경에서 import 실패
- **원인:** `google.genai` 패키지가 설치되어 있지 않거나 namespace package 충돌
- **해결:** `GeminiClient.__new__`로 인스턴스 생성 후 속성 직접 주입, `_make_config`는 MagicMock으로 대체

### [I-2] JobPosting 모델 필드 불일치
- **문제:** 초기 테스트에서 `JobPosting(title=..., description=...)` 사용했으나 실제 모델에 해당 필드 없음
- **원인:** `JobPosting` 모델은 `position`과 `skills` 필드 사용 (description 없음)
- **해결:** 실제 모델 구조에 맞게 테스트 재작성. compression은 posting 개수 제한(30개)으로 집중

### [I-3] sys.path 미설정으로 import 실패
- **문제:** 신규 테스트 파일에서 `ModuleNotFoundError: No module named 'core'`
- **원인:** 기존 테스트 파일들은 `sys.path.insert(0, .../src)` 패턴 사용 — 신규 파일 누락
- **해결:** `test_llm_harness.py` 상단에 `sys.path.insert` 추가

## Pre-existing 실패 (내 변경과 무관)

| 테스트 | 원인 |
|--------|------|
| `test_bok_macro.py::test_macro_service_synthesis` | API mock stat_code 매핑 오류 (기존 버그) |
| `test_dashboard_ui.py::test_dashboard_home_render` | 대시보드 렌더링 의존성 |
| `test_n8n_news.py::TestN8nNews::test_news_api_endpoint` | Claude API 크레딧 부족으로 500 응답 |
| `test_news_insight.py::TestNewsInsight::test_daily_report_generation` | Claude API 크레딧 부족 |
| `test_real_estate_insight.py::test_insight_report` | async 함수 지원 미설정 |

git stash로 master 상태에서 동일하게 재현됨을 확인.
