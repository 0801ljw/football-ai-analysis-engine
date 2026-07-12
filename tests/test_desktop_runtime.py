from pathlib import Path

from app.desktop_runtime import initialize_user_data


def test_initialize_user_data_creates_required_desktop_dirs(tmp_path):
    app_data_dir = tmp_path / "PitchMind"

    paths = initialize_user_data(app_data_dir)

    assert paths.app_data_dir == app_data_dir
    assert paths.runs_path == app_data_dir / "runs"
    assert paths.config_path == app_data_dir / "config"
    assert paths.logs_path == app_data_dir / "logs"
    assert paths.db_path == app_data_dir / "data" / "app.db"
    assert paths.runs_path.is_dir()
    assert paths.config_path.is_dir()
    assert paths.logs_path.is_dir()
    assert paths.db_path.parent.is_dir()
