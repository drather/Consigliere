# Result: apt_master_utilization

**완료일:** 2026-04-10
**브랜치:** `feature/apt_master_utilization`

---

## 구현 요약

### 1-A. 실거래가 분석 품질 향상

#### 버그 수정: `_enrich_transactions()` early return

**파일:** `src/modules/real_estate/service.py`

**문제:** `area_intel={}` 일 때 `if not area_intel: return txs` 로 함수가 조기 반환되어
마스터 DB 조회 블록 전체가 실행되지 않았음.
→ 리포트 파이프라인 전체에서 `household_count=0`, `constructor=""`, `approved_date=""` 상태 유지
→ `_score_liquidity()` 항상 LOW (20점) 반환

**수정:** 마스터 DB 조회 로직을 루프 맨 앞으로 이동, `area_intel` 유무와 무관하게 항상 실행.

```python
# 변경 전
if not area_intel:
    return txs
# ... (아파트 마스터 조회는 루프 아래쪽에만 위치)

# 변경 후
for tx in txs:
    # 아파트 마스터 조회 — 항상 실행
    master = self.apt_master_service.get_or_fetch(...)
    if master:
        tx["household_count"] = master.household_count
        tx["constructor"] = master.constructor
        tx["approved_date"] = master.approved_date
    if not area_intel:
        enriched.append(tx)
        continue
    # area_intel 관련 로직...
```

#### 리포트 서술: 건설사·준공연도 자동 포함

**파일:** `src/modules/real_estate/prompts/report_synthesizer.md`

각 단지 서술 템플릿에 다음 항목 추가:
```
단지 정보: [constructor] 시공, [approved_date 앞 4자리]년 준공, [household_count]세대 / [building_count]개동
```
값이 없으면 생략하도록 지시.

---

### 1-B. Streamlit 마스터 조회 탭

#### `ApartmentMasterRepository.search()` 메서드 추가

**파일:** `src/modules/real_estate/apartment_master/repository.py`

동적 WHERE 조건 조합으로 SQLite 검색:
- `apt_name`: cache_key LIKE 부분일치
- `district_code`: cache_key prefix 매칭
- `min_household` / `max_household`: 세대수 범위
- `constructor`: LIKE 부분일치
- `approved_year_start` / `approved_year_end`: SUBSTR(approved_date,1,4) BETWEEN

`get_distinct_constructors()` 메서드도 추가 (드롭다운용).

#### Streamlit `🏗️ 단지 검색` 탭 추가

**파일:** `src/dashboard/views/real_estate.py`

tab5 추가:
- 아파트명 텍스트 입력 (부분일치)
- 지구 드롭다운 (전체 포함)
- 세대수 범위 슬라이더 (0 ~ 5000)
- 건설사 드롭다운 (DB distinct)
- 준공연도 범위 슬라이더 (1970 ~ 2030)
- 결과 테이블 (클릭 선택 → 단지 상세 expander)

---

## 테스트 결과

| 파일 | 케이스 수 | 결과 |
|------|-----------|------|
| `test_scoring_liquidity.py` | 8 | ✅ 전원 PASS |
| `test_enrich_constructor.py` | 7 | ✅ 전원 PASS |
| `test_apt_master_search.py` | 14 | ✅ 전원 PASS |
| **신규 합계** | **29** | ✅ |
| 기존 전체 (관련 파일) | 271 | ✅ (7개 기존 실패는 Gemini import 오류, 무관) |

---

## 변경 파일 목록

| 파일 | 변경 내용 |
|------|-----------|
| `src/modules/real_estate/service.py` | `_enrich_transactions()` 구조 개선 — 마스터 조회 항상 실행 |
| `src/modules/real_estate/apartment_master/repository.py` | `search()`, `get_distinct_constructors()` 추가 |
| `src/modules/real_estate/prompts/report_synthesizer.md` | 건설사·준공연도 서술 지시 추가 |
| `src/dashboard/views/real_estate.py` | `🏗️ 단지 검색` 탭(tab5) 추가 |
| `tests/modules/real_estate/test_scoring_liquidity.py` | 신규 |
| `tests/modules/real_estate/test_enrich_constructor.py` | 신규 |
| `tests/modules/real_estate/test_apt_master_search.py` | 신규 |
