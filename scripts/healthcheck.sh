#!/usr/bin/env bash
set -euo pipefail
BASE_URL="${BASE_URL:-http://127.0.0.1:${PORT:-8787}}"
curl -fsS "$BASE_URL/api/system/doctor" >/dev/null
