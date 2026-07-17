[English](README.md) / [简体中文](docs/i18n/README.zh-CN.md) / [日本語](docs/i18n/README.ja.md) / [한국어](docs/i18n/README.ko.md)

# PitchMind — Football AI Analysis Engine

![PitchMind hero cover](docs/assets/pitchmind-hero.png)

**PitchMind turns football match research into a local-first desktop workflow: collect match context, generate AI-assisted analysis, review evidence, and export reports without sending your private tokens or local run data to a hosted product.**

[Download public Beta 4](https://github.com/0801ljw/football-ai-analysis-engine/releases/tag/desktop-beta-4) · [Product tour](#product-tour) · [Developer docs](docs/DEVELOPMENT.md)

> Compliance boundary: PitchMind is for research, learning, and entertainment. It is not betting advice, financial advice, or a promise of match outcomes.

## Available desktop Beta

**Latest public prerelease:** [`desktop-beta-4`](https://github.com/0801ljw/football-ai-analysis-engine/releases/tag/desktop-beta-4)

**Latest automated CI draft:** `desktop-beta-8` proves the draft-release automation path, but is not the normal public download entry.

| Platform | Status | Public Beta 4 asset |
| --- | --- | --- |
| Windows x64 | Available | `PitchMind-Setup-x64.exe` |
| macOS Apple Silicon | Available | `PitchMind-macOS-AppleSilicon.dmg` |
| macOS Intel | Available | `PitchMind-macOS-Intel.dmg` |

The Beta is unsigned. Your operating system may show a security warning during installation. Only download from the official GitHub Release above, verify the asset name and checksum when available, and do not install files from mirrors or reuploads.

## Product tour

![PitchMind product tour](docs/assets/pitchmind-product-tour.png)

## Start in 3 steps

1. Open the [`desktop-beta-4` release page](https://github.com/0801ljw/football-ai-analysis-engine/releases/tag/desktop-beta-4) and download the installer for your platform.
2. Install and launch PitchMind. Because this is an unsigned Beta, approve the operating-system warning only if the file came from the official release page.
3. Create a local run, review the data-quality notes, inspect the report, and export artifacts if you need to share your research.

## Core capabilities

| Area | What PitchMind helps with |
| --- | --- |
| Match research | Organize football match numbers, data-source status, and analysis runs in one local workspace. |
| AI-assisted reports | Generate structured football analysis reports with evidence notes, prediction JSON when available, and compliance reminders. |
| Run history and export | Review previous runs, statuses, report artifacts, and exportable outputs. |
| Local-first privacy | Keep configuration, tokens, local databases, and generated run files on your own machine. |
| Safety boundaries | Make unsigned-Beta status and research-only usage clear in the product workflow. |

## Verified historical results

The figures below are reconstructed from 102 raw ledger entries, filtered to 86 clean pre-match samples. 1X2 accuracy uses the clean set. Exact-score Top 3 coverage is rebuilt from historical `lh`/`la` values with the current `score_matrix` scoring method. These are model-evaluation evidence, not a promise of future performance.

![PitchMind verified historical performance dashboard](docs/assets/pitchmind-performance.svg)

| Evaluation set | Result |
| --- | ---: |
| Raw ledger entries | 102 matches |
| Clean pre-match samples | 86 matches |
| 1X2 direction accuracy | **64/86 (74.4%)** |
| Exact-score Top 3 coverage | **33/86 (38.4%)** |

Selected exact-score hits from reports saved before kickoff:

| Match | Pre-match model scores | Final score | Match |
| --- | --- | ---: | --- |
| Argentina vs Austria | **2-0** / 1-0 / 3-0 | **2-0** | Top 1 |
| France vs Iraq | **3-0** / 2-0 / 4-0 | **3-0** | Top 1 |
| Brazil vs Haiti | **3-0** / 4-0 / 5-0 | **3-0** | Top 1 |
| France vs Sweden | **3-0** / 4-0 / 2-0 | **3-0** | Top 1 |
| United States vs Bosnia and Herzegovina | **2-0** / 3-0 / 2-1 | **2-0** | Top 1 |
| Portugal vs Croatia | **2-1** / 1-1 / 3-1 | **2-1** | Top 1 |
| Spain vs Austria | 2-0 / **3-0** / 1-0 | **3-0** | Top 3 |
| Switzerland vs Algeria | 1-1 / 2-1 / **2-0** | **2-0** | Top 3 |

These are selected successful examples. The aggregate rates above include both hits and misses and are the relevant baseline for evaluating the engine.

## Release quality evidence

| Evidence | Status |
| --- | --- |
| Automated test suite | 146 tests passing for the release-quality gate. |
| Native desktop CI | Windows x64, macOS Apple Silicon, and macOS Intel release jobs produce platform installers. |
| Release artifacts | Public Beta 4 provides the three installers, `SHA256SUMS.txt`, install notes, and the allowlisted `worldcup-ai-content-engine-source.tar.gz` source package. |
| Local-first boundary | No claim of cloud sync, remote telemetry, or automatic signed updates in this unsigned Beta stage. |

## Privacy and unsigned-Beta safety

- PitchMind is intended to run locally on your computer.
- Do not send API tokens, account tokens, `.env` files, local databases, or run artifacts when asking for support.
- Browser or desktop token inputs are for your local workflow. Treat tokens as secrets.
- The current desktop Beta is not code-signed and does not claim automatic updates. If you are uncomfortable with unsigned preview software, wait for a signed release.

## Feedback

Please report bugs, installation problems, and usability feedback in [GitHub Issues](https://github.com/0801ljw/football-ai-analysis-engine/issues). Include your operating system, the downloaded asset name, and a description of what happened. Do not include tokens or private local data.

## Technology and developers

| Layer | Stack |
| --- | --- |
| Desktop shell | Tauri |
| Local web app | FastAPI, Jinja2 |
| Frontend assets | HTML, CSS, JavaScript |
| Runtime and tooling | Python, SQLite, PyInstaller sidecar, release packaging scripts |
| Release target | GitHub Releases, manual unsigned Beta distribution |

Developer entry points:

- [Developer documentation](docs/DEVELOPMENT.md)
- [Desktop Beta install notes](desktop/INSTALL_BETA.md)
- [Release checklist](RELEASE_CHECKLIST.md)
- [Desktop source README](desktop/README.md)

## Legal and compliance reminder

PitchMind provides football data research, probability-style exploration, and content-production assistance for entertainment and study. It does not provide betting advice, guaranteed predictions, or instructions to place wagers. Always follow your local laws and platform rules.
