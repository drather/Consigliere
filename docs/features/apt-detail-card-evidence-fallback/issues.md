# Issues: 입지점수 카드 "근거 보기" 빈 항목 표시 수정

## 1. 근본 원인 — evidence가 scoring 시점에 동결되어 영구 빈 배열로 남음

- `LocationScorer.score()`(`enrich_and_save()` 호출 시점)에서 각 dimension의
  `evidence()`를 1회 계산해 `DimensionResult.evidence: List[str]`에 담고,
  `location_repository.py`가 이를 JSON으로 `location_scores` 테이블에 저장한다.
  이후 화면 렌더링은 이 저장값을 그대로 읽으며 재계산하지 않는다.
- `education`/`living_infra`/`medical`/`nature`/`school_premium`/`transportation`
  dimension(`dimensions/*.py`)의 `evidence()`는 `candidate.get("_poi")`(POI 캐시)가
  없으면 `[]`를 반환한다.
- **결론**: POI 캐시가 없던 시점에 `enrich_and_save()`가 실행된 단지는, 위 dimension들의
  `evidence`가 **영구히 `[]`**로 DB에 고정되어, "근거 보기"를 펼쳐도 빈 박스만 보인다.

## 2. 영향 범위 (DB 확인, 87개 단지 기준)

- `data/real_estate.db`의 `location_scores.residential_results`/`investment_results`를
  파싱한 결과, 4개 단지에서 POI 의존 dimension의 evidence가 `[]`:
  - `A13820007` 문정시영 (송파구)
  - `A43106007` 목련마을2단지대우선경 (안양동안구) — ※ 이 complex_code는 별도 매핑 오류
    이슈로 `active_state.md`의 "발견된 이슈: apt_master complex_code 매핑 오류"에서
    추적 중 (본 작업과 무관)
  - `A13811206` 거여1단지 (송파구)
  - `A43177507` 평촌목련2단지아파트 (안양동안구)
- Playwright 검증: "문정시영"(A13820007)에서 🚇교통/🏫교육환경/🛒생활인프라/🏥의료/🌳자연환경
  5개 카드의 "근거 보기"가 완전히 빈 expander로 렌더링됨을 확인.

## 3. 스코프 결정 — View 계층 한정, 데이터 재수집은 별도 작업

- 이번 수정은 `_render_score_dimension_grid()`에 **fallback 캡션 표시**만 추가
  ("데이터 없음 (POI 캐시 미수집)"). `DimensionResult.evidence` 데이터 모델과
  `location_scores` 저장값은 변경하지 않음.
- **이유**: 근본적으로 evidence를 채우려면 POI 캐시 재수집(`POST /jobs/poi/collect`) +
  `enrich_and_save()` 재실행(location_score 재계산)이 필요한 **데이터 파이프라인 작업**이며,
  이는 이미 `docs/context/active_state.md`의 "알려진 후속 과제 (이어서)"에
  "문정시영(A13820007) 등 POI 캐시가 오래된 단지는 `POST /jobs/poi/collect`로 재수집 필요"로
  추적 중인 별도 작업이다. 본 작업은 그 작업이 완료되기 전까지 "빈 박스로 보이는
  혼란스러운 UI"를 즉시 개선하기 위한 view-layer 핫픽스다.
- `🎒 학군프리미엄` 카드는 evidence가 비어 있어도 `_render_school_detail()`이 항상
  라이브 API를 호출해 별도 데이터를 표시하므로 fallback 캡션 대상에서 제외.

## 4. 향후 과제 (변경 없음, 참고용)

- `active_state.md`의 "알려진 후속 과제 (이어서)": POI 캐시 재수집 후 4개 단지의
  `location_score`를 재계산하면, 본 fallback 캡션 대신 실제 evidence가 표시됨
  (코드 변경 불필요 — `if not evidence` 분기를 자연히 타지 않게 됨).
- `A43106007` complex_code 매핑 오류는 "발견된 이슈: apt_master complex_code 매핑 오류"에서
  별도 추적 중.
