# Issues: 아파트 마스터 DB 구축

## DIP 개선 여지 (기록)
- 현재 `RealEstateAgent.__init__()`에서 `ApartmentMasterClient`, `ApartmentMasterRepository`를 직접 생성
- Protocol 인터페이스(`ApartmentMasterClientProtocol`, `ApartmentMasterRepositoryProtocol`) 정의 후 DI 컨테이너로 주입하면 테스트 시 mock 교체가 더 용이해짐
- 현재 규모에서는 직접 생성으로도 충분하며, SOLID 중기 개선 시 함께 적용 예정

## 건축물대장 API (Phase 2 보류)
- 용적률(`vlRat`), 건폐율(`bcRat`)은 건축물대장 기본개요 API에서만 제공
- 이 API는 지번(bun/ji)이 필수 파라미터이나, 공동주택 기본정보 API 응답에는 지번 미포함
- 추가 주소 변환 단계 필요 → 복잡도 증가로 Phase 2에서 별도 구현 예정
- `ApartmentMaster.floor_area_ratio`, `building_coverage_ratio` 필드는 예약해 둠

## API 응답 형식 주의사항
- 공동주택 단지 목록 API: 단지가 1건일 때 `item`이 list 대신 dict로 반환됨 → client.py에서 list로 강제 변환 처리
- API 호출 제한: data.go.kr 기본 일 10,000건, 수도권 71개 지구 × 평균 100단지 = 약 7,100건 → 1일 초과 없음
