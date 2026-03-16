"""Scrape and parse Treasury buyback operation results.

Uses Playwright to discover operation URLs from TreasuryDirect, then
downloads the per-operation BBR (Buyback Results) XML files. Each XML
contains operation-level totals and per-CUSIP accepted amounts.

Data source: https://treasurydirect.gov/auctions/announcements-data-results/buy-backs/
"""

from __future__ import annotations

import json
import logging
import time
import xml.etree.ElementTree as ET
from pathlib import Path

import pandas as pd
import requests

from durshift.utils.files import ensure_parent_dir

logger = logging.getLogger(__name__)

BUYBACKS_PAGE = "https://treasurydirect.gov/auctions/announcements-data-results/buy-backs/"
TREASURYDIRECT_BASE = "https://treasurydirect.gov"

RESULT_COLUMNS = [
    "operation_date",
    "operation_type",
    "security_type",
    "maturity_bucket",
    "operation_status",
    "settlement_date",
    "max_par_redeemed",
    "maturity_range_begin",
    "maturity_range_end",
    "issues_eligible",
    "issues_accepted",
    "total_par_offered",
    "total_par_accepted",
    "cusip",
    "coupon_rate",
    "maturity_date",
    "par_amount_accepted",
    "weighted_avg_price",
    "result_xml",
]


def scrape_operation_index() -> list[dict]:
    """Use Playwright to scrape all buyback operation metadata from TreasuryDirect.

    Returns a list of dicts with operation_date, operation_type, security_type,
    maturity_bucket, and XML URLs for results/announcements.
    """
    import asyncio

    from playwright.async_api import async_playwright

    async def _scrape():
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()

            logger.info("Loading TreasuryDirect buyback page...")
            await page.goto(BUYBACKS_PAGE, timeout=60000)
            await page.wait_for_timeout(5000)

            # Click "Show All" to remove default date filter
            show_all = await page.query_selector("text='Show All'")
            if show_all:
                await show_all.click()
                await page.wait_for_timeout(5000)

            # Show 100 entries per page
            await page.select_option("select[name='example_length']", "100")
            await page.wait_for_timeout(3000)

            all_results: list[dict] = []
            page_num = 1

            while True:
                rows = await page.query_selector_all("#example tbody tr")
                for row in rows:
                    cells = await row.query_selector_all("td")
                    if len(cells) < 6:
                        continue
                    op_date = (await cells[1].inner_text()).strip()
                    if not op_date or "No data" in op_date:
                        continue

                    entry = {
                        "operation_date": op_date,
                        "operation_type": (await cells[3].inner_text()).strip(),
                        "security_type": (await cells[4].inner_text()).strip(),
                        "maturity_bucket": (await cells[5].inner_text()).strip(),
                    }

                    for prefix, key in [
                        ("BBR_", "result_xml"),
                        ("BBA_", "announcement_xml"),
                        ("BBPA_", "prelim_announcement_xml"),
                    ]:
                        links = await row.query_selector_all(f"a[href*='{prefix}'][href$='.xml']")
                        if links:
                            entry[key] = await links[0].get_attribute("href")

                    all_results.append(entry)

                logger.info("Page %d: collected %d total operations", page_num, len(all_results))

                next_btn = await page.query_selector("#example_next:not(.disabled)")
                if next_btn:
                    cls = await next_btn.get_attribute("class") or ""
                    if "disabled" in cls:
                        break
                    await next_btn.click()
                    await page.wait_for_timeout(2000)
                    page_num += 1
                else:
                    break

            await browser.close()
            return all_results

    return asyncio.run(_scrape())


def download_result_xmls(
    operations: list[dict],
    *,
    polite_delay: float = 0.05,
    timeout: int = 30,
) -> pd.DataFrame:
    """Download BBR XML files and parse into a security-level DataFrame.

    Parameters
    ----------
    operations : list[dict]
        Output of :func:`scrape_operation_index`. Only entries with
        ``result_xml`` are processed.
    polite_delay : float
        Seconds to wait between batches of requests.
    timeout : int
        HTTP timeout per request.

    Returns
    -------
    pd.DataFrame
        One row per security per operation with RESULT_COLUMNS.
    """
    ops_with_results = [op for op in operations if "result_xml" in op]
    logger.info("Downloading %d result XMLs...", len(ops_with_results))

    all_rows: list[dict] = []
    errors: list[dict] = []

    for i, op in enumerate(ops_with_results):
        url = op["result_xml"]
        if not url.startswith("http"):
            url = TREASURYDIRECT_BASE + url

        try:
            r = requests.get(url, timeout=timeout)
            r.raise_for_status()
            root = ET.fromstring(r.content)
            _parse_result_xml(root, op, all_rows)
        except Exception as exc:
            errors.append({"url": url, "error": str(exc)})
            logger.warning("Failed to parse %s: %s", url, exc)

        if (i + 1) % 10 == 0:
            time.sleep(polite_delay)
        if (i + 1) % 50 == 0:
            logger.info("  %d/%d processed (%d rows)", i + 1, len(ops_with_results), len(all_rows))

    if errors:
        error_rate = len(errors) / len(ops_with_results) if ops_with_results else 1.0
        logger.error(
            "%d/%d downloads failed (%.0f%%)",
            len(errors),
            len(ops_with_results),
            error_rate * 100,
        )
        if error_rate > 0.1:
            raise RuntimeError(
                f"Buyback results download failed for {len(errors)}/{len(ops_with_results)} "
                f"operations ({error_rate:.0%}). Aborting to prevent partial dataset. "
                f"First error: {errors[0]}"
            )

    logger.info("Parsed %d security rows from %d operations", len(all_rows), len(ops_with_results))

    if not all_rows:
        return pd.DataFrame(columns=RESULT_COLUMNS)

    frame = pd.DataFrame(all_rows, columns=RESULT_COLUMNS)

    # Reconciliation: verify total_par_accepted matches sum of per-security par
    _reconcile_totals(frame)

    return frame


def _reconcile_totals(frame: pd.DataFrame) -> None:
    """Verify that per-security par sums match operation-level totals."""
    grouped = frame.groupby(["operation_date", "result_xml"]).apply(
        lambda g: pd.Series(
            {
                "sum_par": pd.to_numeric(g["par_amount_accepted"], errors="coerce").sum(),
                "stated_total": pd.to_numeric(g["total_par_accepted"], errors="coerce").iloc[0],
            }
        ),
        include_groups=False,
    )

    mismatches = grouped[grouped["sum_par"] != grouped["stated_total"]]
    if not mismatches.empty:
        logger.warning(
            "Par reconciliation mismatch in %d operations (sum of per-security != stated total). "
            "This may indicate missing securityDetails tags in some XMLs.",
            len(mismatches),
        )


def _require_tag(root: ET.Element, tag: str) -> str:
    """Extract required text from an XML element; raise if missing."""
    el = root.find(tag)
    if el is None or el.text is None:
        raise ValueError(f"Required XML tag <{tag}> is missing or empty")
    return el.text


def _parse_result_xml(root: ET.Element, op: dict, rows: list[dict]) -> None:
    """Parse a single BBR XML into rows appended to *rows*.

    Raises ValueError if required tags are missing (schema drift detection).
    """
    op_status = _require_tag(root, "operationStatus")
    settlement = root.findtext("settlementDT", "")
    max_redeemed = root.findtext("maxParAmountRedeemed", "")
    mat_begin = root.findtext("maturityDateRangeBegin", "")
    mat_end = root.findtext("maturityDateRangeEnd", "")
    n_eligible = root.findtext("numberIssuesEligible", "")
    n_accepted = root.findtext("numberIssuesAccepted", "")
    total_offered = root.findtext("totalParAmountOffered", "")
    total_accepted = root.findtext("totalParAmountAccepted", "")

    securities = root.findall("securityDetails")
    if not securities:
        raise ValueError("No <securityDetails> elements found in BBR XML")

    for sec in securities:
        # Required per-security fields
        cusip = sec.findtext("cusipNumber")
        par_accepted = sec.findtext("parAmountAccepted")
        if cusip is None or par_accepted is None:
            raise ValueError("Missing cusipNumber or parAmountAccepted in securityDetails")

        rows.append(
            {
                "operation_date": op["operation_date"],
                "operation_type": op["operation_type"],
                "security_type": op["security_type"],
                "maturity_bucket": op["maturity_bucket"],
                "operation_status": op_status,
                "settlement_date": settlement,
                "max_par_redeemed": max_redeemed,
                "maturity_range_begin": mat_begin,
                "maturity_range_end": mat_end,
                "issues_eligible": n_eligible,
                "issues_accepted": n_accepted,
                "total_par_offered": total_offered,
                "total_par_accepted": total_accepted,
                "cusip": sec.findtext("cusipNumber", ""),
                "coupon_rate": sec.findtext("couponRate", ""),
                "maturity_date": sec.findtext("maturityDate", ""),
                "par_amount_accepted": sec.findtext("parAmountAccepted", ""),
                "weighted_avg_price": sec.findtext("weightedAverageAcceptedPrice", ""),
                "result_xml": op.get("result_xml", ""),
            }
        )


def fetch_and_save_results(
    index_destination: str | Path,
    csv_destination: str | Path,
) -> tuple[Path, Path]:
    """Full pipeline: scrape index, download XMLs, save CSV.

    Returns paths to the saved index JSON and results CSV.
    """
    operations = scrape_operation_index()

    index_path = ensure_parent_dir(index_destination)
    index_path.write_text(json.dumps(operations, indent=2), encoding="utf-8")
    logger.info("Saved %d operation entries to %s", len(operations), index_path)

    results = download_result_xmls(operations)

    csv_path = ensure_parent_dir(csv_destination)
    results.to_csv(csv_path, index=False)
    logger.info("Saved %d result rows to %s", len(results), csv_path)

    return index_path, csv_path
