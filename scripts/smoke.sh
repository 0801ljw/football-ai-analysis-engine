#!/usr/bin/env bash
set -euo pipefail

BASE_URL="${BASE_URL:-http://127.0.0.1:8787}"

curl -fsS "$BASE_URL/api/matches" >/dev/null
curl -fsS "$BASE_URL/api/skill/status" >/dev/null
curl -fsS -X POST "$BASE_URL/api/runs" \
  -H 'Content-Type: application/json' \
  -d '{"nums":"086","title":"世界杯数据推演报告","theme":"dark","dry_run":true}' >/dev/null
