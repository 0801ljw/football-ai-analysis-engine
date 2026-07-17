# Phase 9 Task — Prediction Product Core

You are implementing Phase 9 for `/Users/ljw/projects/worldcup-ai-content-engine`.

## Goal
Turn the current HTML-report run workflow into a product-grade prediction core for external users by adding a structured `prediction.json` artifact and data quality grading. Do NOT implement XHS/social content generation.

## Scope / constraints
- Edit only this project directory.
- Do not modify `~/.hermes/skills` or any runtime data outside this repo.
- Minimal changes; no unrelated refactor.
- No new third-party dependencies.
- Keep existing APIs backward compatible.
- Preserve compliance boundary: product wording must stay as probability/data/research/risk, not paid tips/follow-betting/profit promises.

## Current architecture
- `app/run_manager.py` creates `runs/<run_id>/` with `request.json`, `log.json`, `odds.json`, `odds.valid.json`, `report.html`.
- `app/odds_health.py` checks valid/invalid odds matches.
- `app/main.py` exposes run APIs.
- `app/static/app.js`, `app/templates/index.html`, `app/static/style.css` implement front-end.
- Tests live in `tests/`.

## Required implementation

### 1. Add structured prediction artifact
Create a deterministic product artifact at:

```text
runs/<run_id>/prediction.json
```

For every successful real run that reaches report generation, write `prediction.json` after `odds.valid.json` is available. It can be derived from odds health + valid odds JSON + run request/log metadata. It does not need to parse model probabilities from HTML in this phase.

Minimum schema:

```json
{
  "schema_version": "1.0",
  "run_id": "...",
  "generated_at": "... ISO UTC ...",
  "source": {
    "odds_path": "...",
    "valid_odds_path": "...",
    "report_path": "...",
    "source_type": "sporttery_official_api"
  },
  "data_quality": {
    "grade": "A|B|C|D",
    "status": "publishable|internal_reference|insufficient",
    "score": 0-100,
    "summary": "中文摘要",
    "missing": ["..."],
    "signals": {
      "valid_match_count": 0,
      "invalid_match_count": 0,
      "has_1x2": true/false,
      "has_handicap": true/false,
      "has_total_goals": true/false,
      "has_correct_score": true/false,
      "has_half_full": true/false
    }
  },
  "matches": [
    {
      "num": "091",
      "home": "...",
      "away": "...",
      "markets": {
        "has_1x2": true/false,
        "has_handicap": true/false,
        "has_total_goals": true/false,
        "has_correct_score": true/false,
        "has_half_full": true/false
      },
      "data_quality": {
        "grade": "A|B|C|D",
        "missing": ["..."]
      }
    }
  ],
  "compliance": {
    "positioning": "体育数据推演与娱乐研究，不构成下注建议",
    "publish_blocked": false,
    "warnings": []
  }
}
```

Market detection should be robust to current Sporttery odds shape. Inspect keys heuristically. Use both Chinese and likely code keys if needed. Keep logic deterministic and tested.

Suggested grade logic:
- A: all matches valid, and aggregate has at least 4 of 5 market signals.
- B: all matches valid, and aggregate has at least 3 of 5 market signals.
- C: at least one valid match, but some invalid or only 1-2 market signals.
- D: no valid matches / insufficient.
Status:
- A/B => `publishable`
- C => `internal_reference`
- D => `insufficient`

### 2. Integrate into RunManager
- Add `prediction_path` to artifact paths/status where appropriate.
- In real successful/partial report flow, write prediction artifact.
- If no valid matches, do not fabricate prediction; log should mention prediction unavailable/insufficient if useful.
- Include `prediction.json` in `export_zip()` when present and in manifest files.
- Expose artifact presence in run list/detail responses consistently with existing artifact status pattern.

### 3. API endpoint
Add:

```text
GET /api/runs/{run_id}/prediction
```

Returns parsed `prediction.json` if present. 404 if missing.

### 4. Frontend
Minimal UI:
- For each run, show data quality grade/status if available from run summary/detail.
- For current result panel, add a link/button to view/download prediction JSON if present.
- Do not overbuild.

### 5. Docs
Update `README.md` and `PRODUCT_PLAN.md` with Phase 9: structured prediction artifact + data quality grading.

### 6. Tests
Add/update tests for:
- prediction artifact generation from a valid real run path using monkeypatch/fakes (do not require network).
- data quality grades A/B/C/D if practical.
- `GET /api/runs/{run_id}/prediction` success and 404.
- export zip includes `prediction.json` when present.
- existing tests must still pass.

## Verification to run before finishing
Run:

```bash
.venv/bin/python -m pytest -q
.venv/bin/python -m pip check
bash -n scripts/start.sh scripts/smoke.sh
```

Also run a small TestClient or direct RunManager smoke proving export zip contains `prediction.json` for a fake successful run.

## Completion report
Write a concise report to `/tmp/worldcup_phase9_report.md` with:
- files changed
- implemented endpoints/artifacts
- test outputs
- any limitations
