# Issues: 아파트 마스터 × Market Monitor 통합

**Feature:** `apt-master-monitor-integration`

---

## BUG-01 — AppTest에서 `No module named 'modules.real_estate.apartment_master'`

**증상:** `tests/test_real_estate_tab5.py` 3개 테스트가 모듈 임포트 오류로 실패.

**원인:**
- `src/modules/` 및 `src/modules/real_estate/`에 `__init__.py` 없음 (namespace package)
- AppTest는 별도 실행 환경에서 파일을 실행하므로 `conftest.py`의 sys.path 수정이 적용되기 전에 모듈 임포트가 시도될 수 있음
- `real_estate.py` 최상단의 모듈 레벨 try/except가 `src.` 접두사 경로로 fallback 시, `modules.*` 경로가 sys.modules에 미등록되어 함수 내부 임포트 실패

**해결:**
- `repository.py`, `service.py` 내부의 `from modules.real_estate.models import ApartmentMaster`를 try/except ImportError 패턴으로 교체
- Tab1 함수 내부 임포트도 동일 패턴 적용:
  ```python
  try:
      from modules.real_estate.apartment_master.repository import ApartmentMasterRepository
  except ImportError:
      from src.modules.real_estate.apartment_master.repository import ApartmentMasterRepository
  ```

---

## DECISION-01 — Tab5 완전 제거, Tab1을 "아파트 탐색"으로 대체

**결정:** 기존 Tab1(Market Monitor 실거래가 조회)을 완전히 삭제하고 Tab5(단지 검색)를 "아파트 탐색"으로 대체.

**이유:** 두 화면이 기능상 중복되며, 아파트 마스터 기반 필터로 먼저 단지를 특정한 뒤 실거래가를 보는 흐름이 UX적으로 우수. 탭 수 5→4로 감소.

---

## DECISION-02 — 함수 내부 임포트 (lazy import) 유지

**결정:** `ApartmentMasterRepository`, `RealEstateConfig` 임포트를 Tab1 블록 내부에서 수행.

**이유:** 모듈 레벨에서 임포트 시 DB 초기화가 앱 로드 시점에 발생하여 다른 탭 진입 시에도 오버헤드 발생. Lazy import로 "아파트 탐색" 탭 진입 시에만 DB 연결.

---

## DECISION-03 — `_render_apt_detail_panel()` SRP 분리

**결정:** 상세 패널 렌더링 로직(~80 line)을 별도 함수로 추출.

**이유:** Tab1 블록의 단일 책임 원칙 준수. 상세 패널 로직이 독립적으로 테스트 가능해짐.
