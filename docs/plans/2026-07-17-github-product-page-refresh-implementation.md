# PitchMind GitHub Product Page Refresh Implementation Plan

> **For Hermes:** Execute task-by-task with independent verification; do not overwrite existing uncommitted README/history-dashboard work.

**Goal:** Deliver a polished four-language GitHub product landing page with real product screenshots, truthful release status, auditable metrics, community files, repository cleanup, and verified GitHub metadata.

**Architecture:** Treat `README.md` and three localized READMEs as product landing pages sharing assets under `docs/assets/`. Capture real application states from a disposable local app-data directory. Keep public prerelease and automated Draft status distinct. Move internal phase documents without deleting history.

**Tech Stack:** Markdown, SVG/PNG, FastAPI/Jinja2, Chrome headless screenshots, Python validators, Git/GitHub CLI.

---

### Task 1: Audit authoritative state

**Files:** Read release API, ledger, local README diffs, existing assets and root files.

1. Record Beta 4 and Beta 8 status/assets.
2. Recompute or invalidate historical metrics from authoritative sources.
3. Inventory uncommitted files and preserve them.
4. Define exact move map for root documents.

### Task 2: Capture real product states

**Files:** Create `docs/assets/product-tour/` PNG files only.

1. Start the app with isolated temporary `WC_APP_DATA_DIR`/DB and localhost port.
2. Verify `/`, `/api/matches`, and Demo generation.
3. Capture main workbench at 1440×900.
4. Generate a real Demo report and capture report detail.
5. Capture recent report/export state after successful generation.
6. Stop service and verify no process remains.

### Task 3: Build visual assets

**Files:**
- Update/create `docs/assets/pitchmind-performance.svg`
- Create `docs/assets/pitchmind-product-tour.png`
- Create `docs/assets/pitchmind-social-preview.png`
- Keep/refine existing hero assets as needed

1. Use only verified screenshots and metrics.
2. Apply one consistent deep-blue frame and typography system.
3. Parse SVG as XML and render all assets in Chrome.
4. Verify dimensions, clipping and text legibility.

### Task 4: Rewrite four landing pages

**Files:**
- `README.md`
- `docs/i18n/README.zh-CN.md`
- `docs/i18n/README.ja.md`
- `docs/i18n/README.ko.md`

1. Put CTA and three-platform availability above the fold.
2. Add Product Tour with three real screenshots.
3. Distinguish public Beta 4 from automated Draft Beta 8.
4. Add verified release/build evidence.
5. Add updated historical metrics only when auditable.
6. Reduce repetitive unsigned warnings while preserving safety guidance.
7. Keep developer links and compliance boundary.

### Task 5: Repository hygiene and community files

**Files:**
- Move root phase/task/trial documents to `docs/archive/development-phases/`
- Create `.github/ISSUE_TEMPLATE/bug_report.yml`
- Create `.github/ISSUE_TEMPLATE/feature_request.yml`
- Create `CONTRIBUTING.md`
- Create `SECURITY.md`

1. Move files with `git mv`; do not delete content.
2. Update any links referencing moved files.
3. Include explicit no-secret reporting guidance.
4. Do not add LICENSE without user authorization.

### Task 6: Deterministic verification

1. Resolve every relative Markdown link in all four READMEs.
2. Assert all language pages contain identical platform statuses and release URLs.
3. Assert product image dimensions and shared asset paths.
4. Assert aggregate metrics and selected-example labels.
5. Run `pytest -q`, `pip check`, desktop config verifier, `py_compile`, secret/compliance scans, and `git diff --check`.
6. Browser-render the GitHub-style README preview or local Markdown rendering at desktop and mobile widths.
7. Review final diff/stat and ensure unrelated uncommitted work is preserved or deliberately included.

### Task 7: Publish after final verification

1. Stage only approved files.
2. Commit with clear docs/product-page message.
3. Push `main` only after full verification evidence.
4. Set GitHub Topics and Homepage.
5. Upload/set Social Preview if supported by authenticated GitHub API; otherwise report exact manual blocker.
6. Read back README, About metadata, assets, links and Release status from GitHub.
