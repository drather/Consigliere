"""append_result_md() 단위 테스트."""
import sys
from pathlib import Path
from unittest.mock import patch

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
    assert "기존 내용" in content


def test_append_result_md_returns_none_when_result_md_missing(tmp_path):
    missing_path = tmp_path / "nonexistent" / "result.md"

    with patch("e2e_health_check._get_feature_result_md", return_value=missing_path):
        returned = append_result_md(
            {"summary": {"passed": 0, "failed": 0, "total": 0}, "failures": []},
            "2026-04-16 14:30",
            Path("docs/e2e_health_report.md"),
        )

    assert returned is None


def test_get_feature_result_md_strips_feature_prefix(tmp_path):
    from e2e_health_check import _get_feature_result_md

    with patch("e2e_health_check._get_current_branch", return_value="feature/my-cool-feature"):
        with patch("e2e_health_check.PROJECT_ROOT", tmp_path):
            path = _get_feature_result_md()

    assert path == tmp_path / "docs" / "features" / "my-cool-feature" / "result.md"


def test_get_feature_result_md_non_feature_branch(tmp_path):
    from e2e_health_check import _get_feature_result_md

    with patch("e2e_health_check._get_current_branch", return_value="main"):
        with patch("e2e_health_check.PROJECT_ROOT", tmp_path):
            path = _get_feature_result_md()

    assert path == tmp_path / "docs" / "features" / "main" / "result.md"
