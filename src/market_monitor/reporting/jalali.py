"""Gregorian -> Jalali, at the presentation boundary only.

Storage stays ISO/Gregorian UTC (ARCHITECTURE.md §26). Thirty lines of a known
algorithm beats a dependency, and the golden vectors below come from TGJU's own
Persian date labels.
"""

from __future__ import annotations

from datetime import datetime

MONTHS_FA = (
    "فروردین",
    "اردیبهشت",
    "خرداد",
    "تیر",
    "مرداد",
    "شهریور",
    "مهر",
    "آبان",
    "آذر",
    "دی",
    "بهمن",
    "اسفند",
)

_DAYS_BEFORE_MONTH = (0, 31, 59, 90, 120, 151, 181, 212, 243, 273, 304, 334)


def to_jalali(year: int, month: int, day: int) -> tuple[int, int, int]:
    """Convert a Gregorian date to (jy, jm, jd)."""
    if year > 1600:
        jy = 979
        year -= 1600
    else:
        jy = 0
        year -= 621
    leap_reference = year + 1 if month > 2 else year
    days = (
        365 * year
        + (leap_reference + 3) // 4
        - (leap_reference + 99) // 100
        + (leap_reference + 399) // 400
        - 80
        + day
        + _DAYS_BEFORE_MONTH[month - 1]
    )
    jy += 33 * (days // 12053)
    days %= 12053
    jy += 4 * (days // 1461)
    days %= 1461
    if days > 365:
        jy += (days - 1) // 365
        days = (days - 1) % 365
    if days < 186:
        return jy, 1 + days // 31, 1 + days % 31
    return jy, 7 + (days - 186) // 30, 1 + (days - 186) % 30


def format_date_fa(moment: datetime) -> str:
    """'20 مرداد 1405' — the moment must already be in Tehran time."""
    jy, jm, jd = to_jalali(moment.year, moment.month, moment.day)
    return f"{jd} {MONTHS_FA[jm - 1]} {jy}"
