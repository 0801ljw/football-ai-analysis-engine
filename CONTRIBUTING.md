# Contributing to PitchMind

Thanks for helping improve PitchMind. The project is currently an unsigned desktop Beta, so small, reviewable changes are preferred.

## Before opening a change

- Search existing Issues first.
- For bugs, include the operating system, installer filename, steps to reproduce, expected result, and actual result.
- Never include API keys, tokens, `.env` files, local databases, `runs/` data, or private reports.
- Keep football-analysis claims measurable and avoid guarantees or betting-advice language.

## Local development

```bash
python3.11 -m venv .venv
.venv/bin/python -m pip install -e '.[dev]'
.venv/bin/python -m pytest -q
./scripts/start.sh
```

Desktop development commands are documented in [desktop/README.md](desktop/README.md). The full architecture and operations guide is in [docs/DEVELOPMENT.md](docs/DEVELOPMENT.md).

## Pull request checklist

- Keep the change narrowly scoped.
- Add or update tests for behavior changes.
- Run `pytest -q`, `pip check`, and `git diff --check`.
- Do not commit generated installers, local databases, secrets, or user run data.
- Update user-facing documentation when behavior or platform support changes.

By contributing, you confirm that you have the right to submit the work and that it does not contain private or third-party confidential information.
