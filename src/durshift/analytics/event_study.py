from __future__ import annotations

from datetime import date, timedelta

from durshift.utils.dates import parse_date


def event_window_bounds(
    event_date: date,
    pre_days: int,
    post_days: int,
) -> tuple[date, date]:
    """Return inclusive start and end dates for an event window."""

    start = event_date - timedelta(days=pre_days)
    end = event_date + timedelta(days=post_days)
    return start, end


def relative_day(observation_date: date, event_date: date) -> int:
    """Return observation day relative to the event date."""

    return (observation_date - event_date).days


def is_in_event_window(
    observation_date: str | date,
    event_date: str | date,
    pre_days: int,
    post_days: int,
) -> bool:
    """Check whether a date belongs to an inclusive event window."""

    obs = parse_date(observation_date)
    event = parse_date(event_date)
    start, end = event_window_bounds(event, pre_days, post_days)
    return start <= obs <= end
