# 부동산 모듈 종합 버그픽스: Issues Log

## BUG-001 · CRITICAL: MOLIT API resultCode "0" 누락 → Job1 항상 실패
- **파일:** `src/modules/real_estate/monitor/api_client.py`
- **증상:** 정상 응답임에도 `None` 반환, 실거래가 수집 0건
- **원인:** `<resultCode>0</resultCode>` 케이스가 체크 목록(`"00"`, `"000"`)에서 누락
- **수정:** 에러 코드 역방향 체크로 변경 (정상 코드를 열거하는 대신 에러 코드를 배제)
- **Status:** ✅ 해결

---

## BUG-002 · CRITICAL: SlackSender.send_blocks() 메서드 미존재
- **파일:** `src/modules/real_estate/service.py`
- **증상:** 파이프라인 마지막 Slack 전송 단계에서 매번 `AttributeError` 발생
- **원인:** `SlackSender`에 `send_blocks()`가 없고 `send(message, **kwargs)`만 존재
- **수정:** `sender.send("...", blocks=saved.get("blocks", []))` 로 교체
- **Status:** ✅ 해결

---

## BUG-003 · HIGH: Synthesizer가 예산 범위를 무시하는 단지 추천
- **파일:** `src/modules/real_estate/prompts/insight_parser.md`
- **증상:** `final_max_price` 초과 단지(30억+) 추천 → Validator 점수 45점
- **원인:** 프롬프트 예산 제약 조항이 약해 Gemini가 무시, MAX_ITERATIONS=2 안에 수정 불가
- **수정:** 프롬프트에 `final_max_price` 수치를 명시 삽입, 하드 제약 문구 강화
- **Status:** ✅ 해결

---

## BUG-004 · HIGH: insight_validator.md 미사용 파일 (변수명 불일치)
- **파일:** `src/modules/real_estate/prompts/insight_validator.md`
- **증상:** 실제 사용 파일(`strategy_validator.md`)과 변수명 불일치로 혼란 유발
- **원인:** 레거시 파일이 삭제되지 않고 잔존
- **수정:** 파일 삭제
- **Status:** ✅ 해결

---

## BUG-005 · HIGH: persona.yaml interest_areas 필드 없음
- **파일:** `src/modules/real_estate/persona.yaml`
- **증상:** 개인화 RAG 검색이 항상 기본값 "수도권"으로 동작
- **원인:** 코드에서 참조하는 `interest_areas` 키가 YAML에 없음
- **수정:** `interest_areas: ["강남구", "서초구", "성남시 분당구"]` 추가
- **Status:** ✅ 해결

---

## BUG-006 · MEDIUM: Gemini generate_json — thinking 토큰 혼입
- **파일:** `src/core/llm.py`
- **증상:** `Unterminated string` JSON 파싱 오류, 점수 0점
- **원인:** thinking 모드 활성 시 `response.text`에 thinking 결과가 섞임
- **수정:** 응답 전처리 강화 — markdown fence 제거, JSON 경계(`{`~`}`) 추출 로직 추가
- **Status:** ✅ 해결

---

## BUG-007 · MEDIUM: Calculator DSR/LTV rate 파싱 오류
- **파일:** `src/modules/real_estate/calculator.py`
- **증상:** LLM이 stress rate(한도)를 실제 rate로 반환 → 예산 계산 오류
- **원인:** rate 파싱 로직이 두 값을 구분하지 못함
- **수정:** stress rate와 actual rate 분리 파싱, approval threshold 90점으로 상향
- **Status:** ✅ 해결

---

## PERF-001: Job1 순차 처리 → 병렬화 (ThreadPoolExecutor)
- **파일:** `src/modules/real_estate/service.py`
- **증상:** 71개 구 순차 수집 시 약 24분 소요
- **원인:** for loop 단일 스레드, blocking HTTP (requests.get)
- **수정:** `concurrent.futures.ThreadPoolExecutor(max_workers=8)` 적용, 스레드별 독립 `TransactionMonitorService()` 인스턴스 생성
- **기대 효과:** ~24분 → ~3분 (약 8배 개선)
- **Status:** ✅ 해결

---

## PERF-002: Job1 병렬화 — OOM (Out of Memory)
- **파일:** `src/modules/real_estate/service.py`
- **증상:** ThreadPoolExecutor(max_workers=8) 실행 시 컨테이너 OOM kill (exitCode=137)
- **원인:** 8개 스레드가 동시에 `save_transactions_batch` 호출 → ChromaDB onnxruntime 임베딩 병렬 실행 → 메모리 폭발
- **확인:** `docker events --filter event=oom` → `container oom` 이벤트 확인
- **1차 대응:** fetch/save 분리 (병렬 fetch + 직렬 save), max_workers=3으로 축소
- **Status:** ⚠️ 부분 완화 (여전히 불안정)

---

## PERF-003: Job1 병렬화 — MOLIT API 429 Rate Limit
- **파일:** `src/modules/real_estate/monitor/api_client.py`
- **증상:** max_workers=3에서도 429 Too Many Requests 발생
- **원인:** 국토부 API 동시 3개 이상 요청 시 차단. 허용 동시 요청 수 미공개.
- **1차 대응:** 429 재시도 로직 추가 (exponential backoff: 1s, 2s, 4s, 최대 3회)
- **근본 해결:** aiohttp + asyncio.Semaphore(2) 전환 → 내일 구현 예정
- **Status:** ⚠️ 임시 완화, 근본 해결 필요

---

## PERF-004: 국토부 API 일일 호출 횟수 초과
- **증상:** 2026-03-21 저녁 기준 모든 MOLIT API 호출 실패
- **원인:** 하루 동안 반복 테스트(OOM/429 재시도 과정)로 일일 허용 횟수 소진
- **완화:** API 호출 횟수는 자정(KST) 기준으로 리셋. 내일 새벽 이후 재시도 가능.
- **근본 해결:** 3일 필터 도입 시 호출 횟수 자체가 1회/구/일로 고정 (71회/일)
- **Status:** ⏳ 내일 자동 해소 예정

---

## PERF-005: MOLIT API 페이지네이션 미구현
- **파일:** `src/modules/real_estate/monitor/api_client.py`
- **증상:** numOfRows=100 고정, pageNo=1만 호출 → 월 100건 초과 구 데이터 누락
  - 실제 100건 반환 구: 수원 권선구, 의정부시, 안산 단원구, 고양 덕양구 등
- **원인:** `totalCount` 파싱 및 페이지 반복 로직 없음
- **영향:** 3일치 필터 도입 시 100건 미만으로 수렴 예상 → 우선순위 낮춤
- **Status:** 🔵 우선순위 낮음 (3일 필터 후 재평가)
