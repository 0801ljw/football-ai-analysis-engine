Implement Phase 11 minimal config externalization + first-start guide in this repo only.

Goals:
1. Remove hardcoded user-specific default skill path in app/config.py. Use env-configurable settings with safe defaults.
2. Add `.env.example` documenting config.
3. Add first-start guide endpoint/script so external users know how to configure and run.

Required details:
- app/config.py:
  - Settings still dataclass.
  - get_settings reads environment variables (no new deps):
    WC_APP_NAME, WC_DATA_PATH, WC_RUNS_PATH, WC_SKILL_PATH, WC_MAX_RUN_MATCHES, WC_MAX_CONCURRENT_RUNS, WC_DEFAULT_COMMAND_TIMEOUT.
  - Defaults:
    app_name = current Chinese app name
    data_path = ROOT_DIR/data/demo_matches.json
    runs_path = ROOT_DIR/runs
    skill_path = Path.home()/.hermes/skills/leisure/worldcup2026-betting-analyst
    ints same current defaults.
  - expanduser for path env values. Keep backward-compatible attributes.
  - Invalid integer env should fall back to default, not crash.

- Add app/setup_guide.py:
  - build_setup_guide(settings=None) returns dict with status, steps, config, missing, commands.
  - It should explain missing skill path is not fatal: demo fallback works, real mode needs skill scripts.
  - Include commands: cp .env.example .env, scripts/doctor.sh, scripts/start.sh, curl /api/system/doctor.

- Add API endpoint in app/main.py:
  GET /api/system/setup-guide

- Add scripts/setup.sh executable:
  - If .env missing and .env.example exists, copy it.
  - Print next steps.
  - Run scripts/doctor.sh if executable; do not fail hard if doctor reports degraded.

- Update scripts/start.sh and scripts/doctor.sh to source .env if present before running Python.

- Minimal frontend: add setup guide button/panel calling /api/system/setup-guide and rendering JSON/steps.

- Docs: README.md and PRODUCT_PLAN.md Phase 11 mention env variables, .env.example, setup.sh, setup-guide endpoint.

- Tests:
  - config env override and invalid int fallback.
  - setup guide endpoint shape.
  - scripts/setup.sh exists executable.
  - Existing tests pass.

Verification:
.venv/bin/python -m pytest -q
.venv/bin/python -m pip check
bash -n scripts/start.sh scripts/smoke.sh scripts/doctor.sh scripts/setup.sh
scripts/doctor.sh
python - <<'PY'
from fastapi.testclient import TestClient
from app.main import app
c=TestClient(app)
print('SETUP', c.get('/api/system/setup-guide').status_code, c.get('/api/system/setup-guide').json()['status'])
PY

Write /tmp/worldcup_phase11_report.md with files changed, test outputs, limitations.
Constraints: no new deps, no git, edit only this repo, no social/content features.