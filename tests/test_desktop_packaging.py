from __future__ import annotations

import importlib
import json
import pathlib
import re
import runpy
import shlex
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
DESKTOP = ROOT / "desktop"
SRC_TAURI = DESKTOP / "src-tauri"

DISPLAY_NAME = "足球赛事 AI 推演引擎"
IDENTIFIER = "com.pitchmind.desktop"
PROHIBITED = ("FIFA", "World Cup", "世界杯")
SUPPORTED_TRIPLES = {
    "x86_64-pc-windows-msvc": "pitchmind-sidecar-x86_64-pc-windows-msvc.exe",
    "aarch64-apple-darwin": "pitchmind-sidecar-aarch64-apple-darwin",
    "x86_64-apple-darwin": "pitchmind-sidecar-x86_64-apple-darwin",
}


def read(path: pathlib.Path) -> str:
    return path.read_text(encoding="utf-8")


def test_required_desktop_foundation_files_exist() -> None:
    expected = [
        DESKTOP / "package.json",
        DESKTOP / "dist" / "index.html",
        DESKTOP / "sidecar_main.py",
        SRC_TAURI / "Cargo.toml",
        SRC_TAURI / "tauri.conf.json",
        SRC_TAURI / "build.rs",
        SRC_TAURI / "src" / "main.rs",
        SRC_TAURI / "capabilities" / "default.json",
        DESKTOP / "README.md",
        DESKTOP / "scripts" / "dev-sidecar.py",
        DESKTOP / "scripts" / "build_sidecar.py",
        DESKTOP / "scripts" / "verify_desktop_config.py",
    ]
    missing = [str(path.relative_to(ROOT)) for path in expected if not path.exists()]
    assert missing == []


def test_tauri_config_uses_unsigned_beta_single_owner_sidecar_fields() -> None:
    config = json.loads(read(SRC_TAURI / "tauri.conf.json"))

    assert config["productName"] == DISPLAY_NAME
    assert config["identifier"] == IDENTIFIER
    assert "tauri.app.v2.schema.json" in config["$schema"]
    assert config["build"]["frontendDist"] == "../dist"
    assert "beforeDevCommand" not in config["build"]
    assert "devUrl" not in config["build"]

    bundle = config["bundle"]
    assert bundle["active"] is True
    assert bundle["targets"] == ["dmg", "nsis"]
    assert bundle["externalBin"] == ["binaries/pitchmind-sidecar"]
    assert bundle.get("createUpdaterArtifacts") is False
    assert bundle["publisher"] == "PitchMind"
    assert bundle["shortDescription"] == DISPLAY_NAME
    assert bundle["longDescription"].startswith("Independent football match")
    assert bundle["windows"]["nsis"]["installMode"] == "currentUser"

    windows = config["app"]["windows"]
    assert windows == [{"title": DISPLAY_NAME, "width": 1280, "height": 860, "url": "index.html"}]
    assert "plugins" not in config or "updater" not in config.get("plugins", {})
    assert "allowlist" not in config
    assert "package" not in config


def test_no_prohibited_tournament_trademarks_in_desktop_config_or_packaging_metadata() -> None:
    metadata_files = [
        DESKTOP / "package.json",
        SRC_TAURI / "Cargo.toml",
        SRC_TAURI / "tauri.conf.json",
        SRC_TAURI / "capabilities" / "default.json",
    ]
    for path in metadata_files:
        text = read(path)
        for term in PROHIBITED:
            assert term not in text, f"{term!r} must not appear in {path.relative_to(ROOT)}"


def rust_function_body(source: str, name: str) -> str:
    match = re.search(rf"fn {name}\b[^{{]*{{", source)
    assert match is not None, f"missing Rust function {name}"
    depth = 1
    index = match.end()
    while index < len(source) and depth:
        if source[index] == "{":
            depth += 1
        elif source[index] == "}":
            depth -= 1
        index += 1
    assert depth == 0, f"unterminated Rust function {name}"
    return source[match.end(): index - 1]


def test_rust_sidecar_supervisor_is_async_single_owner_without_remote_config_url() -> None:
    main_rs = read(SRC_TAURI / "src" / "main.rs")
    assert ".sidecar(\"pitchmind-sidecar\")" in main_rs
    assert "TcpListener::bind(\"127.0.0.1:0\")" in main_rs
    assert ".env(\"WC_DESKTOP_MODE\", \"1\")" in main_rs
    assert ".env(\"WC_APP_DATA_DIR\"" in main_rs
    assert ".env(\"WC_HOST\", \"127.0.0.1\")" in main_rs
    assert ".env(\"PORT\"" in main_rs
    assert "/api/system/doctor" in main_rs
    assert "READY_TIMEOUT" in main_rs
    assert "wait_for_sidecar_ready" in main_rs
    assert "spawn_sidecar_worker" in main_rs
    assert "thread::spawn" in main_rs
    assert "ChildGuard" in main_rs
    assert "kill" in main_rs
    assert "http://127.0.0.1:" in main_rs
    assert "tauri_plugin_updater" not in main_rs
    assert "https://" not in main_rs
    setup_body = main_rs.split(".setup(|app|", 1)[1].split("Ok(())", 1)[0]
    assert "wait_for_sidecar_ready" not in setup_body


def test_rust_sidecar_readiness_requires_successful_doctor_json() -> None:
    main_rs = read(SRC_TAURI / "src" / "main.rs")
    readiness_body = rust_function_body(main_rs, "wait_for_sidecar_ready")
    doctor_body = rust_function_body(main_rs, "doctor_response_is_ready")

    assert "status != 200" in doctor_body
    assert "serde_json::from_reader" in doctor_body
    assert "DoctorReport" in main_rs
    assert "ok: bool" in main_rs
    assert 'status: Option<String>' in main_rs
    assert 'report.ok || report.status.as_deref() == Some("ready")' in doctor_body
    assert "200..500" not in readiness_body
    assert "200..400" not in readiness_body
    assert "return Ok(())" not in readiness_body.split("doctor_response_is_ready", 1)[0]


def test_dev_sidecar_invokes_existing_fastapi_app_with_explicit_localhost_data_dir() -> None:
    script = read(DESKTOP / "scripts" / "dev-sidecar.py")
    assert "app.main:app" in script
    assert "127.0.0.1" in script
    assert "WC_DESKTOP_MODE" in script
    assert "WC_APP_DATA_DIR" in script
    assert "--app-data-dir" in script
    assert "tempfile.TemporaryDirectory" in script
    assert "app/static/style.css" in script
    assert "styles.css" not in script


def test_sidecar_entrypoint_runs_uvicorn_app_module_with_validated_port() -> None:
    entrypoint = read(DESKTOP / "sidecar_main.py")
    assert "uvicorn.run" in entrypoint
    assert '"app.main:app"' in entrypoint
    assert "ensure_project_root_on_sys_path" in entrypoint
    assert "WC_HOST" in entrypoint
    assert "127.0.0.1" in entrypoint
    assert "PORT" in entrypoint
    assert "def parse_port" in entrypoint

    module = runpy.run_path(str(DESKTOP / "sidecar_main.py"), run_name="desktop_sidecar_test")
    assert module["ensure_project_root_on_sys_path"]() == ROOT
    assert module["parse_port"]("8765") == 8765
    assert module["parse_port"]("0") == 0
    for value in ("", "not-int", "70000", "-1"):
        try:
            module["parse_port"](value)
        except ValueError as exc:
            assert "PORT" in str(exc)
        else:  # pragma: no cover
            raise AssertionError(f"invalid PORT {value!r} must be rejected")


def test_build_sidecar_target_mapping_and_dry_run_contract() -> None:
    module = runpy.run_path(str(DESKTOP / "scripts" / "build_sidecar.py"))
    assert module["SUPPORTED_TARGETS"] == SUPPORTED_TRIPLES

    for triple, artifact in SUPPORTED_TRIPLES.items():
        command = module["build_pyinstaller_command"](target_triple=triple, project_root=ROOT)
        assert command[0] == "pyinstaller"
        path_values = [command[index + 1] for index, value in enumerate(command) if value == "--paths"]
        assert str(ROOT) in path_values
        assert "--name" in command
        assert artifact.removesuffix(".exe") in command
        assert str(DESKTOP / "sidecar_main.py") in command
        assert command[-1] == str(DESKTOP / "sidecar_main.py")
        assert "-m" not in command
        assert "app.main" not in command
        assert str(SRC_TAURI / "binaries") in command
        add_data_values = [command[index + 1] for index, value in enumerate(command) if value == "--add-data"]
        assert any("app/templates" in value for value in add_data_values)
        assert any("app/static" in value for value in add_data_values)
        demo_source, _demo_separator, demo_destination = next(
            value.rpartition(";" if triple.endswith("windows-msvc") else ":")
            for value in add_data_values
            if value.endswith((";" if triple.endswith("windows-msvc") else ":") + "data")
        )
        assert pathlib.Path(demo_source).name == "demo_matches.json"
        assert demo_destination == "data"
        assert any("app/main.py" in value for value in add_data_values)
        assert any("scripts/start.sh" in value for value in add_data_values)
        assert any("pyproject.toml" in value for value in add_data_values)

        for value in add_data_values:
            source, separator, destination = value.rpartition(";" if triple.endswith("windows-msvc") else ":")
            assert separator
            assert source
            assert destination
            wrong_separator = ":" if triple.endswith("windows-msvc") else ";"
            assert wrong_separator not in destination

    try:
        module["artifact_name_for_target"]("aarch64-pc-windows-msvc")
    except ValueError as exc:
        assert "Unsupported target triple" in str(exc)
    else:  # pragma: no cover
        raise AssertionError("unsupported target triple must be rejected")

    result = subprocess.run(
        [sys.executable, str(DESKTOP / "scripts" / "build_sidecar.py"), "--target", "x86_64-apple-darwin", "--dry-run"],
        cwd=ROOT,
        check=False,
        text=True,
        capture_output=True,
    )
    assert result.returncode == 0
    assert "pyinstaller" in result.stdout
    assert f"--paths {shlex.quote(str(ROOT))}" in result.stdout
    assert "pitchmind-sidecar-x86_64-apple-darwin" in result.stdout
    assert "desktop/sidecar_main.py" in result.stdout


def test_frozen_resource_paths_resolve_source_and_meipass(monkeypatch, tmp_path) -> None:
    import app.resources as resources

    resources = importlib.reload(resources)
    assert resources.resource_path("app", "static").resolve() == ROOT / "app" / "static"
    assert resources.resource_path("app", "templates").resolve() == ROOT / "app" / "templates"
    assert resources.resource_path("data", "demo_matches.json").resolve() == ROOT / "data" / "demo_matches.json"

    frozen_root = tmp_path / "bundle"
    monkeypatch.setattr(sys, "_MEIPASS", str(frozen_root), raising=False)
    assert resources.resource_path("app", "static") == frozen_root / "app" / "static"
    assert resources.resource_path("app", "templates") == frozen_root / "app" / "templates"
    assert resources.resource_path("data", "demo_matches.json") == frozen_root / "data" / "demo_matches.json"


def test_updater_scaffold_is_docs_only_and_readme_sets_runtime_boundaries() -> None:
    cargo = read(SRC_TAURI / "Cargo.toml")
    package_json = json.loads(read(DESKTOP / "package.json"))
    readme = read(DESKTOP / "README.md")
    config = json.loads(read(SRC_TAURI / "tauri.conf.json"))

    assert "tauri-plugin-updater" not in cargo
    assert "tauri_plugin_updater" not in read(SRC_TAURI / "src" / "main.rs")
    assert "plugins" not in config or "updater" not in config.get("plugins", {})
    assert config["bundle"].get("createUpdaterArtifacts") is False
    assert "updater" in readme.lower()
    assert "signed updater integration" in readme.lower()
    assert "no release/update publishing happens here" in readme.lower()
    assert "dependencies must be installed separately" in readme.lower()
    assert "npm install" not in package_json["scripts"].values()
    assert package_json["name"] == "pitchmind-desktop"


def test_verify_desktop_config_script_passes_contract_checks() -> None:
    result = subprocess.run(
        [sys.executable, str(DESKTOP / "scripts" / "verify_desktop_config.py")],
        cwd=ROOT,
        check=False,
        text=True,
        capture_output=True,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert re.search(r"desktop configuration verified", result.stdout, re.I)
