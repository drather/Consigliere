"""
E2E 헬스체크 워크플로우 — 부동산 탭 테스트 실행 + 리포트 자동 생성.

사용법:
    arch -arm64 .venv/bin/python3.12 scripts/e2e_health_check.py [--test-path PATH]

동작:
    1. pytest E2E 테스트 실행 (--json-report로 JSON 출력)
    2. JSON 파싱 → 실패 목록 + 스크린샷 경로 추출
    3. docs/e2e_health_report.md 마크다운 리포트 생성

출력:
    - 터미널: 실시간 pytest 출력
    - docs/e2e_health_report.md: 구조화된 헬스체크 리포트
    - docs/e2e_health_report.json: pytest-json-report 원본

향후 확장:
    - Claude API로 실패 분석 + 자동 수정 제안 통합 예정
"""
import argparse
import json
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
PYTHON = PROJECT_ROOT / ".venv" / "bin" / "python3.12"
SCREENSHOT_DIR = PROJECT_ROOT / "tests" / "e2e" / "screenshots"
JSON_REPORT_PATH = PROJECT_ROOT / "docs" / "e2e_health_report.json"
MD_REPORT_PATH = PROJECT_ROOT / "docs" / "e2e_health_report.md"

DEFAULT_TEST_PATH = "tests/e2e/test_e2e_real_estate.py"


# ──────────────────────────────────────────────────────────────────────────────
# 1. pytest 실행
# ──────────────────────────────────────────────────────────────────────────────

def run_pytest(test_path: str, json_report_path: Path) -> int:
    """pytest를 실행하고 종료 코드를 반환한다.

    실시간 출력(capture=False)으로 진행 상황을 즉시 표시한다.
    --tb=short: 간결한 traceback으로 JSON 크기 최소화.

    Returns:
        pytest 종료 코드 (0=전체 통과, 1=일부 실패, 2=중단)
    """
    cmd = [
        "arch", "-arm64", str(PYTHON),
        "-m", "pytest", test_path,
        "-v",
        "--tb=short",
        "--json-report",
        f"--json-report-file={json_report_path}",
    ]

    print(f"\n{'='*60}")
    print(f"E2E Health Check — {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Test: {test_path}")
    print(f"{'='*60}\n")

    result = subprocess.run(cmd, cwd=PROJECT_ROOT)
    return result.returncode


# ──────────────────────────────────────────────────────────────────────────────
# 2. JSON 리포트 파싱
# ──────────────────────────────────────────────────────────────────────────────

def _find_screenshot(test_name: str, run_start: float) -> Path | None:
    """테스트 실행 시간 이후에 생성된 스크린샷을 검색한다.

    conftest.py의 take_screenshot()은 'tests/e2e/screenshots/{name}.png'에 저장한다.
    error_* 프리픽스 또는 exception_* 프리픽스 파일을 우선 탐색한다.

    Args:
        test_name: 테스트 함수명 (예: "test_apt_search_shows_result_caption")
        run_start: pytest 실행 시작 Unix timestamp

    Returns:
        스크린샷 Path 또는 None
    """
    if not SCREENSHOT_DIR.exists():
        return None

    candidates = []
    for png in SCREENSHOT_DIR.glob("*.png"):
        mtime = png.stat().st_mtime
        if mtime >= run_start:
            candidates.append(png)

    if not candidates:
        return None

    # 테스트명 일부가 파일명에 포함된 것 우선
    short_name = test_name.replace("test_", "")
    for png in sorted(candidates, key=lambda p: p.stat().st_mtime, reverse=True):
        if short_name[:10] in png.stem or "exception" in png.stem or "error" in png.stem:
            return png

    # fallback: 가장 최근 스크린샷
    return sorted(candidates, key=lambda p: p.stat().st_mtime, reverse=True)[0]


def parse_report(json_path: Path, run_start: float) -> dict:
    """pytest-json-report JSON을 파싱하여 구조화된 딕셔너리를 반환한다.

    Returns:
        {
            "summary": {...},
            "failures": [{"test_name", "nodeid", "duration_s", "error_message",
                          "traceback", "screenshot_path"}],
            "passed": ["test_name", ...],
            "skipped": ["test_name", ...],
            "total_duration_s": float,
        }
    """
    with open(json_path, encoding="utf-8") as f:
        data = json.load(f)

    summary = data.get("summary", {})
    tests = data.get("tests", [])

    failures = []
    passed = []
    skipped = []

    for test in tests:
        nodeid = test.get("nodeid", "")
        test_name = nodeid.split("::")[-1] if "::" in nodeid else nodeid
        outcome = test.get("outcome", "unknown")
        duration = test.get("duration", 0)

        if outcome == "passed":
            passed.append(test_name)
        elif outcome == "skipped":
            skipped.append(test_name)
        elif outcome in ("failed", "error"):
            call = test.get("call", {}) or test.get("setup", {}) or {}
            longrepr = call.get("longrepr", "") or ""

            # 에러 메시지 첫 줄 추출
            lines = longrepr.strip().splitlines()
            error_message = lines[-1] if lines else "알 수 없는 오류"
            traceback = longrepr[:2000]  # 최대 2000자

            screenshot = _find_screenshot(test_name, run_start)

            failures.append({
                "test_name": test_name,
                "nodeid": nodeid,
                "duration_s": round(duration, 2),
                "error_message": error_message,
                "traceback": traceback,
                "screenshot_path": str(screenshot) if screenshot else None,
                "screenshot_exists": screenshot is not None,
            })

    return {
        "summary": summary,
        "failures": failures,
        "passed": passed,
        "skipped": skipped,
        "total_duration_s": round(data.get("duration", 0), 2),
    }


# ──────────────────────────────────────────────────────────────────────────────
# 3-B. result.md 자동 섹션 append
# ──────────────────────────────────────────────────────────────────────────────

def _get_current_branch() -> str:
    """현재 git 브랜치명을 반환한다. 실패 시 빈 문자열."""
    try:
        result = subprocess.run(
            ["git", "branch", "--show-current"],
            cwd=PROJECT_ROOT,
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode == 0:
            return result.stdout.strip()
        return ""
    except Exception:
        return ""


def _get_feature_result_md() -> "Path | None":
    """현재 브랜치에 대응하는 docs/features/{feature_name}/result.md 경로를 반환한다."""
    branch = _get_current_branch()
    if not branch or not branch.startswith("feature/"):
        return None
    feature_name = branch.removeprefix("feature/")
    return PROJECT_ROOT / "docs" / "features" / feature_name / "result.md"


def _build_result_section(parsed: dict, run_ts: str, report_path: Path) -> str:
    """파싱된 결과로 result.md에 append할 E2E 검증 결과 섹션을 생성한다."""
    summary = parsed["summary"]
    n_pass = summary.get("passed", 0)
    n_fail = summary.get("failed", 0)
    n_total = summary.get("total", 0)

    if n_fail == 0:
        result_line = f"✅ PASS ({n_pass}/{n_total})"
    else:
        result_line = f"❌ FAIL ({n_pass}/{n_total}, {n_fail}개 실패)"

    lines = [
        "",
        "---",
        "",
        "## E2E 검증 결과",
        "",
        f"- **실행일시:** {run_ts}",
        f"- **결과:** {result_line}",
        f"- **리포트:** {report_path}",
    ]

    failures = parsed.get("failures", [])
    if failures:
        lines.append("- **실패 목록:**")
        for fail in failures:
            lines.append(f"  - {fail.get('test_name', '<unknown>')}")

    lines.append("")

    return "\n".join(lines)


def append_result_md(parsed: dict, run_ts: str, report_path: Path) -> "Path | None":
    """현재 브랜치의 result.md에 E2E 검증 결과 섹션을 append한다.

    Returns:
        append된 result.md Path, 또는 파일이 없으면 None
    """
    result_md = _get_feature_result_md()
    if result_md is None:
        print("[WARNING] append_result_md: not on a feature branch, skipping result.md update")
        return None

    if not result_md.exists():
        print(f"[WARNING] append_result_md: {result_md} not found, skipping")
        return None

    section = _build_result_section(parsed, run_ts, report_path)
    with open(result_md, "a", encoding="utf-8") as f:
        f.write(section)

    print(f"\n[INFO] E2E 결과 섹션 추가됨: {result_md}")
    return result_md


# ──────────────────────────────────────────────────────────────────────────────
# 3. 마크다운 리포트 생성
# ──────────────────────────────────────────────────────────────────────────────

def build_markdown(parsed: dict, run_ts: str, test_path: str) -> str:
    """파싱된 결과로 구조화된 마크다운 헬스체크 리포트를 생성한다."""
    summary = parsed["summary"]
    failures = parsed["failures"]
    passed = parsed["passed"]
    skipped = parsed["skipped"]
    total_duration = parsed["total_duration_s"]

    n_pass = summary.get("passed", len(passed))
    n_fail = summary.get("failed", len(failures))
    n_skip = summary.get("skipped", len(skipped))
    n_total = summary.get("total", n_pass + n_fail + n_skip)

    status_emoji = "✅" if n_fail == 0 else "❌"

    lines = [
        f"# {status_emoji} E2E 헬스체크 리포트 — Real Estate 탭",
        f"",
        f"**생성일시:** {run_ts}  ",
        f"**테스트 대상:** `{test_path}`  ",
        f"**총 소요 시간:** {total_duration}s  ",
        f"**결과:** {n_pass} 통과 / {n_fail} 실패 / {n_skip} 스킵 / {n_total} 전체",
        f"",
        f"---",
        f"",
        f"## 요약",
        f"",
        f"| 상태 | 건수 |",
        f"|------|------|",
        f"| ✅ 통과 | {n_pass} |",
        f"| ❌ 실패 | {n_fail} |",
        f"| ⏭️ 스킵 | {n_skip} |",
        f"| 합계 | {n_total} |",
        f"",
    ]

    # ── 실패 목록 ──
    if failures:
        lines += [
            f"---",
            f"",
            f"## 실패 상세",
            f"",
        ]
        for i, fail in enumerate(failures, 1):
            screenshot_line = (
                f"**스크린샷:** `{fail['screenshot_path']}`"
                if fail["screenshot_exists"]
                else "**스크린샷:** 없음"
            )
            lines += [
                f"### {i}. `{fail['test_name']}`",
                f"",
                f"- **소요 시간:** {fail['duration_s']}s",
                f"- {screenshot_line}",
                f"",
                f"**에러 메시지:**",
                f"```",
                fail["error_message"],
                f"```",
                f"",
                f"**Traceback (앞 2000자):**",
                f"```",
                fail["traceback"],
                f"```",
                f"",
            ]
    else:
        lines += [
            f"---",
            f"",
            f"## 실패 없음",
            f"",
            f"모든 테스트가 통과했습니다. 🎉",
            f"",
        ]

    # ── 통과 목록 ──
    if passed:
        lines += [
            f"---",
            f"",
            f"## 통과 테스트",
            f"",
        ]
        for t in passed:
            lines.append(f"- ✅ `{t}`")
        lines.append("")

    # ── 스킵 목록 ──
    if skipped:
        lines += [
            f"---",
            f"",
            f"## 스킵 테스트",
            f"",
        ]
        for t in skipped:
            lines.append(f"- ⏭️ `{t}`")
        lines.append("")

    # ── 자동 수정 컨텍스트 ──
    lines += [
        f"---",
        f"",
        f"## 자동 수정 컨텍스트",
        f"",
        f"아래 정보는 Claude 자동 수정 루프를 위한 컨텍스트입니다.",
        f"",
        f"**소스 파일:**",
        f"- UI: `src/dashboard/views/real_estate.py`",
        f"- 테스트: `tests/e2e/test_e2e_real_estate.py`",
        f"- 헬퍼: `tests/e2e/conftest.py`",
        f"",
        f"**알려진 Streamlit 셀렉터 매핑:**",
        f"",
        f"| UI 요소 | Playwright 셀렉터 |",
        f"|---------|-----------------|",
        f"| 검색 버튼 | `get_by_role('button', name='🔍 검색')` — expander 스코핑 필요 |",
        f"| 결과 캡션 | `[data-testid='stCaptionContainer']` filter `has_text='건 검색됨'` |",
        f"| 예외 박스 | `[data-testid='stException']` |",
        f"| 경고 박스 | `[data-testid='stAlertWarning']` |",
        f"| info 박스 | `[data-testid='stAlertInfo']` |",
        f"| 탭 | `get_by_role('tab').filter(has_text=...)` |",
        f"| 데이터프레임 | `[data-testid='stDataFrame']` |",
        f"",
        f"**apt_master 상태 주의:**  ",
        f"`real_estate.db`가 비어있으면 Tab1이 `st.stop()` 호출 → 서브탭 미표시 (정상 케이스, pytest.skip() 처리됨)",
        f"",
    ]

    return "\n".join(lines)


# ──────────────────────────────────────────────────────────────────────────────
# 4. main
# ──────────────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="E2E 헬스체크 — 부동산 탭")
    parser.add_argument(
        "--test-path",
        default=DEFAULT_TEST_PATH,
        help=f"pytest 대상 경로 (기본값: {DEFAULT_TEST_PATH})",
    )
    args = parser.parse_args()

    # JSON 리포트 디렉토리 확인
    JSON_REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)

    run_start = datetime.now().timestamp()
    exit_code = run_pytest(args.test_path, JSON_REPORT_PATH)

    if not JSON_REPORT_PATH.exists():
        print("\n[ERROR] JSON 리포트가 생성되지 않았습니다.")
        print("pytest-json-report가 설치되어 있는지 확인하세요:")
        print("  arch -arm64 .venv/bin/python3.12 -m pip install pytest-json-report")
        sys.exit(2)

    parsed = parse_report(JSON_REPORT_PATH, run_start)
    run_ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    md_content = build_markdown(parsed, run_ts, args.test_path)

    MD_REPORT_PATH.write_text(md_content, encoding="utf-8")

    # result.md 자동 섹션 append
    append_result_md(parsed, run_ts, MD_REPORT_PATH)

    summary = parsed["summary"]
    n_pass = summary.get("passed", 0)
    n_fail = summary.get("failed", 0)
    n_total = summary.get("total", 0)

    print(f"\n{'='*60}")
    print(f"리포트 저장: {MD_REPORT_PATH}")
    print(f"결과: {n_pass}/{n_total} 통과 | {n_fail} 실패")
    print(f"{'='*60}\n")

    # CI 호환: pytest 종료 코드 그대로 전달 (0=통과, 1=실패)
    sys.exit(exit_code if exit_code in (0, 1) else 0)


if __name__ == "__main__":
    main()
