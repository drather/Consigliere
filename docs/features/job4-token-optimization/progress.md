# Progress: Job4 토큰 최적화 & 안정화

## 상태: 🔄 진행 중

| Phase | 상태 | 비고 |
|-------|------|------|
| 이슈 문서화 | ✅ 완료 | 2026-03-25 |
| json_repair 적용 (Issue 4) | ✅ 완료 | 2026-03-25 |
| LLM Claude 전환 (Issue 1 임시) | ✅ 완료 | 2026-03-25, LLM_PROVIDER=claude |
| Job1/2/3 중복 방지 (Issue 3 부분) | ✅ 완료 | 2026-03-25, 마커 파일 방식 |
| 프롬프트 입력 토큰 축소 | ⏳ 미착수 | |
| Validator 예산 강제 구조화 | ⏳ 미착수 | |
| 파이프라인 실행 Lock | ⏳ 미착수 | |

## 로그

- 2026-03-24: 전체 파이프라인 통합 테스트 실행
  - Job1: 71개 구 수집 완료 (~14분), Job2/3 정상
  - Job4: Gemini JSON 파싱 오류로 3회 전부 실패
  - Gemini spending cap 초과 (3중 실행으로 당일 한도 소진)
- 2026-03-25: json_repair 도입 + LLM Claude 전환
  - JSON 파싱 문제 해결 확인 (Score 40 반환 → 파싱 성공)
  - 새 문제 확인: Validator Score 40 고착 (예산 초과 단지 반복 추천)
  - 토큰 과소모 확인: Claude 기준 ContextAnalyst 80초, Synthesizer 2분/회
  - docker stop (토큰 절약)
