# Result: 아파트 마스터 DB 구축

**완료일:** 2026-04-09

## 구현 요약

### 신규 파일
| 파일 | 역할 |
|------|------|
| `src/modules/real_estate/models.py` | `ApartmentMaster` dataclass 추가 |
| `src/modules/real_estate/apartment_master/client.py` | 공동주택 단지목록 + 기본정보 공공 API 클라이언트 |
| `src/modules/real_estate/apartment_master/repository.py` | SQLite CRUD (geocoder.py 패턴) |
| `src/modules/real_estate/apartment_master/service.py` | 전수 구축(build_initial) + 온디맨드(get_or_fetch) |
| `tests/modules/real_estate/test_apartment_master.py` | TDD 테스트 20개 |

### 수정 파일
| 파일 | 변경 내용 |
|------|---------|
| `service.py` | `RealEstateAgent` 주입, `_enrich_transactions()` 마스터 enrich 추가, `build_apartment_master()` Job 메서드 |
| `config.yaml` | `apartment_master_db_path`, `apartment_master_rate_limit_sec` 추가 |
| `routers/real_estate.py` | `POST /jobs/real-estate/build-apartment-master` 엔드포인트 |
| `.env.example` | `MOLIT_APT_LIST_API_KEY` 추가 |

## 수집 전략

| 단계 | 방식 |
|------|------|
| 초기 전수 구축 | `POST /jobs/real-estate/build-apartment-master` → 71개 지구 순회, API 호출, SQLite 저장 |
| 온디맨드 보완 | `_enrich_transactions()` 호출 시 SQLite miss → API 조회 → 저장 |
| Rate limiting | `apartment_master_rate_limit_sec: 0.3` (config.yaml) |

## 효과

- `household_count` 실제 값으로 채워짐 → `_score_liquidity()` 의미있는 환금성 점수 산출
- `min_household_count` preference rule 실제 동작 (500세대 미만 소규모 단지 필터링)
- `building_count`, `constructor`, `approved_date` 리포트 서술에 활용 가능

## 테스트 결과

- 신규 테스트: 20개 (Repository 6 + Client 5 + Service 9)
- 전체: 241 passed (기존 221 → +20)
- pre-existing 실패 7개: 변화 없음
