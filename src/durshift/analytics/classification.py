from __future__ import annotations

PURPOSE_LIQUIDITY_SUPPORT = "liquidity_support"
PURPOSE_CASH_MANAGEMENT = "cash_management"
PURPOSE_MATURITY_MANAGEMENT = "maturity_management"


def classify_operation(
    security_type: str,
    maturity_years: float,
    stated_purpose: str | None = None,
    notes: str | None = None,
) -> str:
    """Assign a transparent first-pass purpose label.

    The seed intentionally uses simple rules that are easy to inspect and later replace.
    """

    text = " ".join(part for part in [stated_purpose, notes] if part).lower()

    if "cash" in text:
        return PURPOSE_CASH_MANAGEMENT
    if "maturity" in text:
        return PURPOSE_MATURITY_MANAGEMENT
    if "liquidity" in text:
        return PURPOSE_LIQUIDITY_SUPPORT
    if security_type.lower() == "bill":
        return PURPOSE_CASH_MANAGEMENT
    if maturity_years <= 2.0:
        return PURPOSE_CASH_MANAGEMENT
    return PURPOSE_LIQUIDITY_SUPPORT
