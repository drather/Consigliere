from modules.real_estate.presenter import md_to_slack


def test_bold_conversion():
    assert md_to_slack("**bold**") == "*bold*"


def test_heading_conversion():
    assert md_to_slack("# Title") == "*Title*"
    assert md_to_slack("## Section") == "*Section*"
    assert md_to_slack("### Sub") == "*Sub*"


def test_divider_removed():
    result = md_to_slack("before\n---\nafter")
    assert "---" not in result
    assert "before" in result
    assert "after" in result


def test_blockquote_stripped():
    assert md_to_slack("> quoted text") == "quoted text"


def test_bullet_preserved():
    result = md_to_slack("- item one\n- item two")
    assert "- item one" in result
    assert "- item two" in result


def test_emoji_preserved():
    result = md_to_slack("⚡ **출퇴근편의성** (20점): *5점*")
    assert "⚡" in result
    assert "*출퇴근편의성*" in result


def test_multiple_blank_lines_compressed():
    result = md_to_slack("a\n\n\n\nb")
    assert "\n\n\n" not in result
