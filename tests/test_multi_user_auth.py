from fastapi.testclient import TestClient

from app.auth import AuthManager
from app.main import app
from app.run_manager import RunManager

client = TestClient(app)


def test_admin_can_create_user_and_token_auth_controls_real_runs(monkeypatch, tmp_path):
    auth = AuthManager(tmp_path / "auth.db")
    admin = auth.create_user("admin", role="admin", plan="internal", run_quota=10)
    monkeypatch.setattr("app.main.get_auth_manager", lambda: auth)
    manager = RunManager(root=tmp_path / "runs")
    monkeypatch.setattr("app.main.get_run_manager", lambda: manager)

    create_user_response = client.post(
        "/api/admin/users",
        headers={"X-API-Token": admin["token"]},
        json={"username": "alice", "role": "user", "plan": "free", "run_quota": 1},
    )
    assert create_user_response.status_code == 200
    created = create_user_response.json()
    assert created["user"]["username"] == "alice"
    assert created["user"]["token_preview"].startswith("wc_")
    assert created["user"].get("token_hash") is None
    assert created["token"].startswith("wc_")

    me_response = client.get("/api/me", headers={"X-API-Token": created["token"]})
    assert me_response.status_code == 200
    assert me_response.json()["user"]["username"] == "alice"

    denied = client.post(
        "/api/runs",
        json={"nums": "086", "title": "世界杯数据推演", "theme": "dark", "dry_run": False},
    )
    assert denied.status_code == 401

    allowed = client.post(
        "/api/runs",
        headers={"X-API-Token": created["token"]},
        json={"nums": "086", "title": "世界杯数据推演", "theme": "dark", "dry_run": True},
    )
    assert allowed.status_code == 200


def test_user_quota_blocks_second_real_run(monkeypatch, tmp_path):
    auth = AuthManager(tmp_path / "auth.db")
    user = auth.create_user("bob", role="user", plan="free", run_quota=1)
    monkeypatch.setattr("app.main.get_auth_manager", lambda: auth)
    manager = RunManager(root=tmp_path / "runs")
    monkeypatch.setattr("app.main.get_run_manager", lambda: manager)

    def fake_fetch(self, nums, out=None, timeout=30):
        out.write_text('{"matches":{"086":{"主队":"巴西","客队":"德国","胜平负":{},"让球":{},"总进球":{},"比分波胆":{}}}}', encoding="utf-8")
        return {"ok": True, "command": ["fetch"], "stdout": "", "stderr": ""}

    def fake_report(self, odds_path, out_path, title, theme="dark", intel_path=None, timeout=30):
        out_path.write_text("<html>ok</html>", encoding="utf-8")
        return {"ok": True, "command": ["report"], "stdout": "", "stderr": ""}

    monkeypatch.setattr("app.run_manager.SportteryService.fetch_odds", fake_fetch)
    monkeypatch.setattr("app.run_manager.ReportService.generate_report_file", fake_report)

    first = client.post(
        "/api/runs",
        headers={"X-API-Token": user["token"]},
        json={"nums": "086", "title": "世界杯数据推演", "theme": "dark", "dry_run": False},
    )
    assert first.status_code == 200

    second = client.post(
        "/api/runs",
        headers={"X-API-Token": user["token"]},
        json={"nums": "086", "title": "世界杯数据推演", "theme": "dark", "dry_run": False},
    )
    assert second.status_code == 429
    assert "quota exceeded" in second.json()["detail"]


def test_regular_users_only_see_and_access_their_own_runs(monkeypatch, tmp_path):
    auth = AuthManager(tmp_path / "auth.db")
    alice = auth.create_user("alice", role="user", plan="free", run_quota=10)
    bob = auth.create_user("bob", role="user", plan="free", run_quota=10)
    admin = auth.create_user("admin", role="admin", plan="internal", run_quota=10)
    monkeypatch.setattr("app.main.get_auth_manager", lambda: auth)
    manager = RunManager(root=tmp_path / "runs")
    monkeypatch.setattr("app.main.get_run_manager", lambda: manager)

    alice_run = client.post(
        "/api/runs",
        headers={"X-API-Token": alice["token"]},
        json={"nums": "086", "title": "Alice Run", "theme": "dark", "dry_run": True},
    ).json()
    bob_run = client.post(
        "/api/runs",
        headers={"X-API-Token": bob["token"]},
        json={"nums": "091", "title": "Bob Run", "theme": "dark", "dry_run": True},
    ).json()

    alice_list = client.get("/api/runs", headers={"X-API-Token": alice["token"]}).json()["runs"]
    assert [item["run_id"] for item in alice_list] == [alice_run["run_id"]]

    bob_list = client.get("/api/runs", headers={"X-API-Token": bob["token"]}).json()["runs"]
    assert [item["run_id"] for item in bob_list] == [bob_run["run_id"]]

    forbidden_detail = client.get(f"/api/runs/{bob_run['run_id']}", headers={"X-API-Token": alice["token"]})
    assert forbidden_detail.status_code == 404

    admin_list = client.get("/api/runs", headers={"X-API-Token": admin["token"]}).json()["runs"]
    assert {item["run_id"] for item in admin_list} == {alice_run["run_id"], bob_run["run_id"]}


def test_admin_can_reset_disable_and_update_user_quota(monkeypatch, tmp_path):
    auth = AuthManager(tmp_path / "auth.db")
    admin = auth.create_user("admin", role="admin", plan="internal", run_quota=10)
    alice = auth.create_user("alice", role="user", plan="free", run_quota=1)
    monkeypatch.setattr("app.main.get_auth_manager", lambda: auth)
    manager = RunManager(root=tmp_path / "runs")
    monkeypatch.setattr("app.main.get_run_manager", lambda: manager)

    users = client.get("/api/admin/users", headers={"X-API-Token": admin["token"]}).json()
    listed_alice = next(item for item in users["users"] if item["username"] == "alice")
    assert listed_alice["token_preview"].startswith("wc_")
    assert "token_hash" not in listed_alice
    assert listed_alice["quota"]["run_quota"] == 1

    update = client.patch(
        f"/api/admin/users/{alice['user']['user_id']}",
        headers={"X-API-Token": admin["token"]},
        json={"plan": "pro", "run_quota": 5, "active": False},
    )
    assert update.status_code == 200
    assert update.json()["user"]["plan"] == "pro"
    assert update.json()["user"]["run_quota"] == 5
    assert update.json()["user"]["active"] == 0

    disabled_me = client.get("/api/me", headers={"X-API-Token": alice["token"]})
    assert disabled_me.status_code == 401

    reset = client.post(
        f"/api/admin/users/{alice['user']['user_id']}/reset-token",
        headers={"X-API-Token": admin["token"]},
    )
    assert reset.status_code == 200
    new_token = reset.json()["token"]
    assert new_token.startswith("wc_")
    assert reset.json()["user"]["token_preview"].endswith(new_token[-4:])

    reenable = client.patch(
        f"/api/admin/users/{alice['user']['user_id']}",
        headers={"X-API-Token": admin["token"]},
        json={"active": True},
    )
    assert reenable.status_code == 200

    old_token_me = client.get("/api/me", headers={"X-API-Token": alice["token"]})
    assert old_token_me.status_code == 401
    new_token_me = client.get("/api/me", headers={"X-API-Token": new_token})
    assert new_token_me.status_code == 200
    assert new_token_me.json()["quota"]["run_quota"] == 5


def test_non_admin_cannot_manage_users(monkeypatch, tmp_path):
    auth = AuthManager(tmp_path / "auth.db")
    alice = auth.create_user("alice", role="user", plan="free", run_quota=1)
    monkeypatch.setattr("app.main.get_auth_manager", lambda: auth)

    response = client.get("/api/admin/users", headers={"X-API-Token": alice["token"]})

    assert response.status_code == 403


def test_browser_shell_exposes_admin_user_management_controls():
    response = client.get("/")

    assert response.status_code == 200
    assert 'id="auth-token"' in response.text
    assert 'id="auth-save-button"' in response.text
    assert "保存 API Token" in response.text
    assert 'id="admin-users-button"' in response.text
    assert 'id="admin-user-create-form"' in response.text
    assert "Admin 用户管理" in response.text
