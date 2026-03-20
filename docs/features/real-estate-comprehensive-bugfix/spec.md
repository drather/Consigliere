# Feature Spec: 부동산 모듈 종합 버그픽스

**Branch:** `fix/real-estate-comprehensive-review`
**작성일:** 2026-03-21
**상태:** 완료

---

## 1. 배경 및 목적

LLM을 Gemini로 전환하는 과정에서 부동산 파이프라인 전반에 다수의 버그가 누적·표면화됨.
기존에 Claude가 감춰줬던 품질 문제, SDK 교체로 인한 신규 오류, 그리고 구조적 불일치가
동시에 드러났다. 본 작업은 이를 체계적으로 수거하고 안정화한다.

---

## 2. 확인된 증상

| 증상 | 발생 위치 |
|---|---|
| Job1 (실거래가 수집) 에러 | `monitor/api_client.py` |
| 인사이트 리포트 점수 45점 (예산 초과 단지 추천) | `agents/specialized.py`, `prompts/` |
| Slack 전송 실패 (`send_blocks` 없음) | `service.py`, `notify/slack.py` |
| Gemini JSON Unterminated string (0점) | `core/llm.py` |

---

## 3. 발견된 버그 목록

### BUG-001 · CRITICAL: MOLIT API resultCode 체크 오류 → Job1 항상 실패 가능

**파일:** `src/modules/real_estate/monitor/api_client.py:57-60`

```python
# 현재 코드
if "<resultCode>00</resultCode>" not in response.text \
        and "<resultCode>000</resultCode>" not in response.text:
    return None
```

**원인:** MOLIT API 정상 응답 코드는 `<resultCode>0</resultCode>` (단일 "0") 인 경우가 있음.
현재 코드는 "00", "000"만 체크하고 "0"은 누락 → 정상 응답을 오류로 판단하고 `None` 반환.

**수정:** `"0"` 포함 체크 또는 에러 코드(`ERROR-*`, `99` 등)로 역방향 체크로 변경.

---

### BUG-002 · CRITICAL: SlackSender.send_blocks() 메서드 미존재

**파일:** `src/modules/real_estate/service.py:289`

```python
# 현재 (오류)
sender.send_blocks(saved.get("blocks", []))

# slack.py의 실제 메서드 시그니처
def send(self, message: str, **kwargs)  # blocks는 kwargs로 전달
```

**원인:** `SlackSender`에는 `send()`만 있고 `send_blocks()`는 없음.
Slack 전송 단계에서 매번 `AttributeError` 발생.

**수정:**
```python
sender.send("부동산 인사이트 리포트", blocks=saved.get("blocks", []))
```

---

### BUG-003 · HIGH: Synthesizer가 예산 범위를 무시하는 단지 추천

**파일:** `src/modules/real_estate/prompts/insight_parser.md`

**원인:** 프롬프트에 예산 준수 강제 조항이 약함. `budget_plan.final_max_price`를 "초과하지 않도록"
지침이 있지만 Gemini 모델이 이를 무시하고 상위 단지(래미안대치팰리스 등 30억+)를 추천.
Validator가 잡아내지만 MAX_ITERATIONS=2 안에 수정이 안 됨 → 낮은 점수로 저장.

**수정:**
- 프롬프트에 하드 제약 강화: `final_max_price`를 명시적 수치로 프롬프트에 삽입
- Validator feedback을 Synthesizer에 더 구체적으로 전달하는 구조 개선

---

### BUG-004 · HIGH: insight_validator.md — 변수명 불일치 (미사용 파일)

**파일:** `src/modules/real_estate/prompts/insight_validator.md`

**원인:** 이 파일은 현재 어디서도 사용되지 않음. 실제 사용되는 건 `strategy_validator.md`.
그러나 `insight_validator.md`의 변수명(`{{report_json}}`, `{{persona_data}}`)과
`strategy_validator.md`의 변수명(`{{generated_report}}`, `{{budget_plan}}`)이 달라서
혼란을 유발하고 오사용 시 전체 Validator가 빈 데이터를 받게 됨.

**수정:** `insight_validator.md` 삭제 또는 `strategy_validator.md`와 통합.

---

### BUG-005 · HIGH: persona.yaml에 interest_areas 필드 없음

**파일:** `src/modules/real_estate/persona.yaml`,
참조: `src/modules/real_estate/service.py:106, 247`

```python
# 코드에서 기대하는 필드
area = persona_data.get("user", {}).get("interest_areas", ["수도권"])[0]
```

**원인:** `persona.yaml`에 `interest_areas` 키가 없음 → 항상 기본값 "수도권"으로 ChromaDB 검색.
개인화된 RAG 정책 팩트 검색이 전혀 동작하지 않음.

**수정:** `persona.yaml`에 `interest_areas` 필드 추가.
```yaml
interest_areas:
  - "강남구"
  - "서초구"
  - "성남시 분당구"
```

---

### BUG-006 · MEDIUM: Gemini generate_json — thinking 토큰이 응답에 혼입 가능

**파일:** `src/core/llm.py:55`

```python
return json.loads(response.text)
```

**원인:** `google-genai` 신규 SDK에서 `response_mime_type: application/json`으로 설정해도,
thinking 모드가 활성화된 경우 `response.text`에 thinking 결과가 섞일 수 있음.
현재 폴백 파싱 로직(정규표현식)은 에러 메시지에서만 JSON을 추출하므로 불충분.

**수정:** `response.text` 전처리 로직 추가 — markdown fence, 앞뒤 텍스트 trim, JSON 경계 추출.
(ClaudeClient의 파싱 로직을 참고해 GeminiClient에도 동일하게 적용)

---

### BUG-007 · MEDIUM: strategy_validator 출력 스키마 vs Orchestrator 불일치

**파일:** `src/modules/real_estate/prompts/strategy_validator.md:27-34`
참조: `src/modules/real_estate/insight_orchestrator.py:85-87`

```python
# orchestrator가 읽는 필드
status = validation_result.get("status", "FAIL")   # "PASS" | "FAIL"
score  = validation_result.get("score", 0)          # 0~100
feedback = validation_result.get("feedback", "")
```

**원인:** strategy_validator 프롬프트 출력 스키마는 위와 일치함 (✓).
그러나 `insight_validator.md`는 `score(1~10)`, `reasoning`, `feedbackForImprovement`를 반환.
두 파일이 공존해서 LLM이 어떤 포맷을 써야 하는지 혼동할 가능성 있음.

**수정:** BUG-004와 동일하게 미사용 파일 제거.

---

## 4. 수정 작업 목록

| ID | 작업 | 파일 | 우선순위 |
|---|---|---|---|
| T-01 | MOLIT resultCode 체크 로직 수정 | `monitor/api_client.py` | P0 |
| T-02 | `send_blocks` → `send(..., blocks=)` 수정 | `service.py` | P0 |
| T-03 | Synthesizer 프롬프트 예산 하드 제약 강화 | `prompts/insight_parser.md` | P1 |
| T-04 | `persona.yaml` interest_areas 추가 | `persona.yaml` | P1 |
| T-05 | GeminiClient generate_json 파싱 강화 | `core/llm.py` | P1 |
| T-06 | `insight_validator.md` 삭제 (미사용 파일 정리) | `prompts/insight_validator.md` | P2 |

---

## 5. 검증 방법

1. `docker logs consigliere_api` 에서 각 Job 에러 없음 확인
2. Job1: `POST /jobs/real-estate/fetch-transactions` → 수집 건수 > 0
3. Job4: `POST /jobs/real-estate/run-pipeline` → score >= 70, Slack 전송 성공
4. 로그에서 `send_blocks AttributeError` 미발생 확인
