# Security Policy

## Supported releases

PitchMind is currently an unsigned Beta. Security fixes target the latest GitHub prerelease and the current `main` branch.

## Reporting a vulnerability

Please do not publish sensitive security details in a public Issue. Use GitHub's private vulnerability reporting feature when it is available for this repository. If it is unavailable, open a minimal Issue asking for a private contact channel without including exploit details.

Include:

- affected version or commit;
- operating system and architecture;
- concise reproduction steps;
- impact assessment;
- suggested mitigation, if known.

Never include real API keys, account tokens, `.env` files, databases, private reports, or user run artifacts.

## Beta security boundaries

- Installers are currently unsigned and may trigger Windows SmartScreen or macOS Gatekeeper.
- Download only from the official GitHub Releases page and verify `SHA256SUMS.txt`.
- PitchMind is designed for local-first use; treat all locally configured credentials as secrets.
- Automatic signed updates are not enabled in this Beta stage.
