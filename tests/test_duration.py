from durshift.analytics.duration import (
    bond_price_from_yield,
    dv01,
    maturity_bucket,
    modified_duration,
)


def test_maturity_bucket_boundaries() -> None:
    assert maturity_bucket(0.5) == "0-2Y"
    assert maturity_bucket(3.0) == "2-5Y"
    assert maturity_bucket(7.5) == "5-10Y"
    assert maturity_bucket(15.0) == "10-20Y"
    assert maturity_bucket(25.0) == "20Y+"


def test_modified_duration_positive_and_reasonable() -> None:
    result = modified_duration(
        coupon_rate=0.04,
        yield_rate=0.04,
        maturity_years=10.0,
    )
    assert result > 0
    assert result < 10


def test_zero_coupon_price_discount() -> None:
    price = bond_price_from_yield(
        coupon_rate=0.0,
        yield_rate=0.05,
        maturity_years=1.0,
    )
    assert price < 100


def test_dv01_positive() -> None:
    result = dv01(
        par_amount=1_000_000,
        coupon_rate=0.04,
        yield_rate=0.04,
        maturity_years=5.0,
    )
    assert result > 0
