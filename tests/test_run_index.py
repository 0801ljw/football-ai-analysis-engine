from pathlib import Path

from app.run_index import RunIndex


def test_run_index_upsert_query_and_stats(tmp_path):
    index = RunIndex(tmp_path / "app.db")
    detail = {
        "run_id": "run-1",
        "created_at": "2026-07-05T00:00:00Z",
        "status": "succeeded",
        "request": {"title": "世界杯数据推演", "nums": ["091"], "dry_run": False},
        "artifacts": {"report_exists": True, "prediction_exists": True},
        "data_quality": {"grade": "A", "status": "publishable"},
        "log": {"finished_at": "2026-07-05T00:01:00Z"},
    }

    index.upsert(detail)

    rows = index.query(status="succeeded", num="091", quality="A", q="世界杯")
    assert len(rows) == 1
    assert rows[0]["run_id"] == "run-1"
    assert rows[0]["report_exists"] == 1
    assert index.stats()["total_runs_indexed"] == 1
