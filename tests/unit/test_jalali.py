from datetime import UTC, datetime

import pytest

from market_monitor.reporting.jalali import format_date_fa, to_jalali


@pytest.mark.parametrize(
    ("gregorian", "expected"),
    [
        # TGJU labelled this exact date ۲۰ مرداد in the captured fixture.
        ((2026, 8, 11), (1405, 5, 20)),
        ((2026, 8, 12), (1405, 5, 21)),
        ((2026, 3, 21), (1405, 1, 1)),  # Nowruz
        ((2025, 3, 20), (1403, 12, 30)),  # last day of a leap Jalali year
        ((2024, 1, 1), (1402, 10, 11)),
        ((1979, 2, 11), (1357, 11, 22)),
    ],
)
def test_known_dates(gregorian, expected):
    assert to_jalali(*gregorian) == expected


def test_format_uses_persian_month_name():
    moment = datetime(2026, 8, 11, 13, 0, tzinfo=UTC)
    assert format_date_fa(moment) == "20 مرداد 1405"
