# Feature Spec: Job4 토큰 최적화 & 안정화

## 1. 배경 및 현황

### 통합 테스트 결과 (2026-03-24 ~ 2026-03-25)

전체 파이프라인(Job1→2→3→4→Slack)을 실제 실행해 다음 이슈가 확인됨.

---

## 2. 확인된 이슈

### 🔴 Issue 1: Job4 과도한 토큰 소모 (치명적)

**현상**
- Gemini 2.5-flash: 파이프라인 3중 실행(curl timeout 중 중복 트리거) → 당일 spending cap 초과(429 RESOURCE_EXHAUSTED)
- Claude Sonnet 4.6: ContextAnalystAgent 1회 호출에 약 80초, Synthesizer 1회 호출에 약 2분 소요
- 3회 retry loop 기준 총 LLM 호출: ContextAnalyst 1회 + Synthesizer 최대 3회 = **최대 4회 호출, ~10분**

**원인 분석**
- `insight_parser.md` 프롬프트가 단지별 기준별 섹션 (교통/학군/생활편의/환금성/가격상승가능성) 전체를 서술하도록 요구
- `context_analyst.md` 프롬프트도 거시경제 + 실거래 분석을 단일 호출에 통합
- `persona_data`, `policy_context`, `policy_facts`, `tx_data` 전체를 JSON 직렬화해 프롬프트에 삽입 → 입력 토큰 수천~수만

**임시 해결**: LLM_PROVIDER=claude 로 전환 (Gemini API 월 한도 소진)

---

### 🔴 Issue 2: Validator Score 고착 (Score 40, 3회 retry 전부 실패)

**현상**
```
Score 40 < 75 on attempt 1, retrying...
Score 40 < 75 on attempt 2, retrying...
Score 40 < 75 on attempt 3, retrying...
→ Synthesizer failed after 3 attempts
```

**Validator 피드백 내용**
```
예산 한도 10% 초과 단지: 10.53억, 13.13억 (한도: 8.7억). 예산 이하 단지만 추천하십시오.
출퇴근편의성 항목에 commute_minutes_to_samsung(분 단위 수치)가 인용되지 않았습니다.
```

**원인 분석**
- Budget filter로 실거래 데이터에서 16건 제거 후 **잔여 4건**만 남음
- 4건은 모두 예산 내 단지이나, LLM이 `analyst_insight` 또는 `area_intel.json` 에서 검색한 **다른 단지들을 프롬프트 내 컨텍스트에서 뽑아 추천**함
- `commute_minutes_to_samsung` 필드가 일부 단지에 없어 LLM이 임의 값을 사용 또는 생략

**근본 원인**: Budget filter는 입력 tx 데이터에만 적용되고, LLM은 프롬프트 전체 컨텍스트(area_intel, policy_facts 등)에서 다른 단지명을 읽어 추천 가능

---

### 🟡 Issue 3: 병렬 파이프라인 중복 트리거

**현상**
- curl 600초 timeout 설정 → 응답 대기 중 새 요청 유입 → 동일 시각 파이프라인 3개 동시 실행
- Job1~3은 멱등성 있으나 LLM 호출 3중 실행 → 토큰 3배 소모

**현재 대응**: Job1/2/3 당일 완료 마커 파일 도입 (Job1: `.done` 파일, Job2: `_News.md`, Job3: `_macro.json`)
**미해결**: 파이프라인 자체 실행 중 플래그 없음 → 중복 LLM 호출 가능

---

### 🟡 Issue 4: JSON 파싱 실패 (해결됨)

**현상**
```
Expecting ',' delimiter: line 9 column 6 (char 197)
```

**원인**: mrkdwn 블록 내 이모지(`⚡🎒`) + 한국어 + 줄바꿈 조합 시 Gemini가 JSON 문자열 내 제어문자 미이스케이프 또는 missing comma 출력

**해결**: `json_repair` 라이브러리 도입 (5단계 fallback 파싱 체인)
- 단계1: 마크다운 펜스 제거 후 `json.loads`
- 단계2: outermost `{}` 추출 후 `json.loads`
- 단계3: `\n\r\t` + 기타 제어문자 이스케이프 후 `json.loads`
- 단계4: `json_repair` 복구 후 `json.loads`
- 단계5: raw 응답 로깅 + `{"error": ...}` 반환

---

### 🟢 Issue 5: BOK 거시경제 `101Y001` 데이터 없음 (경미)

**현상**: `⚠️ No data found for 101Y001` — 기준금리 관련 항목 빈값

**원인**: BOK sample API key 한계 (특정 시계열 항목 접근 불가)

---

## 3. 목표 (Definition of Done)

| 이슈 | 현재 | 목표 |
|------|------|------|
| Job4 토큰 소모 | ContextAnalyst ~80초, Synthesizer ~120초/회 | 각 30초 이내 |
| Validator Score | 40점 고착 (3회 실패) | 75점 이상 1~2회 내 통과 |
| 파이프라인 중복 실행 | 마커 파일로 Job1/2/3만 방지 | 파이프라인 전체 실행 lock |
| LLM 제공자 | Gemini (한도 소진) | Claude Sonnet 4.6 (전환 완료) |

---

## 4. 해결 방향

### 4-1. 토큰 절감 (최우선)

**프롬프트 입력 축소**
- `tx_data`: 전체 거래 목록 대신 단지별 최신 1건 + 평균가만 전달
- `policy_facts`: 전체 JSON 대신 상위 3건 요약 텍스트만 전달
- `persona_data`: 리포트에 필요한 필드만 선택적 전달 (interest_areas, budget_plan, priority_weights)
- `policy_context`: DuckDuckGo 검색 결과 원문 대신 요약본만 전달

**ContextAnalyst + Synthesizer 통합 검토**
- 현재 2회 LLM 호출 → 1회로 통합 가능한지 검토 (컨텍스트 분석 + 리포트 생성 동시)

**출력 구조 단순화**
- Slack Block Kit 직접 생성 대신 구조화된 중간 포맷 생성 후 코드로 Block Kit 변환

### 4-2. Validator 예산 강제 구조화

**근본 해결**: LLM 프롬프트에 "이 단지 목록에서만 선택하라" 명시
- `budget_filtered_complexes`: 예산 내 단지명 리스트를 별도 변수로 전달
- Validator 피드백이 3회 반복되면 LLM이 학습 못 한다는 신호 → 프롬프트 레벨 강제 필요

### 4-3. 파이프라인 실행 Lock

- Redis 또는 파일 기반 lock (`pipeline_running.lock`) 도입
- 파이프라인 시작 시 lock 생성, 완료/실패 시 해제
