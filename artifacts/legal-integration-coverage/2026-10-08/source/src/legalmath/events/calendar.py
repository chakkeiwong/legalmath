"""Explicit reviewed calendar conventions; no implicit business-day policy."""
from datetime import date, datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo
from ..errors import LegalMathError


def anniversary(day, years, leap_policy):
    if leap_policy not in ("feb28", "mar1", "reject") or type(years) is not int or years < 0:
        raise LegalMathError("E_SCHEMA")
    d = date.fromisoformat(day)
    try:
        return d.replace(year=d.year + years).isoformat()
    except ValueError as exc:
        if d.month != 2 or d.day != 29 or not 1 <= d.year + years <= 9999 or leap_policy == "reject":
            raise LegalMathError("E_TIME") from exc
        return date(d.year + years, 2 if leap_policy == "feb28" else 3, 28 if leap_policy == "feb28" else 1).isoformat()


def end_of_local_date(day):
    try:
        following = date.fromisoformat(day) + timedelta(days=1)
        value = datetime.combine(following, time(), ZoneInfo("Asia/Hong_Kong")).astimezone(timezone.utc)
    except (ValueError, OverflowError) as exc:
        raise LegalMathError("E_TIME") from exc
    return value.isoformat(timespec="microseconds").replace("+00:00", "Z")
