from app.compliance import assert_compliant, scan_text


def test_scan_text_passes_safe_research_language():
    result = scan_text("这是一份概率推演和数据观察报告，仅供娱乐研究，并包含风险提示。")

    assert result["passed"] is True
    assert result["matches"] == []


def test_scan_text_reports_banned_terms_without_raising():
    result = scan_text("这不是稳赚或必中内容。")

    assert result["passed"] is False
    assert "稳赚" in result["matches"]
    assert "必中" in result["matches"]


def test_assert_compliant_returns_failed_status_instead_of_throwing():
    result = assert_compliant("禁止出现跟单和荐号。")

    assert result["passed"] is False
    assert result["status"] == "failed"
    assert set(result["matches"]) >= {"跟单", "荐号"}
