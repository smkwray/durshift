#!/usr/bin/env bash
set -euo pipefail

python -m durshift.cli build-operation-panel   --input data/examples/sample_buybacks.csv   --output data/processed/sample_operation_panel.csv

python -m durshift.cli build-duration-summary   --input data/processed/sample_operation_panel.csv   --output outputs/tables/sample_duration_summary.csv

python -m durshift.cli plot-acceptance   --input data/processed/sample_operation_panel.csv   --output outputs/figures/sample_buyback_acceptance.png

echo "Sample pipeline complete."
echo "Created:"
echo "  data/processed/sample_operation_panel.csv"
echo "  outputs/tables/sample_duration_summary.csv"
echo "  outputs/figures/sample_buyback_acceptance.png"
