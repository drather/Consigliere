# Building Master — 스펙 요약

**상세 설계 문서:** [`docs/superpowers/specs/2026-04-23-pnu-building-master-design.md`](../../superpowers/specs/2026-04-23-pnu-building-master-design.md)

---

## 목표

건축HUB 건축물대장 API(총괄표제부)를 통해 수도권 아파트 단지의 공식 메타데이터를 수집하고, `building_master` 테이블을 구축한 뒤 기존 `apt_master`와 이름 유사도 기반으로 매핑하여 투자 분석 필드(준공연도·세대수·용적률 등)를 보강한다.

## 아키텍처

```
건축HUB 총괄표제부 API (getBrRecapTitleInfo)
  → BuildingRegisterClient (법정동 코드별 수집, 페이지네이션)
  → BuildingMasterService (수집 + 매핑 오케스트레이션)
  → BuildingMasterRepository → building_master 테이블
  → AptMasterRepository.update_building_mapping() → apt_master.pnu
```

## 주요 결정 사항

- **API 엔드포인트:** 기본개요(getBrBasisOulnInfo) 대신 **총괄표제부(getBrRecapTitleInfo)** 사용 — 기본개요는 단지명/용도 필드가 없어 수집 불가
- **bjdong 코드 필수:** API는 sigunguCd 단독 쿼리 시 빈 결과 반환 → `discover_bjdong_codes()`로 법정동별 자동 탐색 후 수집
- **아파트 필터:** `etcPurps` 필드에 "아파트" 포함 여부로 판별
- **매핑 전략:** `apt_master.district_code`(시군구)로 후보군 좁힌 뒤 `difflib.SequenceMatcher` 이름 유사도 ≥ 0.8 매핑
- **mgm_pk:** 건축HUB PK를 `building_master.PRIMARY KEY`로 사용 (apt_master.pnu에 FK로 저장)
