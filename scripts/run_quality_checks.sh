#!/usr/bin/env bash
set -euo pipefail

python scripts/verify_repo_readiness.py
python -m pytest -q

if command -v ruff >/dev/null 2>&1; then
  ruff check .
  ruff format --check .
fi
