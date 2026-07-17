Implement ONLY this small Phase 10 slice in this repo.

Create runtime doctor for external users.

Required:
1. Add app/runtime_doctor.py with build_runtime_report() returning dict {ok,status,checks,summary}. Also support `python -m app.runtime_doctor` printing pretty JSON and exiting 0 if ok else 1.
Checks:
- python_version pass if >=3.11 else fail
- expected files app/main.py scripts/start.sh scripts/smoke.sh pyproject.toml exist; missing fail
- config values from app.config.get_settings: skill_path, runs_path, max_run_matches, default_command_timeout, max_concurrent_runs
- skill_path exists: pass if exists, warn if missing
- if skill_path exists, required scripts scripts/fetch_sporttery.py and scripts/gen_multi_market_report.py pass/fail
- scripts/start.sh and scripts/smoke.sh executable pass/fail
- runs parent writable using os.access only; do not create files
Status: any fail => not_ready ok false; warn no fail => degraded ok true; all pass => ready ok true.

2. Add GET /api/system/doctor in app/main.py.
3. Add executable scripts/doctor.sh that uses .venv/bin/python if present else python3, runs `python -m app.runtime_doctor`.
4. Add minimal frontend button/panel calling /api/system/doctor and rendering JSON.
5. Add tests for build_runtime_report status shape, API endpoint, doctor.sh executable.
6. Update README.md and PRODUCT_PLAN.md Phase 10 docs.
7. Run pytest, pip check, bash -n scripts/start.sh scripts/smoke.sh scripts/doctor.sh, scripts/doctor.sh.
Write /tmp/worldcup_phase10_report.md.

Constraints: no new deps, no git, edit only this repo, minimal changes, no social/content features.