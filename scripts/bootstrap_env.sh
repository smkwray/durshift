#!/usr/bin/env bash
set -euo pipefail

VENV_DIR="${HOME}/venvs/DurShift"
mkdir -p "$(dirname "$VENV_DIR")"
python -m venv "$VENV_DIR"
source "$VENV_DIR/bin/activate"
export PYTHONDONTWRITEBYTECODE=1
python -m pip install --upgrade pip
pip install --no-compile -e ".[dev]"

echo "Environment ready."
echo "Next steps:"
echo "  python scripts/verify_repo_readiness.py"
echo "  python -m pytest -q"
echo "  bash scripts/run_pipeline.sh"
