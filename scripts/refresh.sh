#!/usr/bin/env bash
# Refresh all DurShift data and rebuild outputs.
# Usage: bash scripts/refresh.sh
set -euo pipefail

P="${PYTHON:-python}"
export PYTHONDONTWRITEBYTECODE=1

echo "=== Fetching data sources ==="
$P -B -m durshift.cli fetch-auctions --output data/raw/treasury_auctions.csv
$P -B -m durshift.cli fetch-tips-frn-auctions --output data/raw/tips_frn_auctions.csv
$P -B -m durshift.cli fetch-h15-rates --output data/raw/h15_rates.csv
$P -B -m durshift.cli fetch-tips-real-yields --output data/raw/tips_real_yields.csv
$P -B -m durshift.cli fetch-dealer-positions --output data/raw/dealer_positions.csv
$P -B -m durshift.cli fetch-soma-holdings --output data/raw/soma_holdings.csv
$P -B -m durshift.cli fetch-buyback-schedule \
    --xml-output data/raw/buyback_schedule.xml \
    --csv-output data/interim/buyback_schedule.csv

echo ""
echo "=== Fetching buyback results (requires Playwright) ==="
$P -B -m durshift.cli fetch-buyback-results \
    --index-output data/raw/buyback_operations_index.json \
    --csv-output data/raw/buyback_results_detail.csv

echo ""
echo "=== Building operation panel ==="
$P -B -m durshift.cli build-real-panel \
    --input data/raw/buyback_results_detail.csv \
    --output data/processed/real_operation_panel.csv \
    --h15-rates data/raw/h15_rates.csv \
    --tips-yields data/raw/tips_real_yields.csv

echo ""
echo "=== Generating outputs ==="
$P -B -m durshift.cli build-duration-summary \
    --input data/processed/real_operation_panel.csv \
    --output outputs/tables/real_duration_summary.csv
$P -B -m durshift.cli plot-acceptance \
    --input data/processed/real_operation_panel.csv \
    --output outputs/figures/real_buyback_acceptance.png

echo ""
echo "=== Generating site data ==="
$P -B scripts/generate_site_data.py

echo ""
echo "=== Building static site ==="
(cd site && npm install --prefer-offline && npx vite build && cp -r public/data dist/data)

echo ""
echo "=== Done ==="
echo "Preview: cd site && npx vite preview"
