#!/usr/bin/env bash
set -u

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

if [ ! -f ".env" ] && [ -f ".env.example" ]; then
  cp .env.example .env
  echo "Created .env from .env.example"
elif [ -f ".env" ]; then
  echo ".env already exists; leaving it unchanged"
else
  echo "No .env.example found; skipping .env creation"
fi

echo ""
echo "Next steps:"
echo "  1. Review .env and adjust WC_* values if needed."
echo "  2. Run scripts/doctor.sh to inspect readiness."
echo "  3. Run scripts/start.sh to start the app."
echo "  4. Open http://127.0.0.1:8787/ or curl /api/system/setup-guide."
echo ""

if [ -x "scripts/doctor.sh" ]; then
  echo "Running scripts/doctor.sh (degraded is allowed during first setup)..."
  scripts/doctor.sh || echo "doctor reported not_ready/degraded; fix the JSON diagnostics above and rerun when ready."
else
  echo "scripts/doctor.sh is not executable; skipping doctor."
fi
