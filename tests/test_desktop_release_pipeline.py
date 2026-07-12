from __future__ import annotations

import ast
import json
import os
import pathlib
import re
import struct
import subprocess
import sys
import tarfile
import zlib

try:
    import yaml
except ModuleNotFoundError:  # pragma: no cover - CI/dev env has PyYAML via pytest deps if needed
    yaml = None

ROOT = pathlib.Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github" / "workflows" / "desktop-release.yml"
INSTALL_BETA = ROOT / "desktop" / "INSTALL_BETA.md"
PACKAGE_SOURCE_SCRIPT = ROOT / "scripts" / "package_desktop_source.py"
PACKAGE_DESKTOP_SCRIPT = ROOT / "desktop" / "scripts" / "package_desktop_release.py"
RELEASE_NOTES_SCRIPT = ROOT / "scripts" / "create_release_notes.py"
CHECKSUM_SCRIPT = ROOT / "scripts" / "write_checksums.py"
VERIFY_DMG_LAYOUT_SCRIPT = ROOT / "desktop" / "scripts" / "verify_dmg_layout.py"
TAURI_CONFIG = ROOT / "desktop" / "src-tauri" / "tauri.conf.json"
TAURI_ICON = ROOT / "desktop" / "src-tauri" / "icons" / "icon.png"
TAURI_WINDOWS_ICON = ROOT / "desktop" / "src-tauri" / "icons" / "icon.ico"
GITIGNORE = ROOT / ".gitignore"
EXPECTED_APP_BUNDLE = "足球赛事 AI 推演引擎.app"
EXPECTED_MATRIX = {
    ("windows-latest", "x86_64-pc-windows-msvc", "nsis"),
    ("macos-14", "aarch64-apple-darwin", "dmg"),
    ("macos-13", "x86_64-apple-darwin", "dmg"),
}
EXPECTED_RELEASE_FILENAMES = {
    "足球赛事AI推演引擎-Setup-x64.exe",
    "足球赛事AI推演引擎-macOS-AppleSilicon.dmg",
    "足球赛事AI推演引擎-macOS-Intel.dmg",
}
FORBIDDEN_RELEASE_TERMS = ("FIFA", "World Cup", "世界杯")
FORBIDDEN_PACKAGE_PATHS = (
    ".env",
    "data/app.db",
    "runs/",
    "desktop/src-tauri/target/",
    "desktop/src-tauri/binaries/",
    "desktop/build/",
    "dist/worldcup",
)


def read(path: pathlib.Path) -> str:
    return path.read_text(encoding="utf-8")


def parse_png_rgba_payload(path: pathlib.Path) -> tuple[int, int, bytes]:
    data = path.read_bytes()
    assert data.startswith(b"\x89PNG\r\n\x1a\n"), "icon must start with a PNG signature"
    pos = 8
    width = height = color_type = bit_depth = None
    idat = bytearray()
    while pos + 12 <= len(data):
        chunk_len = struct.unpack(">I", data[pos : pos + 4])[0]
        chunk_type = data[pos + 4 : pos + 8]
        chunk_data_start = pos + 8
        chunk_data_end = chunk_data_start + chunk_len
        chunk_crc_end = chunk_data_end + 4
        assert chunk_crc_end <= len(data), f"truncated PNG chunk {chunk_type!r}"
        chunk_data = data[chunk_data_start:chunk_data_end]
        expected_crc = struct.unpack(">I", data[chunk_data_end:chunk_crc_end])[0]
        actual_crc = zlib.crc32(chunk_type + chunk_data) & 0xFFFFFFFF
        assert actual_crc == expected_crc, f"bad CRC for PNG chunk {chunk_type!r}"
        pos = chunk_crc_end
        if chunk_type == b"IHDR":
            width, height, bit_depth, color_type, compression, png_filter, interlace = struct.unpack(
                ">IIBBBBB", chunk_data
            )
            assert (compression, png_filter, interlace) == (0, 0, 0)
        elif chunk_type == b"IDAT":
            idat.extend(chunk_data)
        elif chunk_type == b"IEND":
            break
    assert pos == len(data), "PNG must not contain trailing or malformed chunk bytes"
    assert width is not None and height is not None, "PNG must include IHDR"
    assert bit_depth == 8 and color_type == 6, "icon must be 8-bit RGBA PNG"
    return width, height, zlib.decompress(bytes(idat))


def parse_ico_directory(path: pathlib.Path) -> list[tuple[int, int, int, int]]:
    data = path.read_bytes()
    assert len(data) > 6, "Windows icon must be non-empty"
    reserved, icon_type, count = struct.unpack_from("<HHH", data, 0)
    assert (reserved, icon_type) == (0, 1), "Windows icon must be an ICO file"
    assert count >= 2, "Windows icon must contain multiple sizes for Tauri Windows resources"
    entries = []
    for index in range(count):
        offset = 6 + index * 16
        width_raw, height_raw, colors, _reserved, planes, bit_count, size, image_offset = struct.unpack_from(
            "<BBBBHHII", data, offset
        )
        width = 256 if width_raw == 0 else width_raw
        height = 256 if height_raw == 0 else height_raw
        assert colors == 0
        assert planes in (0, 1)
        assert bit_count in (0, 32)
        assert image_offset + size <= len(data), "ICO image payload must be within the file"
        assert data[image_offset : image_offset + 8] == b"\x89PNG\r\n\x1a\n", "ICO payloads must be PNG images"
        entries.append((width, height, bit_count, size))
    return entries


def load_workflow() -> dict:
    assert WORKFLOW.exists(), "desktop release workflow source must exist"
    assert yaml is not None, "PyYAML is required by tests to inspect workflow source"
    return yaml.safe_load(read(WORKFLOW))


def test_tauri_desktop_icon_is_valid_opaque_rgba_png_and_configured() -> None:
    width, height, payload = parse_png_rgba_payload(TAURI_ICON)
    assert width >= 32 and height >= 32
    row_stride = 1 + width * 4
    assert len(payload) == row_stride * height, "RGBA payload must match PNG dimensions"
    pixels = []
    alphas = []
    for row in range(height):
        row_start = row * row_stride
        assert payload[row_start] == 0, "icon rows must use PNG filter type 0 for deterministic validation"
        for col in range(width):
            rgba_start = row_start + 1 + col * 4
            red, green, blue, alpha = payload[rgba_start : rgba_start + 4]
            pixels.append((red, green, blue, alpha))
            alphas.append(alpha)
    assert all(alpha == 255 for alpha in alphas), "icon must be fully opaque for desktop packaging"
    assert len(set(pixels)) > 1, "icon must contain non-empty pixel artwork, not a blank image"

    config = json.loads(read(TAURI_CONFIG))
    assert config["bundle"]["icon"] == ["icons/icon.png", "icons/icon.ico"]
    assert config["bundle"]["windows"]["nsis"]["installerIcon"] == "icons/icon.ico"


def test_tauri_windows_icon_is_valid_multi_size_ico_for_resource_build() -> None:
    entries = parse_ico_directory(TAURI_WINDOWS_ICON)
    sizes = {(width, height) for width, height, _bits, _size in entries}
    assert {(16, 16), (32, 32), (64, 64)} <= sizes


def test_release_workflow_is_manual_native_three_platform_draft_only() -> None:
    workflow = load_workflow()
    assert workflow["name"] == "Desktop Draft Release"
    assert workflow[True] == {"workflow_dispatch": {}}
    assert "push" not in workflow[True]
    assert "pull_request" not in workflow[True]
    assert workflow["permissions"] == {"contents": "write"}

    job = workflow["jobs"]["desktop-release"]
    rows = job["strategy"]["matrix"]["include"]
    matrix = {(row["os"], row["target"], row["bundle"]) for row in rows}
    assert matrix == EXPECTED_MATRIX
    bundle_dirs = {row["target"]: row["bundle_dir"] for row in rows}
    assert bundle_dirs == {
        "x86_64-pc-windows-msvc": "desktop/src-tauri/target/x86_64-pc-windows-msvc/release/bundle/nsis",
        "aarch64-apple-darwin": "desktop/src-tauri/target/aarch64-apple-darwin/release/bundle/dmg",
        "x86_64-apple-darwin": "desktop/src-tauri/target/x86_64-apple-darwin/release/bundle/dmg",
    }
    assert job["runs-on"] == "${{ matrix.os }}"

    release_job = workflow["jobs"]["draft-release"]
    assert release_job["needs"] == ["desktop-release", "source-package"]
    assert release_job["if"] == "github.event_name == 'workflow_dispatch'"
    release_text = json.dumps(release_job, ensure_ascii=False)
    assert "draft: true" in release_text or '"draft": true' in release_text
    assert "prerelease: true" in release_text or '"prerelease": true' in release_text
    assert "make_latest: false" in release_text or '"make_latest": false' in release_text
    assert "softprops/action-gh-release@v3" in release_text
    assert "gh release create" not in release_text


def test_release_workflow_builds_sidecar_before_tauri_with_cross_platform_python() -> None:
    text = read(WORKFLOW)
    for action in [
        "actions/checkout@v7",
        "actions/setup-python@v6",
        "actions/setup-node@v6",
        "actions/upload-artifact@v7",
        "actions/download-artifact@v8",
        "softprops/action-gh-release@v3",
    ]:
        assert action in text
    assert "python-version: '3.11'" in text
    assert "node-version: '22'" in text
    assert ".venv/bin" not in text
    assert ".venv\\Scripts" not in text
    assert "python -m venv" not in text
    assert "python -m pip install -e '.[dev]' pyinstaller" in text
    assert "python -m pytest -q" in text
    assert "python -m pip check" in text
    assert "python desktop/scripts/build_sidecar.py --target ${{ matrix.target }} --execute" in text
    assert "python desktop/scripts/verify_desktop_config.py" in text
    assert "npm ci" in text
    assert "npm install" not in text
    assert "dtolnay/rust-toolchain@stable" in text
    assert "targets: ${{ matrix.target }}" in text
    assert "npm run tauri:build -- --target ${{ matrix.target }} --bundles ${{ matrix.bundle }}" in text
    assert "Verify DMG artifact exists; mounted layout is checked locally" in text
    assert "python desktop/scripts/verify_dmg_layout.py --dmg" in text
    assert "--skip-mount" in text
    assert "Mounted layout acceptance is performed locally" in text
    assert "command -v hdiutil" not in text
    assert "--require-hdiutil" not in text
    assert "--skip-mount-if-hdiutil-unavailable" not in text
    assert "${{ matrix.bundle == 'dmg' }}" in text
    assert text.index("npm run tauri:build") < text.index("verify_dmg_layout.py --dmg")
    assert text.index("verify_dmg_layout.py --dmg") < text.index("package_desktop_release.py")
    assert text.index("build_sidecar.py --target") < text.index("npm run tauri:build")
    assert "desktop/src-tauri/binaries/pitchmind-sidecar-${{ matrix.target }}" in text
    assert "if-no-files-found: error" in text


def test_desktop_installer_packager_normalizes_platform_filenames_and_docs(tmp_path: pathlib.Path) -> None:
    script = read(PACKAGE_DESKTOP_SCRIPT)
    for expected in EXPECTED_RELEASE_FILENAMES:
        assert expected in script
    assert "INSTALL_BETA.md" in script
    assert "copy2" in script

    cases = [
        ("x86_64-pc-windows-msvc", "nsis", "runner-output.exe", "足球赛事AI推演引擎-Setup-x64.exe"),
        ("aarch64-apple-darwin", "dmg", "runner-output.dmg", "足球赛事AI推演引擎-macOS-AppleSilicon.dmg"),
        ("x86_64-apple-darwin", "dmg", "runner-output.dmg", "足球赛事AI推演引擎-macOS-Intel.dmg"),
    ]
    for target, bundle, raw_name, expected_name in cases:
        bundle_dir = tmp_path / target / "bundle"
        bundle_dir.mkdir(parents=True)
        (bundle_dir / raw_name).write_bytes(f"binary {target}".encode())
        out_dir = tmp_path / "out" / target
        result = subprocess.run(
            [
                sys.executable,
                str(PACKAGE_DESKTOP_SCRIPT),
                "--bundle-dir",
                str(bundle_dir),
                "--target",
                target,
                "--bundle",
                bundle,
                "--output-dir",
                str(out_dir),
            ],
            cwd=ROOT,
            encoding="utf-8",
            errors="replace",
            capture_output=True,
            check=False,
            env={**os.environ, "PYTHONIOENCODING": "cp1252"},
        )
        assert result.returncode == 0, result.stdout + result.stderr
        assert (out_dir / expected_name).read_bytes() == f"binary {target}".encode()
        assert (out_dir / "INSTALL_BETA.md").exists()
        assert sorted(p.name for p in out_dir.iterdir()) == ["INSTALL_BETA.md", expected_name]

    ambiguous_dir = tmp_path / "ambiguous"
    ambiguous_dir.mkdir()
    (ambiguous_dir / "one.exe").write_bytes(b"1")
    (ambiguous_dir / "two.exe").write_bytes(b"2")
    blocked = subprocess.run(
        [
            sys.executable,
            str(PACKAGE_DESKTOP_SCRIPT),
            "--bundle-dir",
            str(ambiguous_dir),
            "--target",
            "x86_64-pc-windows-msvc",
            "--bundle",
            "nsis",
            "--output-dir",
            str(tmp_path / "bad"),
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    assert blocked.returncode != 0
    assert "Expected exactly one" in blocked.stderr


def test_dmg_layout_verifier_requires_app_bundle_root_and_rejects_bare_contents(
    tmp_path: pathlib.Path,
) -> None:
    assert VERIFY_DMG_LAYOUT_SCRIPT.exists()
    good_root = tmp_path / "good-dmg-root"
    app_contents = good_root / EXPECTED_APP_BUNDLE / "Contents"
    app_contents.mkdir(parents=True)
    (app_contents / "Info.plist").write_text("plist", encoding="utf-8")
    (good_root / "Applications").symlink_to("/Applications")

    good = subprocess.run(
        [sys.executable, str(VERIFY_DMG_LAYOUT_SCRIPT), "--mounted-root", str(good_root)],
        cwd=ROOT,
        encoding="utf-8",
        errors="replace",
        capture_output=True,
        check=False,
    )
    assert good.returncode == 0, good.stdout + good.stderr
    assert EXPECTED_APP_BUNDLE in good.stdout

    bad_root = tmp_path / "bad-dmg-root"
    (bad_root / "Contents").mkdir(parents=True)
    bad = subprocess.run(
        [sys.executable, str(VERIFY_DMG_LAYOUT_SCRIPT), "--mounted-root", str(bad_root)],
        cwd=ROOT,
        encoding="utf-8",
        errors="replace",
        capture_output=True,
        check=False,
    )
    assert bad.returncode != 0
    assert "bare Contents" in bad.stderr

    extra_root = tmp_path / "extra-dmg-root"
    extra_contents = extra_root / EXPECTED_APP_BUNDLE / "Contents"
    extra_contents.mkdir(parents=True)
    (extra_contents / "Info.plist").write_text("plist", encoding="utf-8")
    (extra_root / "README.txt").write_text("unexpected", encoding="utf-8")
    extra = subprocess.run(
        [sys.executable, str(VERIFY_DMG_LAYOUT_SCRIPT), "--mounted-root", str(extra_root)],
        cwd=ROOT,
        encoding="utf-8",
        errors="replace",
        capture_output=True,
        check=False,
    )
    assert extra.returncode != 0
    assert "unexpected visible item" in extra.stderr


def test_dmg_layout_verifier_handles_chinese_output_under_cp1252_stdout(
    tmp_path: pathlib.Path,
) -> None:
    good_root = tmp_path / "good-dmg-root"
    app_contents = good_root / EXPECTED_APP_BUNDLE / "Contents"
    app_contents.mkdir(parents=True)
    (app_contents / "Info.plist").write_text("plist", encoding="utf-8")

    result = subprocess.run(
        [sys.executable, str(VERIFY_DMG_LAYOUT_SCRIPT), "--mounted-root", str(good_root)],
        cwd=ROOT,
        encoding="utf-8",
        errors="replace",
        capture_output=True,
        check=False,
        env={**os.environ, "PYTHONIOENCODING": "cp1252"},
    )

    assert result.returncode == 0, result.stdout + result.stderr
    assert EXPECTED_APP_BUNDLE in result.stdout


def test_dmg_verifier_can_structure_check_without_hdiutil_and_keeps_strict_mode(tmp_path: pathlib.Path) -> None:
    dmg = tmp_path / "artifact.dmg"
    dmg.write_bytes(b"not a real dmg but enough for CI artifact existence checks")

    tolerant = subprocess.run(
        [sys.executable, str(VERIFY_DMG_LAYOUT_SCRIPT), "--dmg", str(dmg), "--skip-mount-if-hdiutil-unavailable"],
        cwd=ROOT,
        encoding="utf-8",
        errors="replace",
        capture_output=True,
        check=False,
        env={**os.environ, "PATH": str(tmp_path)},
    )
    assert tolerant.returncode == 0, tolerant.stdout + tolerant.stderr
    assert "skipped mounted layout verification" in tolerant.stdout
    assert "hdiutil" in tolerant.stdout

    strict = subprocess.run(
        [sys.executable, str(VERIFY_DMG_LAYOUT_SCRIPT), "--dmg", str(dmg), "--require-hdiutil"],
        cwd=ROOT,
        encoding="utf-8",
        errors="replace",
        capture_output=True,
        check=False,
        env={**os.environ, "PATH": str(tmp_path)},
    )
    assert strict.returncode != 0
    assert "hdiutil is not available" in strict.stderr

    explicit_skip = subprocess.run(
        [sys.executable, str(VERIFY_DMG_LAYOUT_SCRIPT), "--dmg", str(dmg), "--skip-mount"],
        cwd=ROOT,
        encoding="utf-8",
        errors="replace",
        capture_output=True,
        check=False,
    )
    assert explicit_skip.returncode == 0, explicit_skip.stdout + explicit_skip.stderr
    assert "explicitly skipped" in explicit_skip.stdout


def test_workflow_dmg_step_keeps_single_artifact_check_and_defers_mount_to_local_acceptance() -> None:
    workflow = load_workflow()
    steps = workflow["jobs"]["desktop-release"]["steps"]
    step = next(item for item in steps if item.get("name") == "Verify DMG artifact exists; mounted layout is checked locally")
    script = step["run"]

    assert step["if"] == "${{ matrix.bundle == 'dmg' }}"
    assert "dmg_count=$(find" in script
    assert 'test "$dmg_count" = "1"' in script
    assert "--skip-mount" in script
    assert "Mounted layout acceptance is performed locally" in script
    assert "command -v hdiutil" not in script
    assert "--require-hdiutil" not in script
    assert "--skip-mount-if-hdiutil-unavailable" not in script


def test_gitignore_tracks_only_required_tauri_static_loading_ui() -> None:
    result = subprocess.run(
        ["git", "check-ignore", "-v", "--no-index", "desktop/dist/index.html"],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    assert "!desktop/dist/index.html" in result.stdout


def test_release_aggregation_merges_artifacts_generates_checksums_and_notes() -> None:
    text = read(WORKFLOW)
    assert "merge-multiple: true" in text
    assert "release-assets" in text
    assert "python scripts/write_checksums.py release-assets/* --output release-assets/SHA256SUMS.txt" in text
    assert "python scripts/create_release_notes.py --assets-dir release-assets --output release-assets/RELEASE_NOTES.md" in text
    assert "files: release-assets/*" in text
    assert "release-assets/**/*" not in text

    notes_script = read(RELEASE_NOTES_SCRIPT)
    assert "SHA256SUMS.txt" in notes_script
    assert "INSTALL_BETA.md" in notes_script
    assert "sorted" in notes_script


def test_checksum_script_is_deterministic_and_secret_guarded(tmp_path: pathlib.Path) -> None:
    script = read(CHECKSUM_SCRIPT)
    assert "hashlib.sha256" in script
    assert "sorted" in script
    assert "FORBIDDEN_PARTS" in script

    good = tmp_path / "artifact.dmg"
    good.write_bytes(b"beta artifact")
    result = subprocess.run(
        [sys.executable, str(CHECKSUM_SCRIPT), str(good), "--output", str(tmp_path / "SHA256SUMS.txt")],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    sums = read(tmp_path / "SHA256SUMS.txt")
    assert re.fullmatch(r"[0-9a-f]{64}  artifact\.dmg\n", sums)

    secret = tmp_path / ".env"
    secret.write_text("API_KEY=secret", encoding="utf-8")
    blocked = subprocess.run(
        [sys.executable, str(CHECKSUM_SCRIPT), str(secret)],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    assert blocked.returncode != 0
    assert "Refusing" in blocked.stderr


def test_desktop_source_package_script_uses_allowlist_and_product_neutral_deterministic_name(tmp_path: pathlib.Path) -> None:
    script = read(PACKAGE_SOURCE_SCRIPT)
    assert "ALLOWLIST" in script
    for forbidden in FORBIDDEN_PACKAGE_PATHS:
        assert forbidden in script
    assert "git archive" not in script
    assert "worldcup-ai-content-engine-source.tar.gz" in script

    out_dir = tmp_path / "out"
    result = subprocess.run(
        [sys.executable, str(PACKAGE_SOURCE_SCRIPT), "--output-dir", str(out_dir), "--deterministic-name"],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    archive = out_dir / "worldcup-ai-content-engine-source.tar.gz"
    checksum = out_dir / "worldcup-ai-content-engine-source.tar.gz.sha256"
    assert archive.exists()
    assert checksum.exists()
    with tarfile.open(archive, "r:gz") as tar:
        names = tar.getnames()
    assert "worldcup-ai-content-engine-source/README.md" in names
    assert "worldcup-ai-content-engine-source/desktop/INSTALL_BETA.md" in names
    joined = "\n".join(names)
    for forbidden in FORBIDDEN_PACKAGE_PATHS:
        assert forbidden not in joined


def test_release_notes_generator_lists_expected_assets(tmp_path: pathlib.Path) -> None:
    assets = tmp_path / "release-assets"
    assets.mkdir()
    for name in sorted(EXPECTED_RELEASE_FILENAMES | {"worldcup-ai-content-engine-source.tar.gz", "INSTALL_BETA.md", "SHA256SUMS.txt"}):
        (assets / name).write_text(f"{name}\n", encoding="utf-8")
    output = assets / "RELEASE_NOTES.md"
    result = subprocess.run(
        [sys.executable, str(RELEASE_NOTES_SCRIPT), "--assets-dir", str(assets), "--output", str(output)],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    notes = read(output)
    assert "Desktop unsigned Beta" in notes
    assert "Draft GitHub Release" in notes
    assert "SHA256SUMS.txt" in notes
    assert "INSTALL_BETA.md" in notes
    for name in EXPECTED_RELEASE_FILENAMES:
        assert name in notes


def test_unsigned_beta_docs_are_chinese_manual_github_release_only_and_honest() -> None:
    text = read(INSTALL_BETA)
    assert "足球赛事 AI 推演引擎" in text
    assert "PitchMind" in text
    assert "GitHub Release" in text
    assert "只从" in text or "仅从" in text
    assert "不要通过聊天" in text and "密钥" in text
    assert "Windows SmartScreen" in text
    assert "macOS Gatekeeper" in text
    assert "未签名" in text
    assert "手动下载" in text and "自动更新" in text
    assert "暂未启用" in text or "尚未启用" in text
    assert "CI 构建" in text and "不是本地生成" in text
    assert "诊断" in text and "错误" in text
    for term in FORBIDDEN_RELEASE_TERMS:
        assert term not in text


def test_readme_release_checklist_and_gitignore_document_desktop_release_boundaries() -> None:
    readme = read(ROOT / "README.md")
    checklist = read(ROOT / "RELEASE_CHECKLIST.md")
    gitignore = read(GITIGNORE)

    assert "Desktop unsigned Beta" in readme
    assert "Draft GitHub Release" in readme
    assert "manual GitHub Release update" in readme
    assert "automatic signed updater is later" in readme
    assert "worldcup-ai-content-engine-source.tar.gz" in readme
    assert "PitchMind" in readme

    assert "Desktop Draft Release" in checklist
    assert "workflow_dispatch" in checklist
    assert "draft" in checklist.lower()
    assert "不要发布公开 Release" in checklist
    assert "pip check" in checklist
    assert "desktop/scripts/verify_desktop_config.py" in checklist
    assert "worldcup-ai-content-engine-source.tar.gz" in checklist

    for pattern in [
        ".env",
        "data/app.db",
        "runs/",
        ".desktop-data/",
        "desktop/release-out/",
        "desktop/src-tauri/gen/",
        "desktop/src-tauri/target/",
        "desktop/src-tauri/binaries/",
        "desktop/build/",
        "dist/",
        "*.key",
        "*.p12",
    ]:
        assert pattern in gitignore
    assert "desktop/package-lock.json" not in gitignore
