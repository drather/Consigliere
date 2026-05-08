# 학군 분석 기능 설계 문서

**Date:** 2026-05-08  
**Feature:** 학교알리미 기반 학군 분석  
**Module:** `src/modules/real_estate/school/`

---

## 1. 목표

단지 인근 초/중/고교 데이터를 학교알리미 OpenAPI로 수집하여 학군 점수를 산출하고, 리포트 및 대시보드에 통합한다.

---

## 2. 패키지 구조

```
src/modules/real_estate/school/
├── __init__.py
├── models.py                  # SchoolInfo, SchoolStudentRecord, SchoolTeacherRecord, SchoolScore
├── school_info_client.py      # 학교알리미 API 클라이언트
├── school_repository.py       # SQLite 저장소 (real_estate.db 통합)
└── school_service.py          # 수집 오케스트레이션 + 학군 점수 계산
```

**통합 지점:**
- `src/modules/real_estate/scoring.py` — `school` 가중치 항목에 SchoolScore 연결
- `src/api/routes/jobs.py` — `POST /jobs/school/collect`
- `src/api/routes/dashboard.py` — `GET /dashboard/real-estate/school/{complex_code}`
- `src/dashboard/main.py` — Tab1 단지 상세 패널에 학군 섹션 추가

---

## 3. 데이터 모델

### SchoolInfo (학교기본정보 — apiType=0)
| 필드 | 타입 | 설명 |
|------|------|------|
| school_code | str | 고유 식별자 (SCHUL_CODE) |
| school_name | str | 학교명 |
| school_kind | str | 02=초등 / 03=중등 / 04=고등 |
| sido_code | str | 시도코드 |
| sgg_code | str | 시군구코드 |
| address | str | 주소 |
| lat | float? | 위도 (LTTUD) |
| lng | float? | 경도 (LGTUD) |
| establishment_type | str | 공립/사립 |
| founding_year | int? | 설립연도 |
| collected_at | str | ISO8601 |

### SchoolStudentRecord (학년별·학급별 학생수 + 성별 학생수)
| 필드 | 타입 | 설명 |
|------|------|------|
| school_code | str | FK → school_info |
| year | int | 수집 연도 |
| grade | str | 학년 |
| class_count | int | 학급 수 |
| student_count | int | 전체 학생 수 |
| students_per_class | float | student_count / class_count |
| male_count | int | 남학생 수 |
| female_count | int | 여학생 수 |
| collected_at | str | |

### SchoolTeacherRecord (직위별 교원 현황)
| 필드 | 타입 | 설명 |
|------|------|------|
| school_code | str | FK → school_info |
| year | int | 수집 연도 |
| total_teachers | int | 교원 수 합산 |
| students_per_teacher | float | 전체학생수 / 교원수 |
| collected_at | str | |

### SchoolScore (학군 점수)
| 필드 | 타입 | 설명 |
|------|------|------|
| complex_code | str | FK → apt_master |
| school_kind | str | elementary / middle / high / total |
| nearby_school_count | int | 반경 내 학교 수 |
| avg_students_per_class | float | 평균 학급당 학생수 |
| avg_students_per_teacher | float | 평균 교사 1인당 학생수 |
| score | int | 0~100 |
| collected_at | str | |

---

## 4. API 클라이언트

**Base URL:** `https://www.schoolinfo.go.kr/openApi.do`  
**인증:** `apiKey=os.getenv("SCHOOLINFO_API_KEY")` (환경변수, 코드 노출 금지)

| 메서드 | apiType | 데이터 |
|--------|---------|--------|
| `get_school_list()` | 0 | 학교기본정보 (위치·설립유형·좌표) |
| `get_student_counts()` | 학년별·학급별 학생수 | 학급당 학생수 |
| `get_gender_counts()` | 성별 학생수 | 남녀 학생수 |
| `get_teacher_counts()` | 직위별 교원 현황 | 교원 수 |

**schulKndCode:** `"02"` 초등 / `"03"` 중등 / `"04"` 고등 — 루프로 전체 수집  
**주의:** 정확한 apiType 값은 구현 초기 smoke test로 검증 필요 (BOK Client 선례 동일)

---

## 5. Repository

- `real_estate.db`에 통합 (별도 DB 없음)
- 테이블: `school_info`, `school_student_records`, `school_teacher_records`, `school_scores`
- 핵심 메서드:
  - `upsert_school()`, `upsert_student_record()`, `upsert_teacher_record()`, `upsert_school_score()`
  - `get_schools_by_sgg(sgg_code, school_kind)` — 행정구역 기반 목록
  - `get_schools_near(lat, lng, radius_km)` — Haversine 반경 필터링
  - `get_score(complex_code)` — 단지 학군 점수 조회

---

## 6. Service

### `collect_by_district(sido_code, sgg_code)`
초/중/고 × 4개 apiType 순차 수집 → 저장

### `calculate_score(complex_code, lat, lng, sgg_code, radius_km=1.0)`
1. `sgg_code`로 학교 목록 조회 (행정구역 수집)
2. 반경 `radius_km` 필터링 (C 방식): lat/lng 미존재 또는 반경 내 학교 0개이면 sgg_code 전체로 폴백 (A 방식)
3. 점수 계산:
   - 학급당 학생수 달성도 × 70%
   - 근접 학교 수 × 30%
4. `school_scores` 저장

---

## 7. 점수 계산 기준 (config.yaml 외부화)

```yaml
school:
  radius_km: 1.0
  students_per_class_ideal: 20       # 이하 → HIGH (100점)
  students_per_class_warning: 28     # 초과 → LOW (20점)
  nearby_school_high: 3              # 이상 → HIGH (100점)
  nearby_school_mid: 1               # 이상 → MEDIUM (60점)
  score_weight_density: 0.30
  score_weight_class_size: 0.70
```

데이터 미수집 시 → `data_absent_neutral=50` (기존 패턴 동일)

---

## 8. FastAPI 엔드포인트

```
POST /jobs/school/collect
  body: { sido_code: str, sgg_code: str }
  → SchoolService.collect_by_district() 실행

GET /dashboard/real-estate/school/{complex_code}
  → SchoolScore + 근처 학교 목록 반환
```

---

## 9. 대시보드 (Tab1 단지 상세 패널)

`_render_apt_detail_panel()`에 학군 섹션 추가:

```
📚 학군 분석
  초등학교 N개 (반경 1km) | 학급당 평균 XX명
  중학교  N개             | 교사 1인당 XX명
  고등학교 N개             | 학군 점수: XX/100
```

---

## 10. 환경변수

```
SCHOOLINFO_API_KEY=<학교알리미 발급 키>  # .env에만 존재, 코드 노출 금지
```

---

## 11. 테스트 전략 (TDD)

- `tests/modules/real_estate/school/test_school_info_client.py` — API 응답 mock
- `tests/modules/real_estate/school/test_school_repository.py` — SQLite CRUD
- `tests/modules/real_estate/school/test_school_service.py` — 수집 로직, 점수 계산
- `tests/modules/real_estate/school/test_school_scoring.py` — 점수 공식 단위 테스트
