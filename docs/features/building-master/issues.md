# Building Master — 이슈 및 의사결정 기록

---

## ISSUE-01: 잘못된 API 엔드포인트 사용 [RESOLVED]

**발견:** 실데이터 수집 테스트 시 모든 시군구에서 0건 수집
**원인:** 스펙에 명시된 `getBrBasisOulnInfo`(기본개요)는 `mainPurpsCdNm`, `bldNm` 필드를 반환하지 않음. 응답에 `mainPurpsCdNm: null`, `bldNm: " "`만 포함
**조치:** `getBrRecapTitleInfo`(총괄표제부) 엔드포인트로 교체
- 총괄표제부: `bldNm`(공식 단지명), `etcPurps`("공동주택(아파트)"), `hhldCnt`, `mainBldCnt`, `vlRat`, `bcRat` 포함
- 아파트 필터: `mainPurpsCdNm` 대신 `etcPurps`에서 "아파트" 포함 여부로 판별
- `parse_item`: `total_buildings` 소스 → `mainBldCnt` (구버전 호환: `dongCnt` fallback)

---

## ISSUE-02: API가 sigunguCd 단독 파라미터를 허용하지 않음 [RESOLVED]

**발견:** `sigunguCd=11650` 단독 요청 → `{"body": {}, "header": {"resultCode": "00"}}` 빈 응답
**원인:** 건축HUB API는 `sigunguCd` + `bjdongCd` 조합을 필수로 요구 (문서상 optional로 표기되어 있으나 실제로는 필수)
**조치:** `discover_bjdong_codes(sigungu_cd)` 메서드 구현
- 10100~20000 범위에서 100 단위로 법정동 코드 탐색
- `totalCount > 0`인 코드만 반환
- `fetch_apartments_by_sigungu()` → discover → 법정동별 순환 수집

**성능 영향:** 시군구당 ~90회 탐색 API 호출 발생. 79개 전체 수집 시 약 7,000회 추가 호출 예상. 이어받기 로직(`count_by_sigungu > 0` 스킵)으로 재실행 시 탐색 불필요.

---

## ISSUE-03: .env 키 오타 (HUB_API_KTY) [RESOLVED — 임시 조치]

**발견:** `os.getenv("HUB_API_KEY")` 반환 None
**원인:** `.env` 파일에 `HUB_API_KTY`로 오타 저장됨
**임시 조치:** `os.getenv('HUB_API_KEY') or os.getenv('HUB_API_KTY', '')` fallback 적용
**권장:** `.env` 파일에서 직접 `HUB_API_KTY` → `HUB_API_KEY` 수정 필요 (수동 작업)

---

## ISSUE-04: apt_master 미매핑 원인 분석

**현상:** 4개 구 295건 중 77건(26%)만 매핑 성공
**분석:**
- 성공 케이스: 최신 브랜드 단지명 (래미안퍼스티지, 아크로리버파크 등) → score 1.0
- 실패 케이스:
  - 접두어 포함 ("강남역우정에쉐르" vs "우정에쉐르", score 0.77)
  - 단지번호+건설사 조합 ("까치마을1단지대우롯데선경" vs "까치마을", score 0.47)
  - 동 목록 포함 ("대치우성아파트1동,2동,3동..." score 0.18)
- 결론: apt_master의 이름이 실거래가 신고 시 자유입력 → 비공식명 혼재. building_master 품질 문제 아님

**개선 방향 (미구현, 향후 과제):**
- 주소 기반 2차 매핑 (도로명 주소 유사도 비교)
- 매핑 임계값 조정 (0.8 → 0.7) + 수동 검토 워크플로우

---

## 의사결정: except Exception 범위 조정

**배경:** `AptMasterRepository._init_db()`에서 마이그레이션 오류를 `except Exception`으로 잡는 코드 품질 검토
**결정:** `except sqlite3.OperationalError`로 좁힘 — 실제 오류를 마스킹하지 않도록
