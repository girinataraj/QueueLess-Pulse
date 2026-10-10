#!/usr/bin/env bash
set -euo pipefail
python -m pip install pip==26.2.1 -r requirements.txt
python scripts/generate_contracts.py --check
npx --yes pnpm@11.25.0 --dir frontend install --frozen-lockfile --strict-peer-dependencies --prod=false
npx --yes pnpm@11.25.0 --dir frontend run build
test -s frontend/dist/index.html
# Build only. Database initialization/upgrades are deliberate release operations.
