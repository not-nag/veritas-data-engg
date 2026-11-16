#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
python_bin=python3
if [[ -x .venv/bin/python ]]; then python_bin=.venv/bin/python; fi
PYTHONPATH=src "$python_bin" -m unittest discover -s tests -v
node --test tests/test_walkthrough.mjs
