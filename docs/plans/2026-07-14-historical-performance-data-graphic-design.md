# Historical Performance Data Graphic Design

**Goal:** Replace the text-only historical results presentation with a GitHub-renderable brand data graphic while preserving the underlying tables for accessibility and auditability.

## Visual direction

- Deep-blue PitchMind technology dashboard, consistent with `pitchmind-hero.svg`.
- One self-contained SVG at `docs/assets/pitchmind-performance.svg`.
- Canvas: 1280 × 760, responsive through the SVG `viewBox`.
- No external fonts, scripts, images, or network dependencies.

## Information architecture

1. Header: “VERIFIED HISTORICAL PERFORMANCE” and a short provenance label.
2. KPI row:
   - 84 clean pre-match samples.
   - 73.8% 1X2 direction accuracy, with a proportional 62/84 bar.
   - 39.3% exact-score Top 3 coverage, with a proportional 33/84 bar.
3. Highlight grid: six selected Top 1 exact-score hits, each showing matchup, pre-match Top 3, and final score.
4. Footer disclaimer: selected examples; aggregate metrics include hits and misses; historical performance is not a promise of future outcomes.

## README integration

- Insert the SVG immediately below the introductory paragraph of the historical-results section in all four README languages.
- Use language-appropriate alt text.
- Keep the aggregate metric table and match table below the graphic as the canonical accessible text representation.

## Verification

- Parse the SVG as XML.
- Confirm all required metrics and six match cards are present.
- Rasterize with macOS Quick Look and visually inspect the PNG.
- Run `git diff --check` and validate all four README links resolve to the same asset.

## Scope boundary

- No changes to prediction data, model code, application UI, or release artifacts.
- No commit or push without explicit user approval.
