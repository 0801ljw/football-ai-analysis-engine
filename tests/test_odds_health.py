from pathlib import Path

from app.odds_health import inspect_odds_payload, load_odds_file


def test_inspect_odds_payload_all_valid():
    payload = {
        "matches": {
            "091": {
                "主队": "巴西",
                "客队": "德国",
                "spf": {"胜": 1.8},
                "handicap": {"让胜": 2.1},
                "total_goals": {"2": 3.0},
                "correct_score": {"1-0": 6.5},
                "half_full": {"胜胜": 2.8},
            }
        }
    }

    health = inspect_odds_payload(payload)

    assert health["ok"] is True
    assert health["total"] == 1
    assert health["valid_count"] == 1
    assert health["invalid_count"] == 0
    assert health["valid_nums"] == ["091"]
    assert health["invalid"] == {}
    assert health["markets"]["091"] == {
        "has_spf": True,
        "has_handicap": True,
        "has_total_goals": True,
        "has_correct_score": True,
        "has_half_full": True,
    }


def test_inspect_odds_payload_all_invalid_error():
    payload = {"matches": {"086": {"error": "未在受注列表中找到该编号"}}}

    health = inspect_odds_payload(payload)

    assert health["ok"] is False
    assert health["total"] == 1
    assert health["valid_count"] == 0
    assert health["invalid_count"] == 1
    assert health["invalid"] == {"086": "未在受注列表中找到该编号"}
    assert "没有可用于生成报告的有效场次" in health["summary"]


def test_inspect_odds_payload_some_valid_some_invalid():
    payload = {
        "matches": {
            "086": {"error": "未在受注列表中找到该编号"},
            "091": {"主队": "阿根廷", "客队": "法国", "spf": {}},
        }
    }

    health = inspect_odds_payload(payload)

    assert health["ok"] is True
    assert health["valid_count"] == 1
    assert health["invalid_count"] == 1
    assert health["valid_nums"] == ["091"]
    assert health["invalid"]["086"] == "未在受注列表中找到该编号"
    assert health["markets"]["091"]["has_spf"] is True
    assert health["markets"]["091"]["has_handicap"] is False


def test_inspect_odds_payload_bad_format():
    health = inspect_odds_payload({"matches": ["bad"]})

    assert health["ok"] is False
    assert health["total"] == 0
    assert health["valid_count"] == 0
    assert health["invalid_count"] == 0
    assert "格式不符合预期" in health["summary"]


def test_load_odds_file_returns_parse_error_payload(tmp_path: Path):
    path = tmp_path / "odds.json"
    path.write_text("{bad json", encoding="utf-8")

    payload = load_odds_file(path)

    assert payload["_load_error"]["type"] == "JSONDecodeError"
