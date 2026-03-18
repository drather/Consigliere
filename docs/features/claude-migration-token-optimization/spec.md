# Spec: Claude LLM 전환 및 토큰 최적화

## 개요
- **작업 일자:** 2026-03-18
- **목표:** 애플리케이션의 기본 LLM을 Gemini에서 Claude로 전환하고, 부동산 인사이트 리포트 실행 중 발생한 버그 수정 및 토큰 사용량 최적화

---

## 배경 및 동기

1. `sw_development.md` 가이드라인에 기본 LLM으로 `claude-sonnet-4-6` 사용이 명시되어 있었으나, `LLMFactory` 코드의 기본값이 여전히 `"gemini"`로 설정되어 있었음
2. Claude로 전환 후 인사이트 리포트를 실행하는 과정에서 JSON 파싱 오류가 연속 발생
3. 요청 1건당 최대 300,000 토큰에 근접하는 과도한 토큰 사용 확인

---

## 작업 범위

### 1. LLM 기본값 전환
- `src/core/llm.py`: `LLMFactory` 기본값 `"gemini"` → `"claude"`
- `.env.example`: Claude 설정 항목 추가, Gemini Optional로 이동

### 2. JSON 파싱 버그 수정
- `ClaudeClient.generate_json` max_tokens 4096 → 8192 (응답 truncation 방지)
- JSON 경계 추출 로직 추가 (`{` ~ `}` 파싱으로 앞뒤 텍스트 무시)
- `generate_json`에 `max_tokens` 파라미터 추가 (호출처별 토큰 제어)

### 3. 토큰 사용량 최적화
- `MAX_ITERATIONS` 3 → 2 (LLM 호출 최대 6회 → 4회)
- Validator `max_tokens` 8192 → 1024 (소형 JSON 출력만 필요)
- `daily_txs` 상한 20건 → 15건
- `policy_facts` RAG 결과 5건 → 3건

---

## 관련 파일

| 파일 | 변경 유형 |
|---|---|
| `src/core/llm.py` | 버그 수정 + 최적화 |
| `src/modules/real_estate/agents/specialized.py` | 최적화 |
| `src/modules/real_estate/insight_orchestrator.py` | 최적화 |
| `src/modules/real_estate/service.py` | 최적화 |
| `.env.example` | 설정 업데이트 |
