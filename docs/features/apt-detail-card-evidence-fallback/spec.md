# Spec: 입지점수 카드 "근거 보기" 빈 항목 표시 수정

**Feature:** `apt-detail-card-evidence-fallback`
**Branch:** `master` (직접 작업, 소규모 버그 수정)
**작성일:** 2026-06-14
**참조:** `docs/master_plan.md` §2 (Client App: Streamlit 대시보드),
`docs/features/apt-detail-card-redesign/`(Issue 3: 카드+클릭형 근거 expander)

---

## 배경

`apt-detail-card-redesign`(2026-06-12 머지)에서 입지점수 카드를 2열 그리드 +
"근거 보기" expander 구조로 전환했다. Playwright MCP로 "한국"(부평구, A40381801) 단지를
확인했을 때는 모든 카드의 근거가 정상 표시되었으나, 사용자가 다른 단지에서
"근거 보기"를 클릭하면 expander가 펼쳐지긴 하지만 **내용이 완전히 비어있는** 카드가
다수 발견됨.

## 원인

`_render_score_dimension_grid()`(`src/dashboard/views/real_estate.py:193`)는
`DimensionResult.evidence`를 그대로 순회해서 출력한다:

```python
with st.expander("근거 보기", expanded=False):
    for ev in (getattr(dr, "evidence", None) or []):
        st.caption(f"· {ev}")
```

`evidence`는 `LocationScorer.score()` 호출 시점(`enrich_and_save()`)에 계산되어
`location_scores` 테이블에 JSON으로 저장된다 (`location_repository.py`).
`education`/`living_infra`/`medical`/`nature`/`school_premium`/`transportation` 등
다수 dimension의 `evidence()`는 `candidate.get("_poi")`(POI 캐시 객체)가
없으면 빈 리스트 `[]`를 반환한다 (`dimensions/*.py`).

**즉, POI 캐시가 없던 시점에 location_score가 계산된 단지는 해당 dimension들의
`evidence`가 영구히 `[]`로 저장되어, "근거 보기"를 펼쳐도 아무것도 보이지 않는다.**

- 실제 DB 확인(`data/real_estate.db`): 87개 단지 중 4개(`A13820007` 문정시영,
  `A43106007` 목련마을2단지대우선경, `A13811206` 거여1단지, `A43177507` 평촌목련2단지아파트)가
  `medical`/`nature`/`school_premium` 등의 evidence가 `[]`.
- Playwright 검증: "문정시영"(A13820007) — 🚇교통/🏫교육환경/🛒생활인프라/🏥의료/🌳자연환경
  5개 카드의 "근거 보기"가 완전히 빈 박스로 렌더링됨.

## 목표 (표시 계층 한정)

`_render_score_dimension_grid()`에 **빈 evidence에 대한 fallback 표시**를 추가한다.
- `evidence`가 비어있고 학군프리미엄이 아닌 경우 → "데이터 없음 (POI 캐시 미수집)" 캡션 표시
- 학군프리미엄(`🎒`)은 기존과 동일하게 `_render_school_detail()`(라이브 API)을 항상 호출
  (evidence가 비어도 라이브 API 결과는 표시됨)

**범위 외**: POI 캐시 재수집/location_score 재계산(근본 데이터 수정)은
`docs/context/active_state.md`의 "알려진 후속 과제" (문정시영 등 POI 재수집)로
이미 추적 중인 별도 작업이며, 이번 변경 범위에 포함하지 않는다.

## 데이터 모델 (변경 없음)

- `DimensionResult.evidence: List[str]` — 변경 없음, 빈 리스트는 유효한 상태로 유지
- View 계층(`_render_score_dimension_grid`)만 수정
