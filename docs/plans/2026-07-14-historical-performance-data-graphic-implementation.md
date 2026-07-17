# Historical Performance Data Graphic Implementation Plan

> **For Hermes:** Execute directly with narrow verification; this is a static documentation asset change.

**Goal:** Add a branded historical-performance chart to the multilingual GitHub landing pages.

**Architecture:** Use one self-contained SVG shared by all README languages. Keep existing Markdown tables below it as the accessible and auditable source representation.

**Tech Stack:** SVG, Markdown, Chrome headless rendering, Python XML validation.

---

### Task 1: Add the static data graphic

**Files:**
- Create: `docs/assets/pitchmind-performance.svg`

**Steps:**
1. Encode the three aggregate metrics and six selected Top 1 examples.
2. Use a 1280 × 760 brand-consistent dashboard layout.
3. Parse the file with Python `xml.etree.ElementTree`.

### Task 2: Integrate into multilingual landing pages

**Files:**
- Modify: `README.md`
- Modify: `docs/i18n/README.zh-CN.md`
- Modify: `docs/i18n/README.ja.md`
- Modify: `docs/i18n/README.ko.md`

**Steps:**
1. Add one image reference after each historical-results introduction.
2. Use localized alt text.
3. Resolve every relative asset path and assert the file exists.

### Task 3: Verify visual and repository quality

**Steps:**
1. Render the SVG at exactly 1280 × 760 with Chrome headless.
2. Inspect all KPIs, match cards, labels, bars, and disclaimers.
3. Run `git diff --check`.
4. Review `git diff --stat` and `git status --short`.
5. Do not commit or push without explicit user approval.
