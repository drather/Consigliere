# 개별 아파트 심층 분석 기능 설계

**Date:** 2026-05-30
**Feature:** `feature/apt-analysis`
**Status:** 설계 확정

---

## 배경

현재 Job Report(`DailyReportOrchestrator`)는 당일 실거래가 수신 내역 기반으로 여러 단지를 top-k 선별해 리포트를 생성한다. 특정 단지를 눈여겨보고 있을 때 축적된 전체 데이터(실거래가 히스토리, 전세가율, 공급리스크, 입지점수, 거시경제, 출퇴근)를 통합 심층 분석하는 기능이 없다.

---

## 목표

단지 코드를 입력받아 DB에 축적된 모든 데이터를 통합하고, 로컬 LLM CLI(Claude Code / Gemini CLI)로 자연어 종합 인사이트를 생성한다. 결과는 DB에 저장되어 이후에도 조회 가능하며, Slack 알림과 대시보드 Tab1에서 확인할 수 있다.

---

## 아키텍처

```
POST /jobs/apt/analyze  {complex_code, send_slack}
  │
  ▼
AptAnalysisOrchestrator.analyze(complex_code)
  ├── AptMasterRepository      → 단지 기본 정보 (이름, 위치, 좌표)
  ├── TransactionRepository    → 실거래가 히스토리 (전체)
  ├── JeonseRepository         → 전세 데이터 → 전세가율 계산
  ├── SupplyRepository         → 주변 공급 일정 (반경 3km)
  ├── LocationRepository       → 입지점수 (residential / investment)
  ├── MacroService             → 거시경제 최신 지표
  ├── CommuteRepository        → 출퇴근 캐시
  └── ClaudeCodeClient / GeminiCliClient
        └── subprocess 호출 → 자연어 종합 인사이트
  │
  ▼
AptAnalysisReport
  ├── 구조화 데이터 (각 섹션별 수치)
  ├── llm_insight (자연어 분석)
  ├── slack_text
  └── markdown_text
  │
  ├── AptAnalysisRepository.save()  → real_estate.db 저장
  ├── Slack 전송 (send_slack=True)
  └── API 응답 → 대시보드 렌더링
```

---

## 파일 변경 목록

| 파일 | 변경 |
|------|------|
| `src/core/llm.py` | `ClaudeCodeClient`, `GeminiCliClient` 추가, `LLMFactory` 확장 |
| `src/modules/real_estate/apt_analysis/__init__.py` | 신규 패키지 |
| `src/modules/real_estate/apt_analysis/models.py` | `AptAnalysisReport` dataclass |
| `src/modules/real_estate/apt_analysis/orchestrator.py` | `AptAnalysisOrchestrator` |
| `src/modules/real_estate/apt_analysis/formatter.py` | Slack/markdown 포맷터 |
| `src/modules/real_estate/apt_analysis/repository.py` | `AptAnalysisRepository` (SQLite) |
| `src/api/routers/real_estate.py` | `POST /jobs/apt/analyze`, `GET /dashboard/apt/analysis/{complex_code}`, `GET /dashboard/apt/analysis/{complex_code}/latest` 추가 |
| `src/dashboard/views/real_estate.py` | Tab1 단지 상세 패널에 "🔬 심층 분석" + "📋 이전 분석 보기" 버튼 추가 |
| `docker-compose.yml` | claude/gemini 바이너리 + credentials 볼륨 마운트 추가 |

백엔드 기존 파일(`daily_report_orchestrator.py` 등) 변경 없음.

---

## LLM CLI 클라이언트

### ClaudeCodeClient

```python
class ClaudeCodeClient(BaseLLMClient):
    def generate(self, prompt: str) -> str:
        result = subprocess.run(
            ["claude", "--print", prompt],
            capture_output=True, text=True, timeout=120
        )
        return result.stdout.strip()

    def generate_json(self, prompt: str, ...) -> Dict[str, Any]:
        raw = self.generate(prompt)
        # JSON 파싱 시도 → 실패 시 {"insight": raw} fallback
```

### GeminiCliClient

```python
class GeminiCliClient(BaseLLMClient):
    def generate(self, prompt: str) -> str:
        result = subprocess.run(
            ["gemini", prompt],
            capture_output=True, text=True, timeout=120
        )
        return result.stdout.strip()
```

### LLMFactory 확장

`.env`의 `LLM_PROVIDER` 값으로 선택:
- `claude-code` → `ClaudeCodeClient`
- `gemini-cli` → `GeminiCliClient`
- `claude` → 기존 `ClaudeClient` (API)
- `gemini` → 기존 `GeminiClient` (API, 기본값)

### docker-compose.yml 마운트

```yaml
consigliere_api:
  volumes:
    - ~/.claude:/root/.claude:ro
    - /usr/local/bin/claude:/usr/local/bin/claude:ro
    # Gemini CLI 사용 시:
    # - ~/.config/gemini:/root/.config/gemini:ro
    # - /usr/local/bin/gemini:/usr/local/bin/gemini:ro
```

---

## 데이터 모델

### AptAnalysisReport

```python
@dataclass
class AptAnalysisReport:
    complex_code: str
    apt_name: str
    generated_at: str              # ISO8601

    # 수집 데이터
    price_history: List[dict]      # 실거래가 히스토리 (날짜, 가격, 면적)
    jeonse_ratio: Optional[float]  # 전세가율 (%) = 최근 전세가 / 최근 매매가 평균
                                   # 전세가: JeonseRepository, 매매가: TransactionRepository
    supply_risk_summary: str       # SupplyRiskAnalyzer 기존 패턴 재사용 — 반경 3km 공급 건수 + 리스크 레벨
    location_score: Optional[dict] # residential_total, investment_total, results
    commute_summary: Optional[dict]# mode별 소요시간 (persona.yaml의 workplace 좌표 기준)
    macro_snapshot: dict           # 기준금리, 주담대금리 등 최신값

    # LLM 출력
    llm_insight: str               # 자연어 종합 분석

    # 포맷
    slack_text: str
    markdown_text: str
```

### apt_analysis_reports 테이블 (real_estate.db)

```sql
CREATE TABLE IF NOT EXISTS apt_analysis_reports (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    complex_code TEXT NOT NULL,
    apt_name     TEXT NOT NULL,
    generated_at TEXT NOT NULL,
    report_json  TEXT NOT NULL,   -- AptAnalysisReport 전체 JSON
    llm_insight  TEXT NOT NULL,
    slack_text   TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_apt_analysis_complex
    ON apt_analysis_reports(complex_code, generated_at DESC);
```

---

## API 엔드포인트

### POST /jobs/apt/analyze

```
Body: {
  "complex_code": "11110-100",  // 필수
  "send_slack": true             // 선택, 기본 true
}

Response 200:
{
  "status": "success",
  "report": { ...AptAnalysisReport fields... }
}

Error 404: 단지 코드 없음
Error 500: 분석 실패 (LLM CLI 오류 등)
```

### GET /dashboard/apt/analysis/{complex_code}

분석 이력 목록 반환 (최신순, 기본 limit=10).

### GET /dashboard/apt/analysis/{complex_code}/latest

가장 최근 분석 결과 1건 반환. 없으면 404.

---

## 대시보드 Tab1 통합

`_render_apt_detail_panel(complex_code)` 하단에 두 버튼 추가:

```
[🔬 심층 분석]   [📋 이전 분석 보기]
```

- **이전 분석 보기**: `GET /latest` 호출 → 있으면 결과 expander 표시
- **심층 분석**: `POST /jobs/apt/analyze` 호출 → spinner → 완료 후 결과 expander 표시
  - `llm_insight` 텍스트, 실거래가 차트, 전세가율, 입지점수, 공급리스크, 출퇴근 요약 순으로 렌더링

---

## 에러 처리

| 상황 | 처리 |
|------|------|
| CLI 바이너리 없음 / subprocess 실패 | `llm_insight = "분석 실패: CLI 미설치"`, 나머지 구조 데이터는 정상 반환 및 저장 |
| 단지 코드 없음 | HTTP 404 |
| 특정 레포지토리 데이터 없음 | 해당 섹션 `None` / 빈 리스트, 나머지 데이터로 분석 계속 |
| LLM timeout (120s) | `llm_insight = "분석 시간 초과"` |

---

## 테스트 전략

1. **ClaudeCodeClient / GeminiCliClient**: `subprocess.run` mock → `generate()` 반환값 검증
2. **AptAnalysisOrchestrator**: 각 Repository mock → `analyze()` 호출 시 올바른 `AptAnalysisReport` 생성 검증
3. **AptAnalysisRepository**: 인메모리 SQLite → `save()` / `get_latest()` / `get_history()` 검증
4. **API 엔드포인트**: FastAPI TestClient → 404/200 응답 검증
5. **E2E 면제**: 대시보드 버튼 변경은 수동 확인

---

## SOP 체크리스트

- [ ] Phase 0: `feature/apt-analysis` 브랜치 생성
- [ ] Phase 1: `docs/features/apt-analysis/spec.md` 작성
- [ ] Phase 2: TDD — ClaudeCodeClient/GeminiCliClient → Repository → Orchestrator → API
- [ ] Phase 2.5: SOLID Review
- [ ] Phase 3: `result.md` + `history.md` 업데이트
- [ ] Phase 4: 전체 테스트 PASS, 머지
