# Issues: Claude LLM 전환 및 토큰 최적화

## Issue 1: JSON Truncation (max_tokens 부족)

- **증상:** `Claude LLM JSON Parse Error: Unterminated string starting at: line 92 column 17 (char 4552)`
- **원인:** `ClaudeClient.generate_json`의 `max_tokens=4096` 설정으로 인해 Slack Block Kit JSON 응답이 중간에 잘림
- **해결:** `max_tokens` 4096 → 8192로 상향
- **파일:** `src/core/llm.py`

---

## Issue 2: JSON 앞뒤 텍스트 파싱 실패

- **증상:** `Claude LLM JSON Parse Error: Expecting ',' delimiter: line 1 column 806 (char 805)`
- **원인:** Claude가 JSON 앞뒤에 설명 텍스트를 간헐적으로 추가하여 `json.loads()` 실패
- **해결:** 정규식으로 마크다운 펜스 제거 후 `raw.find('{')` ~ `raw.rfind('}')` 범위 추출
- **파일:** `src/core/llm.py`

---

## Issue 3: 과도한 토큰 사용

- **증상:** 요청 1건 처리에 ~300,000 토큰 사용 (Claude Code 세션 + 앱 API 호출 합산)
- **원인:**
  - `MAX_ITERATIONS=3`으로 LLM 최대 6회 호출
  - Validator가 소형 JSON만 출력하면서도 `max_tokens=8192` 낭비
  - `daily_txs` 최대 20건, `policy_facts` 5건의 대형 컨텍스트
- **해결:** 아래 최적화 적용
  - `MAX_ITERATIONS` 3 → 2
  - Validator `max_tokens` 8192 → 1024
  - `daily_txs` 상한 15건, `policy_facts` 3건
- **예상 절감:** 요청당 토큰 ~30~40% 감소

---

## Issue 4: ChromaDB ONNX 모델 초기 다운로드 지연

- **증상:** 첫 실행 시 ~20초간 응답 없음 (감감무소식)
- **원인:** `all-MiniLM-L6-v2` ONNX 모델(79.3MB)을 컨테이너 최초 실행 시 다운로드
- **해결:** 이후 실행에서는 캐시 사용으로 자동 해소됨
- **비고:** Dockerfile에 모델 사전 다운로드 레이어 추가를 고려할 수 있음 (향후 개선)
