# Result: 입지점수 카드 "근거 보기" 빈 항목 표시 수정

## 구현 결과

- **수정 파일**: `src/dashboard/views/real_estate.py` — `_render_score_dimension_grid()` (line 193)
- **변경 내용**:
  - `evidence`가 비어있고 학군프리미엄(`🎒`)이 아닌 dimension 카드 → "데이터 없음 (POI 캐시 미수집)" 캡션 표시
  - 학군프리미엄 카드는 evidence 유무와 관계없이 `_render_school_detail()`(라이브 API) 항상 호출 — 기존 동작 유지

## TDD

- `tests/test_real_estate_evidence_fallback.py` 신규 작성
  - Red: `1 failed, 1 passed` (`test_empty_evidence_shows_fallback_caption` 실패)
  - Green: `2 passed`

## Playwright MCP 검증 (localhost:8501)

- **"문정시영"(A13820007, 버그 재현 단지)**:
  - 수정 전: 🚇교통/🏫교육환경/🛒생활인프라/🏥의료/🌳자연환경 5개 카드의 "근거 보기"가 완전히 빈 박스
  - 수정 후: 동일 5개 카드에 "데이터 없음 (POI 캐시 미수집)" 캡션 표시, 🎒학군프리미엄은
    `_render_school_detail()` 라이브 학군 상세 테이블이 정상 표시됨 (변경 없음)
- **"한국"(A40381801, 부평구, 회귀 확인 단지)**:
  - 11개 "근거 보기" 카드 전부 기존 evidence 내용 그대로 정상 렌더링 (회귀 없음)
- `docker restart consigliere_dashboard` 후 8501에서 위 결과 재확인

## 회귀 테스트

```
8 failed, 897 passed, 1 error
```

- 머지 전 baseline(`apt-detail-card-redesign` 완료 시점): `8 failed/895 passed/1 error`
- 동일한 8건 실패(career/dashboard_ui/real_estate_insight/real_estate_tab5/job4 — 본 작업과 무관,
  기존 flaky/pre-existing 실패) + 신규 테스트 2건(passed) → `895 + 2 = 897`
- **신규 실패 없음**

## 스코프 외 (별도 추적)

- POI 캐시 재수집 + `location_score` 재계산은 `docs/context/active_state.md`
  "알려진 후속 과제 (이어서)"에서 별도 작업으로 추적 중 — 완료 시 fallback 캡션 대신
  실제 evidence가 자동으로 표시됨 (코드 변경 불필요).
