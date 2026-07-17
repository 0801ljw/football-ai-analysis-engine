# Phase 10 Task — External User Setup & Runtime Doctor

You are implementing Phase 10 for `/Users/ljw/projects/worldcup-ai-content-engine`.

## Goal
Move the product from a local developer MVP toward a product that another user can install, configure, diagnose, and run. Do NOT add social/content-generation features. Focus on external-user operability.

## Scope / constraints
- Edit only this project directory.
- Do not modify `~/.hermes/skills` or any runtime data outside this repo.
- Minimal changes; no unrelated refactor.
- No new third-party dependencies.
- Keep existing APIs backward compatible.
- Preserve compliance boundary: probability/data/research/risk wording only; no paid tips/follow-betting/profit promises.
- This project is not a git repo, so commands must not require git.

## Current state
Phase 9 is complete: runs can generate `prediction.json`, data quality, `/api/runs/{run_id}/prediction`, export zip includes prediction artifact.

## Required implementation

### 1. Runtime doctor module
Add a new module, suggested path:

```text
app/runtime_doctor.py
```

It should inspect the runtime environment without side effects and return a deterministic dict like:

```json
{
  "ok": true,
  "status": "ready | degraded | not_ready",
  "checks": [
    {
      "id": "python_version",
      "label": "Python version",
      "status": "pass | warn | fail",
      "summary": "...",
      "detail": {...}
    }
  ],
  "summary": "..."
}
```

Minimum checks:
- Python version is >= 3.11.
- Project root exists and expected files exist: `app/main.py`, `scripts/start.sh`, `scripts/smoke.sh`, `pyproject.toml`.
- Runs directory exists or can be created by app config path. The doctor itself should not create it; just report whether parent exists and target path.
- Config values from `get_settings()`: `skill_path`, `runs_path`, `max_run_matches`, `default_command_timeout`, `max_concurrent_runs`.
- Skill path exists / missing.
- Required skill scripts exist under skill path when skill path exists:
  - `scripts/fetch_sporttery.py`
  - `scripts/gen_multi_market_report.py`
- Shell scripts exist and are executable: `scripts/start.sh`, `scripts/smoke.sh`.
- Writable runs parent directory check. This can use `os.access(parent, os.W_OK)`; do not write test files.

Status rules:
- Any fail => `not_ready`, `ok=false`.
- No fail but at least one warn => `degraded`, `ok=true`.
- All pass => `ready`, `ok=true`.

Missing skill path should be `warn`, not `fail`, because demo fallback can still work. Missing project files/start scripts should be `fail`.

### 2. API endpoint
Add:

```text
GET /api/system/doctor
```

Returns the runtime doctor dict.

### 3. CLI / script entrypoint
Add a lightweight script:

```text
scripts/doctor.sh
```

It should:
- create/reuse `.venv` if needed only enough to run the app module, or use existing `.venv/bin/python` when present, otherwise `python3`.
- run a Python one-liner/module that prints the doctor JSON pretty-printed.
- exit 0 when doctor `ok=true`; exit 1 when `ok=false`.
- be executable.

Prefer a Python module-friendly design, e.g. `python -m app.runtime_doctor`, if clean.

### 4. Frontend
Minimal UI:
- Add a “系统体检 / Runtime doctor” panel or button.
- Button calls `/api/system/doctor` and renders JSON or a compact check list.
- Do not overbuild.

### 5. Docs
Update `README.md` and `PRODUCT_PLAN.md` with Phase 10:
- install/start/check commands for external users
- `scripts/doctor.sh`
- `/api/system/doctor`
- explain that missing Hermes skill degrades to demo fallback, not fatal.

### 6. Tests
Add/update tests for:
- runtime doctor ready/degraded/not_ready status logic if practical.
- `/api/system/doctor` returns expected shape.
- `scripts/doctor.sh` exists and is executable.
- Existing tests must still pass.

## Verification to run before finishing
Run:

```bash
.venv/bin/python -m pytest -q
.venv/bin/python -m pip check
bash -n scripts/start.sh scripts/smoke.sh scripts/doctor.sh
scripts/doctor.sh
```

Also run a small TestClient check for `/api/system/doctor` and print status.

## Completion report
Write a concise report to `/tmp/worldcup_phase10_report.md` with:
- files changed
- implemented endpoint/script
- test outputs
- limitations
