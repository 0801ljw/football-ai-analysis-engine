from app.commercial import UsageTracker


def test_usage_tracker_quota_and_summary(tmp_path):
    tracker = UsageTracker(tmp_path / "app.db", plan="free", run_quota=1)

    assert tracker.quota_status()["quota_exceeded"] is False
    tracker.record("real_run_created", "run-1", "test")

    status = tracker.quota_status()
    assert status["plan"] == "free"
    assert status["real_runs_used"] == 1
    assert status["remaining_real_runs"] == 0
    assert status["quota_exceeded"] is True

    summary = tracker.summary()
    assert summary["events"]["real_run_created"] == 1
    assert summary["recent"][0]["run_id"] == "run-1"
