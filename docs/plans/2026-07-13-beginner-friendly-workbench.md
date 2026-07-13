# Beginner-friendly workbench implementation plan

> **For Hermes:** Use subagent-driven-development to implement this plan with strict RED → GREEN verification.

**Goal:** Replace the crowded homepage with a C-style split workbench that includes A-style onboarding and B-style status summaries without changing backend APIs.

**Architecture:** Keep FastAPI/Jinja and vanilla CSS/JS. Restructure `index.html`, add presentation-only CSS, and minimally adapt existing JS selectors/rendering so the current endpoints and forms continue to work. All developer/admin features remain under one collapsed advanced section.

**Tech Stack:** FastAPI, Jinja2, vanilla JavaScript, vanilla CSS, pytest, Tauri 2 desktop wrapper.

---

### Task 1: Lock the homepage information architecture with a failing regression test

**Files:**
- Modify: `tests/test_app_smoke.py`

**Steps:**
1. Add a focused test asserting the new navigation, three status summaries, onboarding stepper, split workbench, Demo CTA, plain-language modes, recent-report empty state, and single advanced section.
2. Assert technical concepts (`X-API-Token`, Skill status, Runtime doctor, Admin) occur only after the advanced-tools boundary.
3. Run the focused test and record expected RED caused by missing new markup.

**Command:**
```bash
.venv/bin/python -m pytest -q tests/test_app_smoke.py::<new_test>
```

### Task 2: Implement the approved C+A+B Jinja structure

**Files:**
- Modify: `app/templates/index.html`

**Steps:**
1. Replace the theme-heavy hero with compact brand/navigation and status strip.
2. Build the three-step onboarding bar.
3. Recompose existing consumer discover/run/results into a 5/7 split workbench.
4. Reuse the existing `runs-list` as the right-column recent report area.
5. Move auth, desktop data source, doctor, setup, skill, Admin and raw tools into one advanced `<details>`.
6. Preserve all IDs needed by `app.js` and all forms/endpoints.
7. Run focused test to GREEN.

### Task 3: Add the visual system and responsive behavior

**Files:**
- Modify: `app/static/style.css`

**Steps:**
1. Add scoped workbench-v2 tokens and component styles.
2. Use warm gray + navy + teal, strong hierarchy and restrained surfaces.
3. Ensure 1366×768 first-screen usability and 390px single-column fallback.
4. Add hover/pressed/focus-visible and reduced-motion handling.
5. Do not add external assets, fonts or dependencies.

### Task 4: Adapt JS for onboarding, Demo and summary status

**Files:**
- Modify: `app/static/app.js`
- Modify: `tests/test_app_smoke.py` if behavioral assertions are needed

**Steps:**
1. Add one-click Demo behavior using existing consumer forms and dry-run flow.
2. Update stepper based on discover/run progress.
3. Derive current-task and recent-report summaries from existing run data.
4. Keep existing endpoint and auth behavior unchanged.
5. Add/extend tests and verify RED→GREEN for new JS contract markers.

### Task 5: Integration verification

**Commands:**
```bash
.venv/bin/python -m pytest -q
.venv/bin/python -m pip check
.venv/bin/python desktop/scripts/verify_desktop_config.py
node --check app/static/app.js
```

**Browser acceptance:**
1. Start a local isolated server using a temporary DB/data path.
2. Validate desktop viewport 1366×768 and mobile viewport 390px.
3. Check no page-level horizontal overflow and no console errors.
4. Exercise Demo → generate → result/recent report flow.
5. Capture screenshots as evidence.

### Task 6: Package and release only after explicit verification

**Files:** no source changes expected.

**Steps:**
1. Commit the verified UI change locally.
2. Push only because the user explicitly approved execution; do not publish a new Release until build artifacts are verified.
3. Trigger the manual desktop workflow.
4. Verify Windows x64 installer and macOS Apple Silicon DMG; do not claim macOS Intel without an artifact.
5. Publish/replace Beta assets only after checksum and platform checks.
