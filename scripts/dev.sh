#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
if [[ ! -d web/node_modules ]]; then npm ci --prefix web; fi
PYTHONPATH=src python3 -m pipeline.api &
api_pid=$!
cleanup() { kill "$api_pid" 2>/dev/null || true; }
trap cleanup EXIT INT TERM
npm run dev --prefix web
