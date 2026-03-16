from __future__ import annotations

import math


def maturity_bucket(maturity_years: float) -> str:
    """Return a coarse maturity bucket."""

    if maturity_years < 2.0:
        return "0-2Y"
    if maturity_years < 5.0:
        return "2-5Y"
    if maturity_years < 10.0:
        return "5-10Y"
    if maturity_years < 20.0:
        return "10-20Y"
    return "20Y+"


def bond_price_from_yield(
    coupon_rate: float,
    yield_rate: float,
    maturity_years: float,
    frequency: int = 2,
) -> float:
    """Return a simple clean-price approximation for a bullet Treasury security.

    The output is price per 100 par.
    """

    if maturity_years <= 0:
        return 100.0

    periods = max(1, math.ceil(maturity_years * frequency))
    periodic_yield = yield_rate / frequency
    coupon_cashflow = coupon_rate * 100 / frequency

    price = 0.0
    for period in range(1, periods + 1):
        discount = (1 + periodic_yield) ** period
        cashflow = coupon_cashflow
        if period == periods:
            cashflow += 100.0
        price += cashflow / discount
    return price


def modified_duration(
    coupon_rate: float,
    yield_rate: float,
    maturity_years: float,
    frequency: int = 2,
) -> float:
    """Approximate modified duration for a bullet Treasury security."""

    if maturity_years <= 0:
        return 0.0

    periods = max(1, math.ceil(maturity_years * frequency))
    periodic_yield = yield_rate / frequency
    coupon_cashflow = coupon_rate * 100 / frequency

    price = bond_price_from_yield(coupon_rate, yield_rate, maturity_years, frequency)
    weighted_present_value = 0.0

    for period in range(1, periods + 1):
        discount = (1 + periodic_yield) ** period
        cashflow = coupon_cashflow
        if period == periods:
            cashflow += 100.0
        time_years = period / frequency
        weighted_present_value += time_years * cashflow / discount

    macaulay = weighted_present_value / price
    return macaulay / (1 + periodic_yield)


def dv01(
    par_amount: float,
    coupon_rate: float,
    yield_rate: float,
    maturity_years: float,
    frequency: int = 2,
) -> float:
    """Approximate DV01 in dollars for a given par amount."""

    price = bond_price_from_yield(coupon_rate, yield_rate, maturity_years, frequency)
    mod_duration = modified_duration(coupon_rate, yield_rate, maturity_years, frequency)
    market_value = par_amount * price / 100.0
    return mod_duration * market_value * 0.0001
