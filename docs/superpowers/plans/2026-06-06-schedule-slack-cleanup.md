# 스케줄 07:00 변경 + 워크플로우 정리 + Slack 포맷 개선 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Daily Report Slack 발송 시간을 07:00 KST로 변경하고, 사용하지 않는 워크플로우 5개를 삭제하며, Slack 메시지에 날짜·시장신호·뉴스 요약 헤더를 추가한다.

**Architecture:** 3 독립 태스크 — (1) 워크플로우 JSON·레지스트리 파일 수정/삭제 (코드 무관), (2) `report_formatter.py`의 `build_slack()` 파라미터 확장 + 헤더 생성 (TDD), (3) `daily_report_orchestrator.py`에 `_load_news_lines()` 추가 및 호출 갱신 (TDD).

**Tech Stack:** Python 3.12, n8n JSON workflow, pytest, unittest.mock

---

## File Map

| 파일 | 작업 |
|---|---|
| `workflows/real_estate/daily_report_schedule.json` | cron `0 8` → `0 7`, 노드명/워크플로우명/연결키 변경 |
| `workflows/career/career_daily_report.json` | 삭제 |
| `workflows/career/career_weekly_report.json` | 삭제 |
| `workflows/career/career_monthly_report.json` | 삭제 |
| `workflows/slack_router.json` | 삭제 |
| `workflows/real_estate/insight_report_workflow.json` | 삭제 |
| `scripts/deploy_workflows.py` | `wf_to_deactivate`에서 WR-006 이름 제거 |
| `docs/workflows_registry.md` | WR-001 행 삭제, WR-NEW 시간·이름 수정 |
| `src/modules/real_estate/daily_report/report_formatter.py` | `build_slack()` 시그니처 + 헤더 구현 |
| `tests/modules/real_estate/daily_report/test_report_formatter.py` | `build_slack()` 헤더 테스트 추가 |
| `src/modules/real_estate/daily_report/daily_report_orchestrator.py` | `_load_news_lines()` 추가, `build_slack()` 호출 갱신 |
| `tests/modules/real_estate/daily_report/test_daily_report_orchestrator.py` | `_load_news_lines()` 테스트 추가 |

---

## Task 1: 워크플로우 파일 정리 + 스케줄 07:00 변경

**Files:**
- Modify: `workflows/real_estate/daily_report_schedule.json`
- Modify: `scripts/deploy_workflows.py`
- Modify: `docs/workflows_registry.md`
- Delete: `workflows/career/career_daily_report.json`
- Delete: `workflows/career/career_weekly_report.json`
- Delete: `workflows/career/career_monthly_report.json`
- Delete: `workflows/slack_router.json`
- Delete: `workflows/real_estate/insight_report_workflow.json`

> 이 태스크는 순수 파일 변경이므로 TDD 사이클 없음. 기존 테스트 전체 통과 여부로 검증.

- [ ] **Step 1: daily_report_schedule.json — cron + 이름 변경**

  다음 4곳을 정확히 변경한다 (JSON 구조 그대로 유지):

  ```json
  // 변경 전 → 변경 후

  // 워크플로우 이름 (line 2)
  "name": "[Consigliere] Daily Report (08:00 KST)"
  →
  "name": "[Consigliere] Daily Report (07:00 KST)"

  // cron expression (line 10)
  "expression": "0 8 * * *"
  →
  "expression": "0 7 * * *"

  // 노드 이름 (line 19)
  "name": "Daily Schedule (08:00)"
  →
  "name": "Daily Schedule (07:00)"

  // connections 딕셔너리 키 (line 88)
  "Daily Schedule (08:00)": {
  →
  "Daily Schedule (07:00)": {
  ```

- [ ] **Step 2: 워크플로우 파일 5개 삭제**

  ```bash
  rm workflows/career/career_daily_report.json \
     workflows/career/career_weekly_report.json \
     workflows/career/career_monthly_report.json \
     workflows/slack_router.json \
     workflows/real_estate/insight_report_workflow.json
  rmdir workflows/career
  ```

  Expected: 명령 오류 없음. `ls workflows/career/` → `No such file or directory`

- [ ] **Step 3: deploy_workflows.py — wf_to_deactivate 정리**

  `scripts/deploy_workflows.py` 의 `wf_to_deactivate` 리스트에서 `"[Consigliere] 부동산 종합 인사이트 리포트"` 줄을 제거한다. 파일 삭제로 n8n에 없을 수 있으나 이름 보존은 불필요.

  변경 후:
  ```python
  wf_to_deactivate = [
      "[Consigliere] 부동산 실거래가 모니터링 (Slack 알림)",
  ]
  ```

- [ ] **Step 4: workflows_registry.md 정리**

  a) `WR-001` 행 전체 삭제 (Example Daily Sync, Active 섹션):
  ```
  | `WR-001`   | System      | (Example) Daily Sync            | 08:00 KST          | Test entry for registry initialization.                        | Active | -                  |
  ```

  b) `WR-NEW` 행 수정:
  ```
  // 변경 전
  | `WR-NEW`   | System      | Daily Report (08:00 KST)        | 08:00 KST          | 데일리 리포트 생성 + Slack 1회 발송 (모든 인사이트 통합)       | Active | -                  |

  // 변경 후
  | `WR-NEW`   | System      | Daily Report (07:00 KST)        | 07:00 KST          | 데일리 리포트 생성 + Slack 1회 발송 (모든 인사이트 통합)       | Active | -                  |
  ```

- [ ] **Step 5: 기존 테스트 실행**

  ```bash
  arch -arm64 .venv/bin/python3.12 -m pytest tests/ -x -q 2>&1 | tail -5
  ```

  Expected: `858 passed` (또는 그 이상), 새 실패 없음.

- [ ] **Step 6: Commit**

  ```bash
  git add workflows/real_estate/daily_report_schedule.json \
          scripts/deploy_workflows.py \
          docs/workflows_registry.md
  git rm workflows/career/career_daily_report.json \
         workflows/career/career_weekly_report.json \
         workflows/career/career_monthly_report.json \
         workflows/slack_router.json \
         workflows/real_estate/insight_report_workflow.json
  git commit -m "chore(workflows): 07:00 KST 변경 + 불필요 워크플로우 5개 삭제"
  ```

---

## Task 2: report_formatter.py — build_slack() 헤더 확장

**Files:**
- Modify: `src/modules/real_estate/daily_report/report_formatter.py`
- Test: `tests/modules/real_estate/daily_report/test_report_formatter.py`

- [ ] **Step 1: 실패하는 테스트 작성**

  `tests/modules/real_estate/daily_report/test_report_formatter.py` 파일 끝(line 361 다음)에 새 클래스를 추가한다:

  ```python
  class TestBuildSlackHeader:
      """build_slack() 헤더 확장 테스트"""

      def _candidate(self) -> dict:
          return {
              "apt_name": "래미안",
              "composite_score": 0.85,
              "avg_recent_price": 1_250_000_000,
              "price_change_pct": 3.2,
              "_recent_tx_points": [
                  {"price_eok": 11.0, "deal_date": "2026-05-01"},
                  {"price_eok": 12.5, "deal_date": "2026-05-15"},
              ],
              "commute_transit_minutes": 32,
              "commute_car_minutes": 18,
              "commute_walk_minutes": None,
              "_commute_route_summary": "",
              "_verdict": "매수 적기",
              "_key_points": ["역세권"],
              "_location_score": None,
          }

      def test_date_str_appears_in_header(self):
          from modules.real_estate.daily_report.report_formatter import build_slack
          result = build_slack([self._candidate()], date_str="2026-06-06")
          assert "2026-06-06" in result
          assert "📊" in result

      def test_candidate_count_in_header(self):
          from modules.real_estate.daily_report.report_formatter import build_slack
          result = build_slack([self._candidate(), self._candidate()], date_str="2026-06-06")
          assert "2개" in result

      def test_market_summary_section(self):
          from modules.real_estate.daily_report.report_formatter import build_slack
          result = build_slack(
              [self._candidate()],
              date_str="2026-06-06",
              market_summary="- 금리 동결\n- 거래량 회복",
          )
          assert "💡" in result
          assert "금리 동결" in result

      def test_news_lines_section(self):
          from modules.real_estate.daily_report.report_formatter import build_slack
          result = build_slack(
              [self._candidate()],
              date_str="2026-06-06",
              news_lines=["재건축 규제 완화", "전세 안정세"],
          )
          assert "📰" in result
          assert "재건축 규제 완화" in result
          assert "•" in result

      def test_separator_changed_to_unicode_line(self):
          from modules.real_estate.daily_report.report_formatter import build_slack
          c2 = {**self._candidate(), "apt_name": "힐스테이트"}
          result = build_slack([self._candidate(), c2])
          assert "━" in result

      def test_no_header_when_date_str_empty(self):
          from modules.real_estate.daily_report.report_formatter import build_slack
          result = build_slack([self._candidate()])
          assert "📊" not in result
          assert "래미안" in result

      def test_backward_compat_no_positional_kwargs(self):
          """기존 build_slack([c]) 호출 방식이 그대로 동작해야 한다."""
          from modules.real_estate.daily_report.report_formatter import build_slack
          result = build_slack([self._candidate()])
          assert "래미안" in result
          assert "<svg" not in result
  ```

- [ ] **Step 2: 실패 확인**

  ```bash
  arch -arm64 .venv/bin/python3.12 -m pytest tests/modules/real_estate/daily_report/test_report_formatter.py::TestBuildSlackHeader -v 2>&1 | tail -20
  ```

  Expected: `FAILED` — `test_date_str_appears_in_header` 등 새 테스트들이 실패해야 함.  
  (기존 `TestBuildSlack` 테스트들은 여전히 PASS)

- [ ] **Step 3: build_slack() 구현**

  `src/modules/real_estate/daily_report/report_formatter.py` 의 `build_slack` 함수(line 524–526)를 아래로 교체한다:

  ```python
  def build_slack(
      candidates: List[Dict],
      date_str: str = "",
      market_summary: str = "",
      news_lines: Optional[List[str]] = None,
  ) -> str:
      parts: List[str] = []

      if date_str:
          header: List[str] = [
              f"📊 *데일리 부동산 브리핑 — {date_str}*",
              f"주목 단지 {len(candidates)}개",
          ]
          if market_summary:
              header.append("")
              header.append("💡 *시장 신호*")
              for line in market_summary.splitlines():
                  stripped = line.strip()
                  if stripped:
                      header.append(stripped if stripped.startswith("-") else f"- {stripped}")
          if news_lines:
              header.append("")
              header.append("📰 *뉴스 요약*")
              for ln in news_lines:
                  header.append(f"• {ln}")
          parts.append("\n".join(header))

      parts.extend(_slack_candidate_block(c) for c in candidates)
      return "\n\n━━━━━━━━━━━━━━━\n\n".join(parts)
  ```

  `Optional`은 이미 `from typing import Dict, List, Optional` 로 임포트되어 있으므로 추가 불필요.

- [ ] **Step 4: 전체 테스트 실행**

  ```bash
  arch -arm64 .venv/bin/python3.12 -m pytest tests/modules/real_estate/daily_report/test_report_formatter.py -v 2>&1 | tail -20
  ```

  Expected: 모든 테스트 PASS (기존 6개 + 신규 7개).

- [ ] **Step 5: 프로젝트 전체 테스트 확인**

  ```bash
  arch -arm64 .venv/bin/python3.12 -m pytest tests/ -x -q 2>&1 | tail -5
  ```

  Expected: 기존 대비 새 실패 없음.

- [ ] **Step 6: Commit**

  ```bash
  git add src/modules/real_estate/daily_report/report_formatter.py \
          tests/modules/real_estate/daily_report/test_report_formatter.py
  git commit -m "feat(formatter): build_slack() 헤더 확장 — 날짜·시장신호·뉴스 요약"
  ```

---

## Task 3: daily_report_orchestrator.py — _load_news_lines + build_slack 호출 갱신

**Files:**
- Modify: `src/modules/real_estate/daily_report/daily_report_orchestrator.py`
- Test: `tests/modules/real_estate/daily_report/test_daily_report_orchestrator.py`

- [ ] **Step 1: 실패하는 테스트 작성**

  `tests/modules/real_estate/daily_report/test_daily_report_orchestrator.py` 파일 끝에 새 클래스를 추가한다:

  ```python
  class TestLoadNewsLines:
      """_load_news_lines() 유닛 테스트"""

      def _make_orch(self):
          orch = DailyReportOrchestrator.__new__(DailyReportOrchestrator)
          return orch

      def test_returns_bullets_from_file(self, tmp_path):
          content = "# 뉴스 요약\n\n- 재건축 규제 완화 검토\n- 전세 시장 안정세 지속\n"
          orch = self._make_orch()
          with patch(
              "modules.real_estate.daily_report.daily_report_orchestrator.os.path.exists",
              return_value=True,
          ), patch(
              "builtins.open",
              mock_open(read_data=content),
          ):
              result = orch._load_news_lines("2026-06-06")
          assert result == ["재건축 규제 완화 검토", "전세 시장 안정세 지속"]

      def test_returns_empty_when_file_missing(self):
          orch = self._make_orch()
          with patch(
              "modules.real_estate.daily_report.daily_report_orchestrator.os.path.exists",
              return_value=False,
          ):
              result = orch._load_news_lines("2026-06-06")
          assert result == []

      def test_strips_bullet_prefix(self):
          content = "• 항목A는 충분히 긴 문장\n* 항목B도 충분히 긴 문장\n- 항목C도 충분히 긴 문장\n"
          orch = self._make_orch()
          with patch(
              "modules.real_estate.daily_report.daily_report_orchestrator.os.path.exists",
              return_value=True,
          ), patch(
              "builtins.open",
              mock_open(read_data=content),
          ):
              result = orch._load_news_lines("2026-06-06")
          assert any("항목A" in r for r in result)
          assert any("항목B" in r for r in result)
          assert any("항목C" in r for r in result)

      def test_max_lines_respected(self):
          content = "\n".join(f"- 항목{i}번 충분히 긴 텍스트" for i in range(10))
          orch = self._make_orch()
          with patch(
              "modules.real_estate.daily_report.daily_report_orchestrator.os.path.exists",
              return_value=True,
          ), patch(
              "builtins.open",
              mock_open(read_data=content),
          ):
              result = orch._load_news_lines("2026-06-06", max_lines=3)
          assert len(result) == 3
  ```

  파일 상단 `from unittest.mock import MagicMock, patch` 줄을 아래로 변경한다 (`mock_open` 추가):
  ```python
  from unittest.mock import MagicMock, mock_open, patch
  ```
  
  그리고 테스트 코드 내의 `unittest.mock.patch` → `patch`, `unittest.mock.mock_open` → `mock_open` 으로 수정한다.

- [ ] **Step 2: 실패 확인**

  ```bash
  arch -arm64 .venv/bin/python3.12 -m pytest tests/modules/real_estate/daily_report/test_daily_report_orchestrator.py::TestLoadNewsLines -v 2>&1 | tail -15
  ```

  Expected: `FAILED` (AttributeError: 'DailyReportOrchestrator' object has no attribute '_load_news_lines')

- [ ] **Step 3: _load_news_lines() 구현**

  `src/modules/real_estate/daily_report/daily_report_orchestrator.py` 에서 `_enrich_with_commute_quota` 메서드 바로 앞(line 292 근방)에 새 메서드를 추가한다:

  ```python
  def _load_news_lines(self, date_str: str, max_lines: int = 5) -> List[str]:
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

  `os`는 이미 line 5에서 `import os`로 임포트되어 있으므로 추가 불필요.

- [ ] **Step 4: build_slack() 호출 갱신**

  `src/modules/real_estate/daily_report/daily_report_orchestrator.py` 의 line 268:

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

- [ ] **Step 5: 테스트 실행**

  ```bash
  arch -arm64 .venv/bin/python3.12 -m pytest tests/modules/real_estate/daily_report/test_daily_report_orchestrator.py::TestLoadNewsLines -v 2>&1 | tail -15
  ```

  Expected: `4 passed`

- [ ] **Step 6: 전체 테스트 실행**

  ```bash
  arch -arm64 .venv/bin/python3.12 -m pytest tests/ -x -q 2>&1 | tail -5
  ```

  Expected: 기존 대비 새 실패 없음.

- [ ] **Step 7: Commit**

  ```bash
  git add src/modules/real_estate/daily_report/daily_report_orchestrator.py \
          tests/modules/real_estate/daily_report/test_daily_report_orchestrator.py
  git commit -m "feat(orchestrator): _load_news_lines() 추가 + build_slack 헤더 인자 전달"
  ```
