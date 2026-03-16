from datetime import date

from durshift.analytics.event_study import event_window_bounds, is_in_event_window, relative_day


def test_event_window_bounds() -> None:
    start, end = event_window_bounds(date(2026, 3, 10), pre_days=2, post_days=3)
    assert start == date(2026, 3, 8)
    assert end == date(2026, 3, 13)


def test_relative_day() -> None:
    assert relative_day(date(2026, 3, 12), date(2026, 3, 10)) == 2


def test_is_in_event_window() -> None:
    assert is_in_event_window("2026-03-09", "2026-03-10", pre_days=1, post_days=1)
    assert not is_in_event_window("2026-03-08", "2026-03-10", pre_days=1, post_days=1)
