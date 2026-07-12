from fastapi.testclient import TestClient
import os
from pathlib import Path
import zipfile

from app.main import app
from app.run_manager import RunManager


client = TestClient(app)


def test_homepage_renders_compliant_product_shell():
    response = client.get("/")

    assert response.status_code == 200
    assert "足球赛事 AI 推演引擎" in response.text
    assert "概率推演" in response.text
    assert "风险提示" in response.text
    assert "三步生成赛前报告" in response.text
    assert "高级工具" in response.text
    assert 'id="consumer-discover-form"' in response.text
    assert 'id="consumer-run-form"' in response.text
    assert 'id="consumer-run-result"' in response.text
    assert 'id="consumer-nums"' in response.text
    assert 'id="consumer-discover-button"' in response.text
    assert 'id="consumer-selected-nums"' in response.text
    assert 'id="consumer-run-button"' in response.text
    assert 'id="consumer-progress"' in response.text
    assert 'name="trial_mode"' in response.text
    assert 'checked' in response.text
    assert "试用模式" in response.text
    assert 'id="runs-filter-form"' in response.text
    assert "商业化状态 / Admin usage" in response.text
    assert 'id="admin-usage-button"' in response.text
    assert 'data-desktop-mode="false"' in response.text


def test_api_matches_returns_demo_data():
    response = client.get("/api/matches")

    assert response.status_code == 200
    data = response.json()
    assert len(data["matches"]) >= 3
    assert data["matches"][0]["source"] == "demo"


def test_api_generate_returns_report_json():
    response = client.post("/api/generate", json={"match_id": "demo-001", "theme": "dark"})

    assert response.status_code == 200
    data = response.json()
    assert data["match"]["id"] == "demo-001"
    assert data["content_copy"]["title"]
    assert data["compliance_status"]["passed"] is True


def test_report_page_renders_chinese_report():
    response = client.get("/report/demo-001")

    assert response.status_code == 200
    assert "中文推演报告" in response.text
    assert "数据观察" in response.text


def test_api_skill_status_returns_bridge_metadata():
    response = client.get("/api/skill/status")

    assert response.status_code == 200
    data = response.json()
    assert "skill_path" in data
    assert "available" in data
    assert "scripts" in data
    assert "fetch_sporttery.py" in data["scripts"]


def test_api_system_doctor_returns_runtime_diagnostics():
    response = client.get("/api/system/doctor")

    assert response.status_code == 200
    data = response.json()
    assert data["status"] in {"ready", "degraded", "not_ready"}
    assert isinstance(data["ok"], bool)
    assert isinstance(data["checks"], list)
    assert data["summary"]
    assert {check["id"] for check in data["checks"]} >= {"python_version", "settings", "runs_directory"}


def test_api_system_setup_guide_returns_first_start_shape():
    response = client.get("/api/system/setup-guide")

    assert response.status_code == 200
    data = response.json()
    assert data["status"] in {"ready", "degraded", "not_ready"}
    assert isinstance(data["steps"], list)
    assert isinstance(data["config"], dict)
    assert isinstance(data["missing"], list)
    assert "cp .env.example .env" in data["commands"]
    assert "scripts/doctor.sh" in data["commands"]
    assert "scripts/start.sh" in data["commands"]
    assert "curl /api/system/doctor" in data["commands"]


def test_api_admin_usage_and_run_index(monkeypatch, tmp_path):
    manager = RunManager(root=tmp_path / "runs")
    monkeypatch.setattr("app.main.get_run_manager", lambda: manager)

    created = manager.create_run(["086"], "世界杯数据推演", dry_run=True)
    rebuild_response = client.post("/api/admin/run-index/rebuild")
    assert rebuild_response.status_code == 200
    assert rebuild_response.json()["indexed"] >= 1

    index_response = client.get("/api/admin/run-index")
    assert index_response.status_code == 200
    assert index_response.json()["total_runs_indexed"] >= 1

    filtered_response = client.get("/api/runs", params={"status": "dry_run", "num": "086", "q": "世界杯"})
    assert filtered_response.status_code == 200
    assert any(item["run_id"] == created["run_id"] for item in filtered_response.json()["runs"])

    usage_response = client.get("/api/admin/usage")
    assert usage_response.status_code == 200
    assert "quota" in usage_response.json()


def test_api_odds_fetch_dry_run_returns_command():
    response = client.post(
        "/api/odds/fetch",
        json={"nums": "086 087,088", "dry_run": True, "out_path": "/tmp/odds.json"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["dry_run"] is True
    assert data["parsed_nums"] == ["086", "087", "088"]
    assert data["command"][0] == "python3"
    assert "fetch_sporttery.py" in data["command"][1]
    assert "--out" in data["command"]


def test_api_reports_build_dry_run_returns_command():
    response = client.post(
        "/api/reports/build",
        json={
            "odds_path": "/tmp/odds.json",
            "out_path": "/tmp/report.html",
            "title": "世界杯数据推演",
            "theme": "dark",
            "dry_run": True,
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert data["dry_run"] is True
    assert data["command"][0] == "python3"
    assert "gen_multi_market_report.py" in data["command"][1]
    assert "--theme" in data["command"]


def test_api_runs_create_list_and_detail_with_missing_report_404(monkeypatch, tmp_path):
    manager = RunManager(root=tmp_path / "runs")
    monkeypatch.setattr("app.main.get_run_manager", lambda: manager)

    create_response = client.post(
        "/api/runs",
        json={
            "nums": "086 087",
            "title": "世界杯数据推演",
            "theme": "dark",
            "dry_run": True,
        },
    )

    assert create_response.status_code == 200
    created = create_response.json()
    assert created["run_id"]
    assert created["status"] == "dry_run"

    list_response = client.get("/api/runs")
    assert list_response.status_code == 200
    runs = list_response.json()["runs"]
    assert any(item["run_id"] == created["run_id"] for item in runs)

    detail_response = client.get(f"/api/runs/{created['run_id']}")
    assert detail_response.status_code == 200
    assert detail_response.json()["run_id"] == created["run_id"]

    report_response = client.get(f"/runs/{created['run_id']}/report.html")
    assert report_response.status_code == 404


def test_api_runs_rejects_too_many_matches(monkeypatch, tmp_path):
    manager = RunManager(root=tmp_path / "runs")
    monkeypatch.setattr("app.main.get_run_manager", lambda: manager)

    response = client.post(
        "/api/runs",
        json={
            "nums": "001 002 003 004 005 006 007 008 009",
            "title": "世界杯数据推演",
            "theme": "dark",
            "dry_run": True,
        },
    )

    assert response.status_code == 422


def test_api_runs_rejects_invalid_theme(monkeypatch, tmp_path):
    manager = RunManager(root=tmp_path / "runs")
    monkeypatch.setattr("app.main.get_run_manager", lambda: manager)

    response = client.post(
        "/api/runs",
        json={
            "nums": "086",
            "title": "世界杯数据推演",
            "theme": "light",
            "dry_run": True,
        },
    )

    assert response.status_code == 422


def test_api_runs_create_real_flow_returns_report_url(monkeypatch, tmp_path):
    manager = RunManager(root=tmp_path / "runs")
    monkeypatch.setattr("app.main.get_run_manager", lambda: manager)

    def fake_fetch(self, nums, out=None, timeout=30):
        assert timeout == 11
        out.write_text('{"matches":{"086":{"主队":"巴西","客队":"德国","胜平负":{},"让球":{},"总进球":{},"比分波胆":{}}}}', encoding="utf-8")
        return {"ok": True, "command": ["fetch"], "stdout": "", "stderr": ""}

    def fake_report(self, odds_path, out_path, title, theme="dark", intel_path=None, timeout=30):
        assert timeout == 11
        out_path.write_text("<html><body>ok</body></html>", encoding="utf-8")
        return {"ok": True, "command": ["report"], "stdout": "", "stderr": ""}

    monkeypatch.setattr("app.run_manager.SportteryService.fetch_odds", fake_fetch)
    monkeypatch.setattr("app.run_manager.ReportService.generate_report_file", fake_report)

    response = client.post(
        "/api/runs",
        json={
            "nums": "086",
            "title": "世界杯数据推演",
            "theme": "dark",
            "dry_run": False,
            "timeout": 11,
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "succeeded"
    assert data["report_url"] == f"/runs/{data['run_id']}/report.html"
    assert data["odds_health"]["valid_count"] == 1
    assert data["artifacts"]["prediction_exists"] is True
    assert data["data_quality"]["grade"] == "A"
    prediction_response = client.get(f"/api/runs/{data['run_id']}/prediction")
    assert prediction_response.status_code == 200
    prediction = prediction_response.json()
    assert prediction["run_id"] == data["run_id"]
    assert prediction["data_quality"]["status"] == "publishable"


def test_api_runs_retry_returns_new_run(monkeypatch, tmp_path):
    manager = RunManager(root=tmp_path / "runs")
    monkeypatch.setattr(manager, "_start_worker", lambda: None)
    monkeypatch.setattr("app.main.get_run_manager", lambda: manager)
    original = manager.create_run(["086"], "世界杯数据推演", theme="dark", dry_run=True, timeout=13)
    run_dir = tmp_path / "runs" / original["run_id"]
    request = manager._read_json(run_dir / "request.json")
    request["dry_run"] = False
    request["background"] = False
    manager._write_json(run_dir / "request.json", request)
    log = manager._read_json(run_dir / "log.json")
    log["status"] = "failed"
    manager._write_json(run_dir / "log.json", log)

    response = client.post(f"/api/runs/{original['run_id']}/retry")

    assert response.status_code == 200
    data = response.json()
    assert data["run_id"] != original["run_id"]
    assert data["status"] == "queued"
    assert data["request"]["retry_of"] == original["run_id"]
    assert data["log"]["retry_of"] == original["run_id"]


def test_api_runs_retry_rejects_dry_run(monkeypatch, tmp_path):
    manager = RunManager(root=tmp_path / "runs")
    monkeypatch.setattr("app.main.get_run_manager", lambda: manager)
    original = manager.create_run(["086"], "世界杯数据推演", dry_run=True)

    response = client.post(f"/api/runs/{original['run_id']}/retry")

    assert response.status_code == 409
    assert "cannot retry" in response.json()["detail"]


def test_api_runs_cancel_queued_and_running(monkeypatch, tmp_path):
    manager = RunManager(root=tmp_path / "runs")
    monkeypatch.setattr("app.main.get_run_manager", lambda: manager)
    queued = manager.create_run(["086"], "世界杯数据推演", dry_run=True)
    queued_dir = tmp_path / "runs" / queued["run_id"]
    queued_log = manager._read_json(queued_dir / "log.json")
    queued_log["status"] = "queued"
    manager._write_json(queued_dir / "log.json", queued_log)

    queued_response = client.post(f"/api/runs/{queued['run_id']}/cancel")

    assert queued_response.status_code == 200
    assert queued_response.json()["status"] == "cancelled"

    running = manager.create_run(["091"], "世界杯数据推演", dry_run=True)
    running_dir = tmp_path / "runs" / running["run_id"]
    running_log = manager._read_json(running_dir / "log.json")
    running_log["status"] = "running_report"
    manager._write_json(running_dir / "log.json", running_log)

    running_response = client.post(f"/api/runs/{running['run_id']}/cancel")

    assert running_response.status_code == 200
    running_data = running_response.json()
    assert running_data["status"] == "running_report"
    assert running_data["log"]["cancel_requested"] is True
    assert "worker will stop before the next stage" in running_data["warning"]


def test_api_run_prediction_404_when_missing(monkeypatch, tmp_path):
    manager = RunManager(root=tmp_path / "runs")
    monkeypatch.setattr("app.main.get_run_manager", lambda: manager)
    created = manager.create_run(["086"], "世界杯数据推演", dry_run=True)

    response = client.get(f"/api/runs/{created['run_id']}/prediction")

    assert response.status_code == 404
    assert response.json()["detail"] == "prediction not found"


def test_run_report_file_returns_html_for_existing_report(monkeypatch, tmp_path):
    manager = RunManager(root=tmp_path / "runs")
    monkeypatch.setattr("app.main.get_run_manager", lambda: manager)
    run_dir = tmp_path / "runs" / "manual-run"
    run_dir.mkdir(parents=True)
    (run_dir / "request.json").write_text(
        '{"nums":["086"],"title":"世界杯数据推演","theme":"dark","dry_run":false,"created_at":"2026-07-05T00:00:00Z"}',
        encoding="utf-8",
    )
    (run_dir / "log.json").write_text('{"status":"succeeded"}', encoding="utf-8")
    (run_dir / "report.html").write_text("<html><body>report</body></html>", encoding="utf-8")

    response = client.get("/runs/manual-run/report.html")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/html")
    assert "report" in response.text


def test_api_odds_inspect_reads_tmp_odds_file(tmp_path):
    odds_path = tmp_path / "odds.json"
    odds_path.write_text('{"matches":{"091":{"主队":"巴西","客队":"德国"}}}', encoding="utf-8")

    response = client.post("/api/odds/inspect", json={"odds_path": str(odds_path)})

    assert response.status_code == 200
    data = response.json()
    assert data["ok"] is True
    assert data["valid_count"] == 1


def test_api_run_odds_health_returns_logged_health(monkeypatch, tmp_path):
    manager = RunManager(root=tmp_path / "runs")
    monkeypatch.setattr("app.main.get_run_manager", lambda: manager)
    run_dir = tmp_path / "runs" / "manual-health"
    run_dir.mkdir(parents=True)
    (run_dir / "request.json").write_text(
        '{"nums":["091"],"title":"世界杯数据推演","theme":"dark","dry_run":false,"created_at":"2026-07-05T00:00:00Z"}',
        encoding="utf-8",
    )
    (run_dir / "odds.json").write_text('{"matches":{"091":{"主队":"巴西","客队":"德国"}}}', encoding="utf-8")
    (run_dir / "log.json").write_text(
        '{"status":"succeeded","odds_health":{"ok":true,"total":1,"valid_count":1,"invalid_count":0,"valid_nums":["091"],"invalid":{},"markets":{},"summary":"已记录"}}',
        encoding="utf-8",
    )

    response = client.get("/api/runs/manual-health/odds-health")

    assert response.status_code == 200
    data = response.json()
    assert data["ok"] is True
    assert data["summary"] == "已记录"


def test_api_odds_discover_returns_health_without_creating_run(monkeypatch, tmp_path):
    manager = RunManager(root=tmp_path / "runs")
    monkeypatch.setattr("app.main.get_run_manager", lambda: manager)

    def fake_fetch(self, nums, out=None, timeout=30):
        assert nums == ["086", "091"]
        assert timeout == 9
        assert out is not None
        out.write_text(
            '{"matches":{"086":{"error":"未在受注列表中找到该编号"},"091":{"主队":"巴西","客队":"德国","胜平负":{}}}}',
            encoding="utf-8",
        )
        return {"ok": True, "command": ["fetch"], "stdout": "", "stderr": ""}

    monkeypatch.setattr("app.main.SportteryService.fetch_odds", fake_fetch)

    response = client.post("/api/odds/discover", json={"nums": "086 091", "timeout": 9})

    assert response.status_code == 200
    data = response.json()
    assert data["ok"] is True
    assert data["valid_nums"] == ["091"]
    assert data["invalid"] == {"086": "未在受注列表中找到该编号"}
    assert data["markets"]["091"]["has_spf"] is True
    assert data["summary"]
    assert manager.list_runs() == []



def test_api_odds_discover_preserves_raw_fetch_payload_outside_desktop(monkeypatch):
    def fake_fetch(self, nums, out=None, timeout=30):
        assert out is not None
        out.write_text('{"matches":{"086":{"主队":"巴西","客队":"德国","胜平负":{}}}}', encoding="utf-8")
        return {"ok": True, "returncode": 0, "command": ["fetch", "raw"], "stdout": "raw stdout", "stderr": "raw stderr"}

    monkeypatch.setattr("app.main.SportteryService.fetch_odds", fake_fetch)

    response = client.post("/api/odds/discover", json={"nums": "086"})

    assert response.status_code == 200
    assert response.json()["fetch"] == {
        "ok": True,
        "returncode": 0,
        "command": ["fetch", "raw"],
        "stdout": "raw stdout",
        "stderr": "raw stderr",
    }



def test_api_odds_discover_returns_structured_error_on_fetch_failure(monkeypatch):
    def fake_fetch(self, nums, out=None, timeout=30):
        return {"ok": False, "error": {"code": "script_unavailable", "message": "missing"}}

    monkeypatch.setattr("app.main.SportteryService.fetch_odds", fake_fetch)

    response = client.post("/api/odds/discover", json={"nums": ["086"]})

    assert response.status_code == 200
    data = response.json()
    assert data["ok"] is False
    assert data["error"]["code"] == "script_unavailable"
    assert data["valid_nums"] == []


def test_api_runs_phase8_queue_recover_failures_and_export(monkeypatch, tmp_path):
    manager = RunManager(root=tmp_path / "runs")
    monkeypatch.setattr(manager, "_start_workers", lambda: None)
    monkeypatch.setattr("app.main.get_run_manager", lambda: manager)

    queued = manager.create_run(["086"], "queued", dry_run=True)
    failed = manager.create_run(["087"], "failed", dry_run=True)
    failed_dir = tmp_path / "runs" / failed["run_id"]
    failed_log = manager._read_json(failed_dir / "log.json")
    failed_log["status"] = "running_report"
    manager._write_json(failed_dir / "log.json", failed_log)
    queued_dir = tmp_path / "runs" / queued["run_id"]
    queued_log = manager._read_json(queued_dir / "log.json")
    queued_log["status"] = "queued"
    manager._write_json(queued_dir / "log.json", queued_log)
    (queued_dir / "odds.json").write_text('{"matches":{}}', encoding="utf-8")

    recover_response = client.post("/api/runs/recover")
    assert recover_response.status_code == 200
    recover = recover_response.json()
    assert recover["recovered_run_ids"] == [queued["run_id"]]
    assert recover["marked_failed_run_ids"] == [failed["run_id"]]

    queue_response = client.get("/api/runs/queue")
    assert queue_response.status_code == 200
    queue_data = queue_response.json()
    assert queue_data["queued_count"] == 1
    assert queue_data["active_count"] == 0
    assert queue_data["queued_run_ids"] == [queued["run_id"]]

    failures_response = client.get("/api/runs/failures")
    assert failures_response.status_code == 200
    failures = failures_response.json()
    assert failures["counts"]["interrupted"] == 1
    assert failures["recent"][0]["run_id"] == failed["run_id"]
    assert failures["recent"][0]["category"] == "interrupted"

    export_response = client.get(f"/api/runs/{queued['run_id']}/export.zip")
    assert export_response.status_code == 200
    assert export_response.headers["content-type"].startswith("application/zip")
    export_path = tmp_path / "export.zip"
    export_path.write_bytes(export_response.content)
    with zipfile.ZipFile(export_path) as archive:
        assert {"manifest.json", "request.json", "log.json", "odds.json"}.issubset(set(archive.namelist()))


def test_startup_and_smoke_scripts_exist_and_are_executable():
    for script in ("scripts/start.sh", "scripts/smoke.sh", "scripts/doctor.sh", "scripts/package_release.sh", "scripts/external_trial_smoke.py"):
        path = Path(script)
        assert path.exists()
        assert os.access(path, os.X_OK)


def test_package_release_script_contains_secret_exclusions():
    script = Path("scripts/package_release.sh").read_text(encoding="utf-8")
    assert "data/app.db" in script
    assert "runs/" in script
    assert ".env" in script
    assert "EXTERNAL_TRIAL.md" in script


def test_external_trial_doc_documents_first_user_flow():
    doc = Path("EXTERNAL_TRIAL.md").read_text(encoding="utf-8")
    assert "首个真实外部用户试用流程" in doc
    assert "scripts/external_trial_smoke.py" in doc
    assert "WC_API_TOKEN" in doc


def test_consumer_flow_defaults_to_trial_dry_run_mode():
    script = Path("app/static/app.js").read_text(encoding="utf-8")
    assert "dry_run: trialMode" in script
    assert "background: !trialMode" in script
    assert "试用模式" in Path("app/templates/index.html").read_text(encoding="utf-8")
