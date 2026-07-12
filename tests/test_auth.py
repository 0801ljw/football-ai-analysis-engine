from app.auth import AuthManager


def test_auth_manager_creates_user_and_authenticates_token(tmp_path):
    auth = AuthManager(tmp_path / "auth.db")

    created = auth.create_user("alice", role="admin", plan="pro", run_quota=3)
    token = created["token"]

    assert token.startswith("wc_")
    assert created["user"]["username"] == "alice"
    assert created["user"]["role"] == "admin"
    assert created["user"]["plan"] == "pro"
    assert created["user"]["run_quota"] == 3

    user = auth.authenticate(token)
    assert user is not None
    assert user["username"] == "alice"
    assert user["role"] == "admin"
    assert "token_hash" not in user
    assert auth.authenticate("bad-token") is None


def test_auth_manager_tracks_per_user_quota(tmp_path):
    auth = AuthManager(tmp_path / "auth.db")
    created = auth.create_user("bob", plan="free", run_quota=1)
    user = auth.authenticate(created["token"])

    status = auth.quota_status(user)
    assert status["quota_exceeded"] is False

    auth.record_usage(user["user_id"], "real_run_created", "run-1")

    status = auth.quota_status(user)
    assert status["real_runs_used"] == 1
    assert status["remaining_real_runs"] == 0
    assert status["quota_exceeded"] is True
