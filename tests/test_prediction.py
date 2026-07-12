from pathlib import Path

from app.prediction import build_prediction


def _health(valid_count=1, invalid_count=0):
    return {
        "ok": valid_count > 0,
        "total": valid_count + invalid_count,
        "valid_count": valid_count,
        "invalid_count": invalid_count,
        "valid_nums": [str(90 + idx) for idx in range(valid_count)],
        "invalid": {"086": "未在受注列表中找到该编号"} if invalid_count else {},
        "markets": {},
        "summary": "health summary",
    }


def _payload(match):
    return {"matches": {"091": {"主队": "巴西", "客队": "德国", **match}}}


def test_build_prediction_grades_a_when_all_valid_and_four_market_signals(tmp_path: Path):
    prediction = build_prediction(
        run_id="run-a",
        valid_odds_payload=_payload({"胜平负": {}, "让球": {}, "总进球": {}, "比分波胆": {}}),
        odds_health=_health(valid_count=1, invalid_count=0),
        odds_path=str(tmp_path / "odds.json"),
        valid_odds_path=str(tmp_path / "odds.valid.json"),
        report_path=str(tmp_path / "report.html"),
    )

    assert prediction["schema_version"] == "1.1"
    assert prediction["source"]["source_label"] == "竞彩公开接口实时抓取"
    assert prediction["data_trust"]["grade"] == "A"
    assert prediction["data_trust"]["trust_level"] == "高"
    assert prediction["data_quality"]["grade"] == "A"
    assert prediction["data_quality"]["status"] == "publishable"
    assert prediction["data_quality"]["signals"]["has_1x2"] is True
    assert prediction["matches"][0]["num"] == "091"
    assert prediction["matches"][0]["home"] == "巴西"
    assert prediction["compliance"]["publish_blocked"] is False


def test_build_prediction_grades_b_c_d():
    base_args = {
        "run_id": "run",
        "odds_path": "odds.json",
        "valid_odds_path": "odds.valid.json",
        "report_path": "report.html",
    }

    grade_b = build_prediction(
        valid_odds_payload=_payload({"胜平负": {}, "让球": {}, "总进球": {}}),
        odds_health=_health(valid_count=1, invalid_count=0),
        **base_args,
    )
    assert grade_b["data_quality"]["grade"] == "B"
    assert grade_b["data_quality"]["status"] == "publishable"

    grade_c = build_prediction(
        valid_odds_payload=_payload({"胜平负": {}}),
        odds_health=_health(valid_count=1, invalid_count=1),
        **base_args,
    )
    assert grade_c["data_quality"]["grade"] == "C"
    assert grade_c["data_quality"]["status"] == "internal_reference"
    assert grade_c["compliance"]["warnings"]

    grade_d = build_prediction(
        valid_odds_payload={"matches": {}},
        odds_health=_health(valid_count=0, invalid_count=1),
        **base_args,
    )
    assert grade_d["data_quality"]["grade"] == "D"
    assert grade_d["data_quality"]["status"] == "insufficient"
    assert grade_d["compliance"]["publish_blocked"] is True
