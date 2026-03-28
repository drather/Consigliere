# Progress: Job4 토큰 최적화 & 안정화

## 상태: ✅ 전체 완료

| Phase | 상태 | 비고 |
|-------|------|------|
| 이슈 문서화 | ✅ 완료 | 2026-03-25 |
| json_repair 적용 (Issue 4) | ✅ 완료 | 2026-03-25 |
| LLM Claude 전환 (Issue 1 임시) | ✅ 완료 | 2026-03-25, LLM_PROVIDER=claude |
| Job1/2/3 중복 방지 (Issue 3 부분) | ✅ 완료 | 2026-03-25, 마커 파일 방식 |
| 프롬프트 입력 토큰 축소 | ✅ 완료 | 2026-03-28, tx/policy_facts/persona 슬림화 |
| Validator 예산 강제 구조화 | ✅ 완료 | 2026-03-28, 화이트리스트 + 적응형 스코어카드 |
| 파이프라인 실행 Lock | ✅ 완료 | 2026-03-28, pipeline_running.lock + try/finally |
| SOLID 리팩토링 | ✅ 완료 | 2026-03-28, P1~P5 전체 |

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
- 2026-03-28: 핵심 이슈 해결
  - **화이트리스트 강제**: service.py에서 budget filter 후 단지명 목록 추출 → Synthesizer 프롬프트에 명시
  - **insight_parser.md 절대 규칙 추가**: 목록 외 단지 추천 즉시 기각 명시
  - **입력 토큰 슬림화**: TX_SLIM_FIELDS(12개 필드), policy_facts content[:500], persona 핵심 키만 전달
  - **Validator 적응형 스코어카드**: available_complex_count에 따라 required_ranks 동적 조정 (가용 단지 < 3개 대응)
  - **retry 3회 → 2회**: Synthesizer 최대 호출 횟수 감소 (최악 LLM 호출 4회→3회)
  - 43개 테스트 전부 통과 (7개 신규 TestAdaptiveScorecardValidator 포함)
- 2026-03-28: SOLID 리팩토링 완료
  - **P5 (silent exceptions)**: service.py 3개 bare except에 logger.warning/debug 추가
  - **P1 (pipeline lock)**: `_pipeline_lock_path()` + `pipeline_running.lock` try/finally 적용 → 동시 실행 차단
  - **P4 (LSP/naming)**: `CodeBasedValidator` → `ReportValidator` 리네임 + 하위호환 alias 유지
  - **P3 (DIP)**: `InsightOrchestrator.__init__` optional injected agents 파라미터 추가
  - **P2 (SRP)**: `PersonaManager` + `PreferenceRulesManager` → `persona_manager.py` 분리, service.py 위임 래퍼로 교체
  - 테스트 6개 업데이트 (PersonaManager 경로 패치 방식 반영), 43개 전부 통과
