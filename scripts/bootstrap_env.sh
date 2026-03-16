#!/usr/bin/env bash
set -euo pipefail

python -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -e ".[dev]"

echo "Environment ready."
echo "Next steps:"
echo "  python scripts/verify_repo_readiness.py"
echo "  python -m pytest -q"
echo "  bash scripts/run_pipeline.sh"
