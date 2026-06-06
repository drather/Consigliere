# 스펙: 스케줄 07:00 변경 + 워크플로우 정리 + Slack 포맷 개선

**날짜:** 2026-06-06  
**상태:** 승인됨

---

## 1. 배경 및 목적

Daily Report 발송 시간을 출근길(07:00 KST)로 변경하고, 사용하지 않는 워크플로우 파일들을 정리한다.  
또한 Slack 메시지에 날짜 헤더·시장 신호·뉴스 요약을 추가하여 모바일에서 컨텍스트 없이도 읽을 수 있게 한다.

---

## 2. Part 1 — 스케줄 변경 + 워크플로우 파일 정리

### 2-A. cron 시간 변경

| 파일 | 변경 |
|---|---|
| `workflows/real_estate/daily_report_schedule.json` | `"0 8 * * *"` → `"0 7 * * *"`, 노드명 "Daily Schedule (07:00)" |

WR-003(06:30 수집), WR-004(06:00 수집) 이후 07:00 리포트 실행 순서 문제 없음.

### 2-B. 삭제할 워크플로우 파일

| 파일 | 이유 |
|---|---|
| `workflows/career/career_daily_report.json` | 개발 예정, 현재 불필요 (active: false) |
| `workflows/career/career_weekly_report.json` | 동일 |
| `workflows/career/career_monthly_report.json` | 동일 |
| `workflows/slack_router.json` | 미작동, 정리 |
| `workflows/real_estate/insight_report_workflow.json` | Daily Report로 통합됨 (active: false) |

삭제 후 `workflows/career/` 디렉토리 자체도 제거.

### 2-C. deploy_workflows.py 정리

`wf_to_deactivate` 목록에서 이미 파일이 삭제된 워크플로우 이름 제거:

```python
wf_to_deactivate = [
    "[Consigliere] 부동산 실거래가 모니터링 (Slack 알림)",  # WR-005만 유지
]
```

`"[Consigliere] 부동산 종합 인사이트 리포트"` (WR-006) 항목 제거 — 파일 삭제로 불필요.

### 2-D. workflows_registry.md 정리

- `WR-001` (Example Daily Sync) 행 삭제
- `WR-NEW` 스케줄 `08:00 KST` → `07:00 KST` 수정, 이름 `Daily Report (07:00 KST)`로 수정

---

## 3. Part 2 — Slack 포맷 개선

### 3-1. 최종 메시지 구조 (모바일 최적화)

```
📊 *데일리 부동산 브리핑 — 2026-06-06*
주목 단지 3개 | 분석 기간 3일

💡 *시장 신호*
- 강남권 거래량 회복세 지속
- 금리 동결 영향으로 관망세

📰 *뉴스 요약*
• 서울시 재건축 규제 완화 검토
• 전세 시장 안정세 지속

━━━━━━━━━━━━━━━

*1. 아파트명* — 종합 85점
💰 12.5억 ▲ 3.2% ▁▂▅▇█
🚌 32분 | 🚗 18분
🔍 판단 텍스트
• 핵심포인트1
• 핵심포인트2

━━━━━━━━━━━━━━━
...
```

### 3-2. report_formatter.py 변경

**`build_slack()` 시그니처 변경:**

```python
# 변경 전
def build_slack(candidates: List[Dict]) -> str:

# 변경 후
def build_slack(
    candidates: List[Dict],
    date_str: str = "",
    market_summary: str = "",
    news_lines: List[str] = [],
) -> str:
```

**헤더 생성 로직:**
- `date_str` 있으면 첫 줄에 `📊 *데일리 부동산 브리핑 — {date_str}*` 추가
- `len(candidates)` 를 `주목 단지 N개` 로 표시
- `market_summary` 있으면 `💡 *시장 신호*` 섹션 추가 (줄별 `-` 포맷)
- `news_lines` 있으면 `📰 *뉴스 요약*` 섹션 추가 (줄별 `•` 포맷)
- 단지 구분자: 기존 `\n\n---\n\n` → `\n\n━━━━━━━━━━━━━━━\n\n`

### 3-3. daily_report_orchestrator.py 변경

**뉴스 요약 추출 (새 private 메서드):**
```python
def _load_news_lines(self, date_str: str, max_lines: int = 5) -> List[str]:
    """당일 뉴스 리포트에서 핵심 줄(bullet) 최대 N개 추출."""
    path = f"data/real_estate/news/{date_str}_News.md"
    if not os.path.exists(path):
        return []
    with open(path, encoding="utf-8") as f:
        content = f.read()
    lines = [
        ln.lstrip("-•* ").strip()
        for ln in content.splitlines()
        if ln.strip().startswith(("-", "•", "*")) and len(ln.strip()) > 10
    ]
    return lines[:max_lines]
```

**`build_slack()` 호출 변경 (line 268 근방):**
```python
# 변경 전
slack_text = build_slack(candidates)

# 변경 후
news_lines = self._load_news_lines(date_str)
slack_text = build_slack(
    candidates=candidates,
    date_str=date_str,
    market_summary=market_summary,
    news_lines=news_lines,
)
```

---

## 4. 변경 파일 목록

| 파일 | 작업 |
|---|---|
| `workflows/real_estate/daily_report_schedule.json` | cron + 노드명 변경 |
| `workflows/career/career_daily_report.json` | **삭제** |
| `workflows/career/career_weekly_report.json` | **삭제** |
| `workflows/career/career_monthly_report.json` | **삭제** |
| `workflows/slack_router.json` | **삭제** |
| `workflows/real_estate/insight_report_workflow.json` | **삭제** |
| `scripts/deploy_workflows.py` | wf_to_deactivate 목록 정리 |
| `docs/workflows_registry.md` | WR-001 삭제, WR-NEW 시간 수정 |
| `src/modules/real_estate/daily_report/report_formatter.py` | `build_slack()` 헤더 추가, 구분자 변경 |
| `src/modules/real_estate/daily_report/daily_report_orchestrator.py` | `_load_news_lines()` 추가, `build_slack()` 호출 수정 |

---

## 5. 범위 외 (Out of Scope)

- 뉴스 요약 품질 개선 (LLM 기반 요약 → 향후)
- 커리어 워크플로우 실제 개발
- 다른 Slack 채널로 메시지 라우팅

---

## 6. 성공 기준

1. Daily Report Slack이 07:00 KST에 1회 수신됨
2. 메시지 상단에 날짜·시장신호·뉴스요약 헤더 포함
3. 삭제된 워크플로우 파일 5개가 repository에서 제거됨
4. 기존 테스트 863개 모두 통과
