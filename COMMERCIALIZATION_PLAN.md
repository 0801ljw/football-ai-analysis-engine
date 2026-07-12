# Commercialization Completion Plan

> For Hermes: implement phase-by-phase with Codex/Claude Code doing code changes and Hermes independently verifying. Exclude 小红书/social-media content generation by user request.

**Goal:** Turn the current local V1 beta into a普通用户/商业化可用 product while preserving the existing local workflow and compliance guardrails.

**Architecture:** Keep the current FastAPI + Jinja2 + file artifact base. Add user-facing workflow first, then data trust surface, then SQLite indexing, then deploy/security/commercial controls. Avoid payment integration until product workflow is stable.

**Tech Stack:** FastAPI, Jinja2, vanilla JS/CSS, Python stdlib where possible, SQLite stdlib, pytest.

---

## Scope exclusions

- Do not build 小红书/社媒内容 generation/export in this commercial track.
- Do not add payment processing yet.
- Do not introduce external SaaS dependencies unless explicitly approved.

## Phase 12 — Consumer workflow UI

**Goal:** Replace the engineering-first homepage experience with a normal-user 3-step flow: select matches → generate → preview/export.

**Deliverables:**
- Add a prominent consumer workflow panel above advanced panels.
- Hide/visually demote dry-run/debug JSON panels under “高级工具”.
- Reuse existing `/api/odds/discover`, `/api/runs`, polling, preview, and export APIs.
- Add clear status copy and disabled states.
- Keep existing advanced tools working.

**Acceptance:**
- A non-technical user can use the top flow without touching raw JSON/API concepts.
- Tests cover homepage elements and workflow helpers.
- Existing 81 tests continue passing.

## Phase 13 — Data trust and source clarity ✅ Implemented

**Goal:** Productize data reliability: source, timestamp, missing markets, demo/fallback, and trust grade are visible before users trust a report.

**Deliverables:**
- Extend `prediction.json`/run detail surface with source metadata when available.
- Add user-facing “数据可信度” panel for each run.
- Show missing markets and limitation copy in plain Chinese.
- Distinguish `demo`, `snapshot`, `live-ish`/real script output.

**Acceptance:**
- Every generated result has a visible source/trust summary.
- Missing/partial odds are surfaced as warnings, not hidden in logs.

## Phase 14 — SQLite run index ✅ Implemented

**Goal:** Keep file artifacts, but add SQLite index for fast history/search/filter and future multi-user readiness.

**Deliverables:**
- Add stdlib SQLite DB under project data path, e.g. `data/app.db` or configurable `WC_DB_PATH`.
- Index run_id, nums, status, title, created_at, updated_at, data_quality grade/status, failure category, report/prediction existence.
- Backfill existing `runs/*` on startup or via script.
- API supports history filters: status, num, quality, text query.
- UI history filter/search.

**Acceptance:**
- File artifacts remain source of truth for content.
- SQLite index can be rebuilt from runs directory.
- Tests cover backfill and filtered list.

## Phase 15 — Deployment/distribution and security boundary ✅ Implemented

**Goal:** Make it installable and safe to run beyond the developer machine.

**Deliverables:**
- Dockerfile or documented local package flow.
- `.env.example` expanded with security knobs.
- Optional API token / local auth gate for non-localhost deployments.
- CORS/host binding documented and safe by default.
- Healthcheck endpoint/script for deployment.

**Acceptance:**
- Fresh checkout can run with documented commands.
- Non-local exposure requires explicit auth/config.
- Smoke test works in packaged mode.

## Phase 16 — Commercial foundation, no payments yet ✅ Implemented

**Goal:** Prepare for monetization without integrating payment provider.

**Deliverables:**
- SQLite-backed multi-user token accounts with role, plan and per-user quota.
- Configurable plan/quota model in local config/DB: free/pro/internal.
- Usage tracking: runs created, real fetches, exports.
- Admin/status page for usage and limits.
- Friendly quota exceeded errors.
- Audit log for real data fetch/report generation.

**Acceptance:**
- Can enforce quotas per user locally.
- Can later attach Stripe/支付 provider without rewriting run flow.

## Phase 17 — Polish and release checklist ✅ Implemented

**Goal:** Final product hardening.

**Deliverables:**
- Product copy pass: no gambling-sales phrasing, no guarantee language.
- Error state UX pass.
- Empty states and first-run onboarding.
- Release checklist and demo script.
- Final regression run and manual browser smoke.

**Acceptance:**
- Ordinary-user happy path is obvious.
- Failure states explain next action.
- Full test suite and smoke pass.
