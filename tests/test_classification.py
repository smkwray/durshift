from durshift.analytics.classification import (
    PURPOSE_CASH_MANAGEMENT,
    PURPOSE_LIQUIDITY_SUPPORT,
    PURPOSE_MATURITY_MANAGEMENT,
    classify_operation,
)


def test_classify_cash_management_from_text() -> None:
    assert (
        classify_operation("NominalCoupon", 1.5, stated_purpose="cash_management")
        == PURPOSE_CASH_MANAGEMENT
    )


def test_classify_bills_as_cash_management() -> None:
    assert classify_operation("Bill", 0.25) == PURPOSE_CASH_MANAGEMENT


def test_classify_maturity_management_from_notes() -> None:
    assert (
        classify_operation("NominalCoupon", 8.0, notes="maturity management adjustment")
        == PURPOSE_MATURITY_MANAGEMENT
    )


def test_longer_coupon_defaults_to_liquidity_support() -> None:
    assert classify_operation("NominalCoupon", 12.0) == PURPOSE_LIQUIDITY_SUPPORT
