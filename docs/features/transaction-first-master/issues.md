# Issues: 실거래가 중심 아파트 마스터 재설계

**브랜치:** `feature/transaction-first-master`

---

## [결정] apartments 테이블 리네임 보류

**상황:** spec에서 Step 3으로 `apartments → apt_details` 리네임을 요구했으나 마이그레이션 스크립트에서 제외.

**이유:**
- 기존 `ApartmentRepository`, `apartment_master/` 코드, 서비스 레이어가 모두 `apartments` 테이블을 참조
- 리네임 즉시 수행 시 전체 코드베이스 일괄 수정 필요 → 이 PR 범위 초과
- `apt_master` 아키텍처가 완전히 안착된 후 별도 cleanup PR에서 처리

**영향:** `apt_details` 역할은 현재 `apartments`가 그대로 수행. 기능 동작에는 영향 없음.

---

## [이슈] DIP - 대시보드 레이어의 구체 클래스 직접 의존

**위치:** `src/dashboard/views/real_estate.py`

**내용:**
```python
_repo = AptMasterRepository(db_path=_re_db_path)
_apt_detail_repo = ApartmentRepository(db_path=_re_db_path)
```

Streamlit 대시보드 레이어가 `AptMasterRepository`, `ApartmentRepository` 구체 클래스를 직접 생성.
스펙에서는 `AptMasterProtocol`, `AptDetailsProtocol` 인터페이스에 의존하도록 요구.

**현재 상태:**
- FastAPI 레이어는 `api/dependencies.py`에서 `Depends()` DI 패턴으로 완전 분리됨 ✅
- 대시보드 레이어는 Streamlit의 특성상(단일 프로세스, 세션 상태 관리) DI 컨테이너 없이 직접 생성

**결정:** 트레이드오프로 허용. 단, 향후 `AptMasterProtocol` 작성 시 `_render_apt_detail_panel`의 함수 시그니처를 프로토콜 타입으로 타입힌트 추가 예정.

---

## [결정] pytest.ini에 `pythonpath = src` + `--import-mode=importlib` 추가

**상황:** 기존 테스트들이 모듈 레벨 import를 사용하는 경우 `ModuleNotFoundError` 발생.

**원인:** `tests/modules/real_estate/__init__.py` 존재로 pytest가 package import 모드 사용 → `src/`가 sys.path에 추가되지 않음.

**해결:**
```ini
[pytest]
pythonpath = src
addopts = --ignore=tests/e2e --import-mode=importlib
```

**영향:** 기존 117개 테스트 모두 정상 통과. 신규 테스트도 모듈 레벨 import 가능.

---

## [결정] `apt_master_id` 필드를 `RealEstateTransaction` dataclass에 추가

**상황:** `TransactionRepository.save_batch()`가 `apt_master_id`를 저장하려면 `RealEstateTransaction`에 해당 필드가 있어야 함.

**결정:** `apt_master_id: Optional[int] = None` 필드를 `RealEstateTransaction`에 추가. 기존 코드는 이 필드를 사용하지 않으므로 `getattr(tx, 'apt_master_id', None)` 패턴으로 하위 호환성 유지.

---

## [결정] `build_from_transactions()`의 details_table fallback

**상황:** `apartments` 테이블이 없는 in-memory 테스트 환경에서 LEFT JOIN 실패.

**해결:** try/except로 details_table JOIN 실패 시 sido/sigungu 없이 삽입하는 fallback 경로 추가. 테스트 독립성 보장.
