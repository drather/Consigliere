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


def test_stats_block_becomes_blockquote():
    text = "<!-- stats -->\n**거래:** 4건\n**위치:** 강남구\n<!-- /stats -->"
    result = md_to_slack(text)
    assert result == "> *거래:* 4건\n> *위치:* 강남구"


def test_stats_markers_removed_from_output():
    text = "<!-- stats -->\n**거래:** 4건\n<!-- /stats -->"
    result = md_to_slack(text)
    assert "<!--" not in result
    assert "-->" not in result


def test_stats_block_inline_with_content():
    text = "### 1. 단지명\n\n<!-- stats -->\n**거래:** 4건  |  평균 5억\n**출퇴근:** 30분\n<!-- /stats -->\n\n**거래 동향**"
    result = md_to_slack(text)
    assert "> *거래:* 4건" in result
    assert "> *출퇴근:* 30분" in result
    assert "*거래 동향*" in result
    assert "<!--" not in result
