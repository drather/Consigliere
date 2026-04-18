# Playwright E2E → SOP Phase 4 통합 구현 플랜

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** SOP Phase 4에 Playwright E2E 검증을 하드 블로킹 게이트로 통합하고, `e2e_health_check.py`가 result.md에 E2E 결과 섹션을 자동 append하도록 한다.

**Architecture:** `e2e_health_check.py`에 `append_result_md()` 함수를 추가해 현재 git 브랜치에서 피처명을 추출하고 `docs/features/{feature_name}/result.md`에 결과 섹션을 append한다. `sop.md`의 Phase 4를 교체하여 E2E 게이트를 공식 절차로 명문화한다.

**Tech Stack:** Python 3.12, subprocess (git), pathlib, pytest-playwright (기존)

---

## 파일 변경 범위

| 파일 | 변경 유형 | 내용 |
|------|-----------|------|
| `scripts/e2e_health_check.py` | 수정 | `append_result_md()` 함수 추가 + `main()` 에서 호출 |
| `docs/guidelines/sop.md` | 수정 | Phase 4 섹션 교체 + 문서 표준 테이블 행 추가 |

> **참고:** exit code(0/1)는 `e2e_health_check.py` line 350에 이미 구현되어 있음. 추가 불필요.

---

## Task 1: `append_result_md()` 함수 구현 (TDD)

**Files:**
- Modify: `scripts/e2e_health_check.py`
- Test: `tests/unit/scripts/test_e2e_health_check.py` (신규)

### 함수 명세

```python
def append_result_md(parsed: dict, run_ts: str, report_path: Path) -> Path | None:
    """현재 git 브랜치에서 피처명을 추출하고 result.md에 E2E 결과 섹션을 append한다.

    Returns:
        append된 result.md Path, 또는 result.md 미존재 시 None
    """
```

**동작:**
1. `git branch --show-current` 실행 → 브랜치명 추출
2. `feature/` 접두사 제거 → 피처 디렉토리명 (예: `feature/e2e-real-estate-scenarios` → `e2e-real-estate-scenarios`)
3. `docs/features/{feature_name}/result.md` 존재 확인
4. 존재하면 아래 섹션 append, 없으면 경고 출력 후 `None` 반환

**append할 섹션 포맷:**
```markdown

---

## E2E 검증 결과

- **실행일시:** 2026-04-16 14:30
- **결과:** ✅ PASS (18/18) | ❌ FAIL (15/18, 3개 실패)
- **리포트:** docs/e2e_health_report.md
- **실패 목록:**
  - test_apt_search_shows_result_caption
  - test_apt_dataframe_visible_with_results
```

(PASS인 경우 "실패 목록" 행 생략)

---

- [ ] **Step 1: 테스트 디렉토리 생성 확인**

```bash
mkdir -p tests/unit/scripts
touch tests/unit/scripts/__init__.py
```

- [ ] **Step 2: 실패하는 테스트 작성**

`tests/unit/scripts/test_e2e_health_check.py` 파일을 아래 내용으로 신규 생성:

```python
"""append_result_md() 단위 테스트."""
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# scripts/ 디렉토리를 sys.path에 추가
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / "scripts"))

from e2e_health_check import append_result_md, _build_result_section


# ── _build_result_section ──────────────────────────────────────────────────────

def test_build_result_section_all_pass():
    parsed = {
        "summary": {"passed": 18, "failed": 0, "total": 18},
        "failures": [],
    }
    section = _build_result_section(parsed, "2026-04-16 14:30", Path("docs/e2e_health_report.md"))
    assert "✅ PASS (18/18)" in section
    assert "실패 목록" not in section


def test_build_result_section_with_failures():
    parsed = {
        "summary": {"passed": 15, "failed": 3, "total": 18},
        "failures": [
            {"test_name": "test_foo"},
            {"test_name": "test_bar"},
            {"test_name": "test_baz"},
        ],
    }
    section = _build_result_section(parsed, "2026-04-16 14:30", Path("docs/e2e_health_report.md"))
    assert "❌ FAIL (15/18, 3개 실패)" in section
    assert "test_foo" in section
    assert "test_bar" in section
    assert "test_baz" in section


def test_build_result_section_contains_report_path():
    parsed = {
        "summary": {"passed": 5, "failed": 0, "total": 5},
        "failures": [],
    }
    section = _build_result_section(parsed, "2026-04-16 10:00", Path("docs/e2e_health_report.md"))
    assert "docs/e2e_health_report.md" in section


# ── append_result_md ───────────────────────────────────────────────────────────

def test_append_result_md_writes_to_result_md(tmp_path):
    """result.md가 존재할 때 섹션이 append되는지 확인."""
    result_md = tmp_path / "result.md"
    result_md.write_text("# 기존 내용\n\n기존 본문\n", encoding="utf-8")

    parsed = {
        "summary": {"passed": 3, "failed": 0, "total": 3},
        "failures": [],
    }

    with patch("e2e_health_check._get_feature_result_md", return_value=result_md):
        returned = append_result_md(parsed, "2026-04-16 14:30", Path("docs/e2e_health_report.md"))

    assert returned == result_md
    content = result_md.read_text(encoding="utf-8")
    assert "## E2E 검증 결과" in content
    assert "✅ PASS (3/3)" in content
    # 기존 내용 보존
    assert "기존 내용" in content


def test_append_result_md_returns_none_when_result_md_missing(tmp_path):
    """result.md가 없을 때 None을 반환하고 경고를 출력하는지 확인."""
    missing_path = tmp_path / "nonexistent" / "result.md"

    with patch("e2e_health_check._get_feature_result_md", return_value=missing_path):
        returned = append_result_md(
            {"summary": {"passed": 0, "failed": 0, "total": 0}, "failures": []},
            "2026-04-16 14:30",
            Path("docs/e2e_health_report.md"),
        )

    assert returned is None


def test_get_feature_result_md_strips_feature_prefix(tmp_path):
    """feature/ 접두사가 제거되어 올바른 경로가 구성되는지 확인."""
    from e2e_health_check import _get_feature_result_md

    with patch("e2e_health_check._get_current_branch", return_value="feature/my-cool-feature"):
        with patch("e2e_health_check.PROJECT_ROOT", tmp_path):
            path = _get_feature_result_md()

    assert path == tmp_path / "docs" / "features" / "my-cool-feature" / "result.md"


def test_get_feature_result_md_non_feature_branch(tmp_path):
    """feature/ 접두사 없는 브랜치도 그대로 경로에 사용되는지 확인."""
    from e2e_health_check import _get_feature_result_md

    with patch("e2e_health_check._get_current_branch", return_value="main"):
        with patch("e2e_health_check.PROJECT_ROOT", tmp_path):
            path = _get_feature_result_md()

    assert path == tmp_path / "docs" / "features" / "main" / "result.md"
```

- [ ] **Step 3: 테스트 실행 — FAIL 확인**

```bash
arch -arm64 .venv/bin/python3.12 -m pytest tests/unit/scripts/test_e2e_health_check.py -v
```

Expected: `ImportError: cannot import name 'append_result_md'` 또는 `ModuleNotFoundError`

- [ ] **Step 4: `e2e_health_check.py`에 세 함수 구현**

`scripts/e2e_health_check.py`의 `# ── 3. 마크다운 리포트 생성` 섹션 바로 위에 아래 블록을 추가:

```python
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
        return result.stdout.strip()
    except Exception:
        return ""


def _get_feature_result_md() -> Path:
    """현재 브랜치에서 피처명을 추출해 result.md 경로를 반환한다.

    feature/my-feature → docs/features/my-feature/result.md
    other-branch       → docs/features/other-branch/result.md
    """
    branch = _get_current_branch()
    feature_name = branch.removeprefix("feature/") if branch else "unknown"
    return PROJECT_ROOT / "docs" / "features" / feature_name / "result.md"


def _build_result_section(parsed: dict, run_ts: str, report_path: Path) -> str:
    """E2E 검증 결과 마크다운 섹션 문자열을 생성한다."""
    summary = parsed["summary"]
    failures = parsed["failures"]
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

    if failures:
        lines.append("- **실패 목록:**")
        for fail in failures:
            lines.append(f"  - {fail['test_name']}")

    lines.append("")
    return "\n".join(lines)


def append_result_md(parsed: dict, run_ts: str, report_path: Path) -> Path | None:
    """result.md에 E2E 검증 결과 섹션을 append한다.

    Returns:
        append된 result.md Path, 또는 result.md 미존재 시 None
    """
    result_md = _get_feature_result_md()

    if not result_md.exists():
        print(f"\n[WARNING] result.md를 찾을 수 없습니다: {result_md}")
        print("  result.md 없이 e2e_health_report.md에만 결과를 저장합니다.")
        return None

    section = _build_result_section(parsed, run_ts, report_path)
    with open(result_md, "a", encoding="utf-8") as f:
        f.write(section)

    print(f"\n[INFO] E2E 결과 섹션 추가됨: {result_md}")
    return result_md
```

- [ ] **Step 5: `main()` 함수에서 `append_result_md()` 호출 추가**

`scripts/e2e_health_check.py`의 `main()` 함수 내부에서 `MD_REPORT_PATH.write_text(...)` 직후 아래 두 줄을 추가:

```python
    MD_REPORT_PATH.write_text(md_content, encoding="utf-8")

    # result.md 자동 섹션 append (신규)
    append_result_md(parsed, run_ts, MD_REPORT_PATH)
```

즉, 기존 코드:
```python
    MD_REPORT_PATH.write_text(md_content, encoding="utf-8")

    summary = parsed["summary"]
```

를 아래로 교체:
```python
    MD_REPORT_PATH.write_text(md_content, encoding="utf-8")

    # result.md 자동 섹션 append
    append_result_md(parsed, run_ts, MD_REPORT_PATH)

    summary = parsed["summary"]
```

- [ ] **Step 6: 테스트 실행 — PASS 확인**

```bash
arch -arm64 .venv/bin/python3.12 -m pytest tests/unit/scripts/test_e2e_health_check.py -v
```

Expected: 모든 테스트 PASS

- [ ] **Step 7: 기존 단위 테스트 회귀 확인**

```bash
arch -arm64 .venv/bin/python3.12 -m pytest tests/unit/ -v
```

Expected: 기존 테스트 전부 PASS (새 테스트 포함)

- [ ] **Step 8: 커밋**

```bash
git add scripts/e2e_health_check.py tests/unit/scripts/test_e2e_health_check.py tests/unit/scripts/__init__.py
git commit -m "feat(e2e): append_result_md() — Phase 4 E2E 결과 result.md 자동 기록"
```

---

## Task 2: `sop.md` Phase 4 업데이트

**Files:**
- Modify: `docs/guidelines/sop.md`

- [ ] **Step 1: Phase 4 섹션 교체**

`docs/guidelines/sop.md`의 `## Phase 4: Release` 섹션 전체를 아래로 교체:

```markdown
## Phase 4: Release

### 4-1. 백엔드 단위 테스트

```bash
arch -arm64 .venv/bin/python3.12 -m pytest tests/ -v
```

### 4-2. E2E 화면단 검증 (하드 블로킹 ⭐)

```bash
arch -arm64 .venv/bin/python3.12 scripts/e2e_health_check.py
```

- exit 0 → 계속 진행
- exit 1 → **머지 중단.** 실패 테스트 수정 후 재실행

> **면제 조건:** 화면 변경이 없는 작업(백엔드 리팩토링, DB 스키마 변경, n8n 워크플로우 수정, 문서 작업 등)은  
> `result.md`에 `## E2E 검증 면제` 섹션과 사유를 기록하면 4-2 스킵 허용.

### 4-3. 머지 및 푸시

```bash
git checkout master
git merge feature/{feature_name}
git push origin master
```
```

- [ ] **Step 2: 문서 작성 표준 테이블에 행 추가**

`docs/guidelines/sop.md`의 `## 문서 작성 표준` 테이블에 아래 행 추가:

기존 마지막 행:
```
| `result.md` | 구현 결과, walkthrough, 검증 증거 | Phase 3 완료 시 |
```

아래로 교체:
```
| `result.md` | 구현 결과, walkthrough, 검증 증거, **E2E 검증 결과** | Phase 3 완료 시 + Phase 4-2 완료 시 자동 생성 |
```

- [ ] **Step 3: 커밋**

```bash
git add docs/guidelines/sop.md
git commit -m "docs(sop): Phase 4에 E2E 화면단 검증 게이트 추가"
```

---

## 검증 체크리스트 (구현 완료 후)

- [ ] `arch -arm64 .venv/bin/python3.12 -m pytest tests/unit/scripts/ -v` — 신규 단위 테스트 PASS
- [ ] `arch -arm64 .venv/bin/python3.12 -m pytest tests/unit/ -v` — 기존 단위 테스트 회귀 없음
- [ ] `docs/guidelines/sop.md` Phase 4에 4-1/4-2/4-3 세 단계 포함 확인
- [ ] `docs/guidelines/sop.md` 문서 표준 테이블에 E2E 항목 포함 확인
- [ ] `scripts/e2e_health_check.py`에 `_get_current_branch`, `_get_feature_result_md`, `_build_result_section`, `append_result_md` 네 함수 존재 확인
