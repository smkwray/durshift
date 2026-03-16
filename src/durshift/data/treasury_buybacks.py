from __future__ import annotations

from pathlib import Path

import requests

from durshift.utils.files import ensure_parent_dir

BUYBACK_RESULTS_PAGE = "https://www.treasurydirect.gov/auctions/results/"


def save_buyback_results_snapshot(destination: str | Path, timeout: int = 30) -> Path:
    """Download the current TreasuryDirect buyback landing page.

    This helper intentionally stores the raw HTML only. The parser for live buyback results
    should be implemented milestone-by-milestone once the current markup assumptions are
    verified against the official page.
    """

    output_path = ensure_parent_dir(destination)
    response = requests.get(BUYBACK_RESULTS_PAGE, timeout=timeout)
    response.raise_for_status()
    output_path.write_text(response.text, encoding="utf-8")
    return output_path


def parse_buyback_results_html(_: str) -> None:
    """Placeholder for the live TreasuryDirect HTML parser.

    Not implemented — use buyback_results.py (Playwright-based scraper) instead,
    which downloads per-operation BBR XML files directly.
    """

    raise NotImplementedError(
        "HTML parsing not implemented. Use buyback_results.fetch_and_save_results() instead."
    )
