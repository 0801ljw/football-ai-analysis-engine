#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

VERSION="${VERSION:-$(python3 - <<'PY'
from pathlib import Path
import re
text = Path('pyproject.toml').read_text(encoding='utf-8')
match = re.search(r'^version\s*=\s*"([^"]+)"', text, re.M)
print(match.group(1) if match else '0.0.0')
PY
)}"
STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
NAME="worldcup-ai-content-engine-v${VERSION}-${STAMP}"
DIST_DIR="${DIST_DIR:-dist}"
OUT_DIR="$DIST_DIR/$NAME"
ARCHIVE="$DIST_DIR/${NAME}.tar.gz"
SHA_FILE="${ARCHIVE}.sha256"
MANIFEST="$OUT_DIR/PACKAGE_MANIFEST.txt"

rm -rf "$OUT_DIR"
mkdir -p "$OUT_DIR" "$DIST_DIR"

copy_if_exists() {
  local item="$1"
  if [ -e "$item" ]; then
    mkdir -p "$OUT_DIR/$(dirname "$item")"
    cp -R "$item" "$OUT_DIR/$item"
  fi
}

for item in \
  app \
  data/demo_matches.json \
  scripts \
  tests \
  pyproject.toml \
  README.md \
  PRODUCT_PLAN.md \
  COMMERCIALIZATION_PLAN.md \
  RELEASE_CHECKLIST.md \
  EXTERNAL_TRIAL.md \
  Dockerfile \
  .env.example; do
  copy_if_exists "$item"
done

find "$OUT_DIR" -type d -name '__pycache__' -prune -exec rm -rf {} +
find "$OUT_DIR" -type f \( -name '*.pyc' -o -name '.DS_Store' \) -delete
rm -f "$OUT_DIR/data/app.db" "$OUT_DIR/.env"
rm -rf "$OUT_DIR/runs" "$OUT_DIR/dist" "$OUT_DIR/.pytest_cache"

cat > "$MANIFEST" <<EOF
Package: $NAME
Created: $STAMP
Version: $VERSION

Included:
- app/ FastAPI product code
- data/demo_matches.json demo fallback data
- scripts/ setup/start/doctor/smoke/package/external-trial utilities
- tests/ pytest verification suite
- README.md, PRODUCT_PLAN.md, COMMERCIALIZATION_PLAN.md, RELEASE_CHECKLIST.md, EXTERNAL_TRIAL.md
- Dockerfile and .env.example

Excluded by design:
- .env and real secrets
- data/app.db user tokens/usage database
- runs/ generated artifacts
- dist/ previous release packages
- __pycache__/.pytest_cache build caches

First external-user trial:
1. tar -xzf ${NAME}.tar.gz && cd ${NAME}
2. scripts/setup.sh
3. scripts/start.sh
4. BASE_URL=http://127.0.0.1:8787 scripts/external_trial_smoke.py
EOF

# Guard against accidental secret/runtime artifact packaging.
if find "$OUT_DIR" \( -name '.env' -o -name 'app.db' -o -path '*/runs/*' \) | grep -q .; then
  echo "Refusing to package runtime secrets/artifacts" >&2
  find "$OUT_DIR" \( -name '.env' -o -name 'app.db' -o -path '*/runs/*' \) >&2
  exit 1
fi

tar -C "$DIST_DIR" -czf "$ARCHIVE" "$NAME"
shasum -a 256 "$ARCHIVE" > "$SHA_FILE"

echo "$ARCHIVE"
echo "$SHA_FILE"
