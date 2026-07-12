Implement Phase 12 consumer workflow UI in this repo only.

Goal: make the homepage usable by ordinary users without touching raw JSON/API panels.

Scope:
- Keep existing APIs and advanced panels working.
- Do NOT add social-media/XHS content features.
- No new dependencies.
- No git/commit.

Required UX:
1. Add a top-level consumer workflow section near top of app/templates/index.html:
   - Title: “三步生成赛前报告”
   - Step 1: enter match nums, with default "086 087 088"
   - Button: “检查可用场次” calling POST /api/odds/discover
   - Show valid/invalid nums in plain Chinese, with checkboxes for valid nums.
   - Step 2: title/theme/timeout settings and button “生成报告” that calls POST /api/runs with dry_run=false, background=true.
   - Step 3: progress/status, report preview/open link, export zip link, prediction.json link when available.
   - User-facing copy must avoid betting-sales language and must say reports are probability/data research, not guarantees.

2. Advanced tools:
   - Wrap existing engineering/debug panels (generate JSON, Skill 状态, doctor, setup guide, odds dry-run, report dry-run, raw API preview) under a <details> or visually separate “高级工具” section.
   - Existing Create Run and Available Match Check panels may remain, but consumer workflow should be clearly primary.

3. app/static/app.js:
   - Add separate consumer workflow handlers; reuse existing helpers postJson/getJson/renderHealth/renderDataQuality/renderProgress/exportLink/predictionLink/previewButton where possible.
   - Poll background run until terminal.
   - Do not break existing run/discover handlers.

4. app/static/style.css:
   - Add simple styling for consumer workflow: steps/cards, selected nums, primary CTA, warning/copy blocks.

5. Tests:
   - Update/add tests in tests/test_app_smoke.py to assert homepage contains “三步生成赛前报告”, “高级工具”, and consumer control IDs.
   - Add any lightweight tests needed for no-regression.

Verification to run:
.venv/bin/python -m pytest -q
.venv/bin/python -m pip check
bash -n scripts/start.sh scripts/smoke.sh scripts/doctor.sh scripts/setup.sh
node --check app/static/app.js
scripts/doctor.sh

Also start the app and smoke manually if possible:
- scripts/start.sh
- scripts/smoke.sh
- GET / should contain the consumer workflow title

Write /tmp/worldcup_phase12_report.md with:
- files changed
- summary
- exact verification outputs
- limitations.
