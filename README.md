# DurShift

**[Live Dashboard](https://smkwray.github.io/durshift/)**

DurShift is a research toolkit that measures how U.S. Treasury buyback operations redistribute duration (interest-rate exposure) across the yield curve.

Since April 2024, the U.S. Treasury has conducted regular debt buyback operations totaling **$321B in par value** across **121 operation dates** and **301 unique CUSIPs** (the nine-character identifiers assigned to individual securities). DurShift turns the raw operation data into an analysis-ready panel and produces descriptive analytics on duration redistribution, dealer positioning, and yield curve impact. The results are descriptive, not causal estimates.

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

This pattern is consistent with cash management operations reducing short-dated supply while not mechanically suppressing long yields. These are simple averages: most operations coincide with auction settlement dates, and 70 of 121 operations have another operation within ±5 days.

### Dealer positioning

Primary dealers increase net Treasury coupon holdings by ~$7B on average around buyback operations, with the largest accumulation in the <2Y sector (+$3.0B). All maturity buckets show positive mean changes.

### TIPS vs nominal

Nominal coupons dominate at 97% of par ($310B / 963 securities). Buybacks of Treasury Inflation-Protected Securities (TIPS) are smaller ($11B / 202 securities) but carry higher duration per dollar of par due to lower real yields.

---

## Method

For each buyback operation, DurShift downloads the official buyback results (BBR) XML file from TreasuryDirect and extracts per-CUSIP accepted par amounts, weighted average accepted prices, coupon rates, and maturity dates.

**Yield proxies** are interpolated from the constant maturity Treasury (CMT) yields in the Federal Reserve's H.15 release: nominal CMT rates for coupon securities, real CMT rates for TIPS (which can be negative). The interpolation weights linearly between the two nearest tenor points.

**Modified duration** and **DV01** (dollar value of a one-basis-point yield change) are computed using standard semiannual cashflow discounting. Duration-dollars are market value (par × price / 100) × modified duration, a measure of the dollar-weighted interest-rate exposure removed from the market.

**Event windows** compare primary dealer positions (New York Fed weekly data) and Treasury yields (H.15 daily) around each operation date. For each window endpoint (for example, 5 calendar days before), the nearest available observation within a ±5 day tolerance is selected. Nearby gross issuance is estimated from Treasury auctions within a ±14 calendar day window; it measures total auction volume near each buyback, not matched replacement supply.

**Classification** uses the stated operation type from TreasuryDirect (Cash Management, Liquidity Support, or Small Value). Maturity buckets follow a standard 5-bucket scheme: 0-2Y, 2-5Y, 5-10Y, 10-20Y, 20Y+.

---

## Data Sources

| Source | Provider | Method | Records |
|:---|:---|:---|---:|
| Buyback results | TreasuryDirect | BBR XML per operation | 3,917 |
| Buyback schedule | Treasury.gov | Public XML | 21 |
| Treasury auctions | Fiscal Data API | REST JSON | 2,733 |
| TIPS and floating rate note (FRN) auctions | TreasuryDirect TA_WS | REST JSON | 151 |
| Treasury yields | Federal Reserve Board | H.15 CSV + bulk XML | 1,617 |
| TIPS real yields | Federal Reserve Board | H.15 bulk XML | 6,551 |
| Dealer positions | NY Fed Markets API | CSV per series | 675 |
| System Open Market Account (SOMA) holdings | NY Fed Markets API | CSV summary | 1,184 |

All data are from official U.S. government public sources, and no API keys are required. The buyback results fetcher uses Playwright (a headless browser) to discover operation URLs on TreasuryDirect, then downloads each BBR XML file directly.

---

## Quick Start

Requires Python 3.11+ and Node.js (the refresh script also builds the dashboard).

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
playwright install chromium     # needed to fetch buyback results

bash scripts/refresh.sh         # fetch all sources, build the panel, outputs, and site data
```

`scripts/refresh.sh` runs each stage through `durshift.cli` (`python -m durshift.cli <command>`), so you can also run individual fetch and build stages on their own.

To run the dashboard locally:

```bash
cd site && npm install && npm run dev
```

The dashboard has 8 interactive Plotly charts with a dark/light theme toggle, summary statistics, chart captions, and the full methodology.

## Architecture

```
src/durshift/
  data/           # Source clients (Fiscal Data, TreasuryDirect, Fed Board, NY Fed)
  panels/         # Panel assembly (operations, financing context, dealer pressure)
  analytics/      # Classification, duration, event windows, duration accounting
  reporting/      # Charts and summary tables
  cli.py          # Command-line entry point
scripts/
  refresh.sh      # Full pipeline: fetch → build → site
  generate_site_data.py  # JSON generation for dashboard
site/             # Vite + Plotly.js static dashboard
```

## Validation

```bash
python scripts/verify_repo_readiness.py
pytest -q
ruff check .
```

## Limitations

- Duration-dollars use coarse yield proxies (H.15 CMT interpolation) and should be treated as approximations, not exact dollar-duration.
- Event-study results are descriptive averages with confounding from same-day auction activity and overlapping windows. They are not causal estimates.
- TIPS securities with maturities below 5 years are clamped to the 5Y real yield (shortest available TIPS CMT tenor).
- Sub-0.5Y maturities are rounded up to a full semiannual period for duration calculation, affecting ~$20B of short-dated par.
- The "nearby gross issuance" measure captures total auction volume within ±14 days, not matched replacement supply.

## License

[MIT](LICENSE)
