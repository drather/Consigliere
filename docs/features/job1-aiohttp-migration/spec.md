# Spec: Job1 aiohttp 비동기 전환 + 데이터 라이프사이클 관리

## 배경

`fetch_transactions` (Job1)이 `ThreadPoolExecutor`를 사용해 MOLIT API 병렬 호출 중 두 가지 문제 반복 발생:

1. **OOM** — max_workers=3 + ChromaDB onnxruntime 임베딩 병렬 실행 → exitCode=137
2. **429 Rate Limit** — 국토부 API 동시 3개 이상 호출 시 차단

추가로 월 전체 데이터를 저장 중이나 실제로는 최근 3일치만 필요하고, ChromaDB에 오래된 데이터가 누적되고 있음.

## 목표

- `aiohttp + asyncio.Semaphore(2)` 전환으로 OOM·429 근본 해결
- 수집 데이터를 최근 3일치로 제한
- 1년 이상 된 ChromaDB 데이터 자동 삭제

## API 스펙

- URL: `http://apis.data.go.kr/1613000/RTMSDataSvcAptTradeDev/getRTMSDataSvcAptTradeDev`
- 파라미터: `serviceKey`, `pageNo=1`, `numOfRows=100`, `LAWD_CD`(5자리 구 코드), `DEAL_YMD`(YYYYMM)
- 응답: XML, `<resultCode>0/00/000</resultCode>` 성공
- 날짜 범위 파라미터 없음 → 월 전체 반환 → Python 레벨 3일 필터
- 70개 구 × 1회 호출 = 70번 API 호출, `numOfRows=100` 으로 충분 (3일치 100건 초과 불가)

## 수정 범위

| 파일 | 변경 내용 |
|---|---|
| `requirements.txt` | `aiohttp>=3.9.0` 추가 |
| `monitor/service.py` | `_parse_item_to_transaction` 모듈 레벨 함수로 추출 |
| `models.py` | `to_chroma_format()`에 `deal_date_int` 필드 추가 |
| `repository.py` | `delete_old_transactions(cutoff_date)` 메서드 추가 |
| `service.py` | `fetch_transactions` async 재구현 + async 헬퍼 3개 추가 |

## 완료 조건

- 70개 구 완주, OOM(docker events) 없음, 429 에러 없음
- 로그에 `[Job1] 비동기 수집: 71개 지구` 출력
- 각 구 fetched 건수 ≤ 100 (3일치)
- 전체 완료 3~5분 이내
- `deleted_old_count` 키가 응답에 포함됨
