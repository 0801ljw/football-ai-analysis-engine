# GitHub README i18n Design — 2026-07-13

Approved implementation scope:

- Use English as the default GitHub landing page in `README.md`.
- Provide native Markdown language links for English, Simplified Chinese, Japanese, and Korean at the top of every landing page.
- Keep the old developer-focused README unchanged in `docs/DEVELOPMENT.md` and link to it from all four landing pages.
- Add a local SVG hero image at `docs/assets/pitchmind-hero.svg`; no remote image dependencies.
- Present the desktop Beta clearly for ordinary users: release CTA, platform availability, quick start, privacy, unsigned Beta safety notice, compliance boundary, feedback, tech stack, and developer entry points.
- State platform support accurately for `desktop-beta-4`: Windows x64 available, macOS Apple Silicon available, macOS Intel not yet available.
- Do not claim code signing, automatic updates, telemetry, betting advice, or unsupported Intel macOS builds.

Validation is performed with a read-only Python script outside the repository.
