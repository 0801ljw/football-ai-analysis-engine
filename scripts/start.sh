#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

if [ -f ".env" ]; then
  set -a
  # shellcheck disable=SC1091
  . ".env"
  set +a
fi

if [ ! -x ".venv/bin/python" ]; then
  python3 -m venv .venv
fi

if [ "${WC_HOST:-127.0.0.1}" != "127.0.0.1" ] && [ "${WC_HOST:-127.0.0.1}" != "localhost" ] && [ "${WC_HOST:-127.0.0.1}" != "::1" ] && [ -z "${WC_API_TOKEN:-}" ]; then
  echo "Refusing non-local WC_HOST=${WC_HOST:-} without WC_API_TOKEN. Set WC_API_TOKEN or bind to 127.0.0.1." >&2
  exit 1
fi

if ! .venv/bin/python - <<'PY' >/dev/null 2>&1
import fastapi
import uvicorn
PY
then
  .venv/bin/python -m pip install -e '.[dev]'
fi

exec .venv/bin/python -m uvicorn app.main:app --host "${WC_HOST:-127.0.0.1}" --port "${PORT:-8787}"
