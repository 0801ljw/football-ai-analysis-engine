# Desktop security and verification

This upgrade changes desktop transport and credential storage. Non-desktop
`WC_API_TOKEN` and existing multi-user authentication retain their behavior.

## Session boundary

The Rust host generates 32 random OS bytes per start. It writes the session token
to the child's stdin pipe; Python keeps it in memory. It is never placed in process
arguments, environment, URL, web storage, a response body, or a user configuration
file. The child binds loopback port 0 and retains the socket while Uvicorn serves
it. Only the actual port is returned over the child's stdout pipe. A bounded
startup wait and authenticated doctor check precede opening the workbench.

A document-start initialization script adds `X-Desktop-Session` only to same-origin
fetch requests. Requests carrying the session reject redirects. The workbench has
no native Tauri capabilities and is restricted to its own root-page navigation.
Reports are fetched with headers and rendered in script-free, opaque sandboxed
iframes; ZIP/prediction downloads also use authenticated fetches.

All desktop HTTP routes, including docs/OpenAPI, doctor, generated reports,
administration, settings, and run operations, require this session. The only public
resources are the GET/HEAD root shell (bundled demo content only, never a custom
`WC_DATA_PATH` dataset) and static assets. The workbench loads the configured
dataset afterward through the authenticated matches API. The public shell cannot bootstrap a
session. Direct external-browser desktop access is intentionally unsupported.
Host must be numeric `127.0.0.1:<port>`. Origin, if present, must exactly match it;
`null`, foreign origins and cross-site Fetch Metadata are rejected. Header-only
native clients can omit Origin but still need the session. No CORS allowance is
introduced. Missing bootstrap credentials fail closed.

This prevents unauthenticated local clients and hostile websites from invoking
protected desktop routes. It **does not defend against code running with the
same OS user's privileges**, debuggers/process-memory access, an already
compromised host/sidecar or same-origin script execution. The token remains
accessible to the trusted WebView runtime. Loopback HTTP is not TLS. OS account
separation and trusted local code remain necessary.

## System credentials and legacy migration

New API keys use explicitly selected `keyring.backends.macOS.Keyring` or
`keyring.backends.Windows.WinVaultKeyring`. No auto-selected backend, plaintext
fallback or Linux fallback is allowed. Unavailable/locked/denied native storage
returns a generic unavailable response. Storage is scoped by the resolved config
directory so development profiles do not collide with the production profile.
`WC_API_KEY_STORAGE_MODE=local_json` does not re-enable legacy writes.

In advanced desktop settings:

1. Choose **迁移旧版 Key** to copy the allowed provider's old JSON entry to the
   system store and verify readback. Conflicting native/legacy entries are blocked
   for manual resolution. A failed operation leaves the original file untouched.
2. The old plaintext remains present, and status explicitly says so. After the
   verified copy exists, **清理已验证的旧副本** asks for confirmation before
   atomically removing only that provider's old JSON entry. Other file data stays.
3. Save/delete never silently overwrite a different old key or leave a legacy
   credential looking deleted. Migrate and explicitly clean the old copy first.

No real user configuration was opened or migrated during development. Native
macOS storage was probed with a uniquely named synthetic credential only; that
synthetic entry was removed after readback. Unit tests use an injected memory
backend and temporary JSON files. Removing a legacy JSON entry is not secure
erasure of filesystem snapshots, backups or historical copies.

## Reproducible checks

`uv.lock` locks runtime, test, audit and optional sidecar build dependencies across
supported platforms. Install uv 0.11.25, then:

```sh
uv sync --locked --extra dev --extra audit
uv run --no-sync pytest -q
uv pip check
uv run --no-sync pip-audit --skip-editable
uv run --no-sync python desktop/scripts/verify_desktop_config.py
node --test desktop/scripts/test-session.mjs
node --check app/static/app.js
git diff --check
```

The push/PR CI uses read-only contents permission, SHA-pinned checkout/setup-uv,
Python 3.11/3.12 on Linux/Windows/macOS ARM, plus JS checks and a vulnerability
scan. It does not publish artifacts or releases, access repository secrets, or
exercise a real OS credential vault. Real vault acceptance is separate.
The existing manually triggered release workflow now installs the same locked
build environment; it is not triggered by this change.

For a local sidecar build use `uv sync --locked --extra dev --extra desktop-build`
and `uv run --no-sync python desktop/scripts/build_sidecar.py --target <triple>
--execute`. Do not use real production app-data when manually launching a host.

## Evaluation and release follow-up

The repository has demo data and prediction logic/tests, but does not contain the
102-entry raw ledger, the exact 86-sample filtering pipeline, timestamp provenance,
or the historical score reconstruction script required to reproduce the README's
figures. Those figures remain **not independently verified**. Historical score
reconstruction is not prospective validation. Next work requires the actual raw
artifacts and a frozen, timestamped holdout evaluation with baseline comparisons;
no performance data is manufactured here.

No repository security settings or permissions changed. Repository owners can
separately decide whether to enable available Dependabot updates, secret scanning
and push protection. No license is selected. The existing proprietary metadata is
not changed. This upgrade does not buy/import signing certificates, sign/notarize
an installer for distribution, publish a release, enable an updater, or merge main.

Remaining release gates: Windows Credential Manager real-vault tests, Intel macOS
native acceptance, Tauri/WebView interactive preview/export/save/migrate/restart
checks on each target, full installer acceptance, signing/notarization decisions,
and a signed update feed with version/rollback policy. Test matrices with mock
vaults do not replace these gates.

## Rollback

Review/revert the security and CI commits on the feature branch. Keep old JSON and
native vault entries intact. Reverting code does not migrate a vault entry back to
plaintext; reinstalling the old version may require manually re-entering a key.
Never bulk-delete configuration, vault entries, databases or run data to roll back.
