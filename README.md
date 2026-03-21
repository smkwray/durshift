# DurShift

**[Live Dashboard](https://smkwray.github.io/durshift/)**

Research toolkit for analyzing how U.S. Treasury buyback operations redistribute duration across the yield curve.

Since April 2024, the U.S. Treasury has conducted regular debt buyback operations totaling **$321B in par value** across **121 operation dates** and **301 unique CUSIPs**. DurShift processes the raw operation data into an analysis-ready panel and produces descriptive analytics on duration redistribution, dealer positioning, and yield curve impact.

---

## Results

### Duration redistribution

| Maturity Bucket | Par Retired | % of Par | % of Duration-$ | Avg Duration |
|:---|---:|---:|---:|---:|
| 0-2Y | $180B | 56% | 16% | 1.3 |
| 2-5Y | $45B | 14% | 12% | 3.4 |
| 5-10Y | $22B | 7% | 10% | 6.1 |
| 10-20Y | $37B | 11% | **28%** | 13.8 |
| 20Y+ | $37B | 12% | **35%** | 17.5 |

**Total duration retired: ~$1.2 trillion in duration-dollars.** Duration-dollars = market value (par × accepted price / 100) × modified duration.

The par/duration asymmetry is the central finding. Cash management operations retire over half of all par in the 0-2Y bucket, but that represents only 16% of duration impact. The 10-20Y and 20Y+ buckets together account for just 23% of par but **63% of duration-dollars**, because each long bond retired removes 15-25 years of interest-rate exposure.

### Yield curve impact

Around buyback operations, front-end yields show statistically significant declines at 1M, 3M, and 6M tenors, while the long end (20Y, 30Y) shows significant positive moves. Mid-curve tenors (1Y-10Y) are not distinguishable from zero. See the dashboard for confidence intervals and p-values.

This pattern is consistent with cash management operations reducing short-dated supply while not mechanically suppressing long yields. However, these are simple averages, not causal estimates — most operations coincide with auction settlement dates, and 70 of 121 operations have another operation within ±5 days.

### Dealer positioning

Primary dealers increase net Treasury coupon holdings by ~$7B on average around buyback operations, with the largest accumulation in the <2Y sector (+$3.0B). All maturity buckets show positive mean changes.

### TIPS vs nominal

Nominal coupons dominate at 97% of par ($310B / 963 securities). TIPS buybacks ($11B / 202 securities) are smaller but carry higher duration per dollar of par due to lower real yields.

---

## Method

For each buyback operation, DurShift downloads the official results XML from TreasuryDirect, extracting per-CUSIP accepted par amounts, weighted average accepted prices, coupon rates, and maturity dates.

**Yield proxies** are interpolated from the Federal Reserve H.15 constant maturity term structure — nominal CMT rates for coupon securities, real CMT rates for TIPS (which can be negative). The interpolation uses linear weighting between the two nearest tenor points.

**Modified duration** and **DV01** are computed using standard semiannual cashflow discounting. Duration-dollars are defined as market value (par × price / 100) × modified duration, which gives a measure of dollar-weighted interest-rate exposure removed from the market.

**Event windows** compare primary dealer positions (NY Fed weekly data) and Treasury yields (H.15 daily) at exact calendar offsets before and after each operation date. Nearby gross issuance is estimated from Treasury auctions within a ±14 calendar day window — this measures total auction volume near each buyback, not matched replacement supply.

**Classification** uses the stated operation type from TreasuryDirect (Cash Management, Liquidity Support, or Small Value). Maturity buckets follow a standard 5-bucket scheme: 0-2Y, 2-5Y, 5-10Y, 10-20Y, 20Y+.

---

## Data Sources

| Source | Provider | Method | Records |
|:---|:---|:---|---:|
| Buyback results | TreasuryDirect | BBR XML per operation | 3,917 |
| Buyback schedule | Treasury.gov | Public XML | 21 |
| Treasury auctions | Fiscal Data API | REST JSON | 2,733 |
| TIPS/FRN auctions | TreasuryDirect TA_WS | REST JSON | 151 |
| Treasury yields | Federal Reserve Board | H.15 CSV + bulk XML | 1,617 |
| TIPS real yields | Federal Reserve Board | H.15 bulk XML | 6,551 |
| Dealer positions | NY Fed Markets API | CSV per series | 675 |
| SOMA holdings | NY Fed Markets API | CSV summary | 1,184 |

All data is from official U.S. government public sources. No authentication or API keys required. The buyback results scraper uses Playwright to discover operation URLs from TreasuryDirect, then downloads individual BBR XML files directly.

---

## Quick Start

```bash
# 1. Create virtualenv (never inside the repo)
uv venv ~/venvs/DurShift --python 3.11
P="$HOME/venvs/DurShift/bin/python"

# 2. Install (playwright needed for buyback scraping)
$P -m pip install -e ".[dev]"
$P -m playwright install chromium

# 3. Fetch all data sources
$P -B -m durshift.cli fetch-auctions --output data/raw/treasury_auctions.csv
$P -B -m durshift.cli fetch-tips-frn-auctions --output data/raw/tips_frn_auctions.csv
$P -B -m durshift.cli fetch-h15-rates --output data/raw/h15_rates.csv
$P -B -m durshift.cli fetch-tips-real-yields --output data/raw/tips_real_yields.csv
$P -B -m durshift.cli fetch-dealer-positions --output data/raw/dealer_positions.csv
$P -B -m durshift.cli fetch-soma-holdings --output data/raw/soma_holdings.csv
$P -B -m durshift.cli fetch-buyback-schedule \
    --xml-output data/raw/buyback_schedule.xml \
    --csv-output data/interim/buyback_schedule.csv
$P -B -m durshift.cli fetch-buyback-results \
    --index-output data/raw/buyback_operations_index.json \
    --csv-output data/raw/buyback_results_detail.csv

# 4. Build the operation panel
$P -B -m durshift.cli build-real-panel \
    --input data/raw/buyback_results_detail.csv \
    --output data/processed/real_operation_panel.csv \
    --h15-rates data/raw/h15_rates.csv \
    --tips-yields data/raw/tips_real_yields.csv

# 5. Generate outputs + site data
$P -B -m durshift.cli build-duration-summary \
    --input data/processed/real_operation_panel.csv \
    --output outputs/tables/real_duration_summary.csv
$P -B scripts/generate_site_data.py

# Or just: bash scripts/refresh.sh
```

## Interactive Dashboard

**[https://smkwray.github.io/durshift/](https://smkwray.github.io/durshift/)**

8 interactive Plotly charts with dark/light theme toggle, summary statistics, chart captions, and full methodology. To run locally:

```bash
cd site && npm install && npm run dev
```

## Architecture

```
src/durshift/
  data/           # 8 source clients (Fiscal Data, TreasuryDirect, Fed Board, NY Fed)
  panels/         # Panel assembly (operations, financing context, dealer pressure)
  analytics/      # Classification, duration, event windows, duration accounting
  reporting/      # Charts and summary tables
  cli.py          # 12 CLI commands
scripts/
  refresh.sh      # Full pipeline: fetch → build → site
  generate_site_data.py  # JSON generation for dashboard
site/             # Vite + Plotly.js static dashboard
```

## Validation

```bash
"$HOME/venvs/DurShift/bin/python" scripts/verify_repo_readiness.py
PYTHONDONTWRITEBYTECODE=1 "$HOME/venvs/DurShift/bin/python" -B -m pytest -q  # 76 tests
"$HOME/venvs/DurShift/bin/ruff" check .
```

## Limitations

- Duration-dollars use coarse yield proxies (H.15 CMT interpolation) and should be treated as approximations, not exact dollar-duration.
- Event-study results are descriptive averages with confounding from same-day auction activity and overlapping windows. They are not causal estimates.
- TIPS securities with maturities below 5 years are clamped to the 5Y real yield (shortest available TIPS CMT tenor).
- Sub-0.5Y maturities are rounded up to a full semiannual period for duration calculation, affecting ~$20B of short-dated par.
- The "nearby gross issuance" measure captures total auction volume within ±14 days, not matched replacement supply.

## License

[MIT](LICENSE)
