"""Independent integer Gregorian calculation for retained calendar evidence."""
import re


def civil_number(value):
    """Count days from 0001-01-01 using the Gregorian leap-year definition."""
    year, month, day = (int(p) for p in value.split("-"))
    leap = year % 4 == 0 and (year % 100 != 0 or year % 400 == 0)
    lengths = [31, 29 if leap else 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
    if not (1 <= year <= 9999 and 1 <= month <= 12 and 1 <= day <= lengths[month - 1]):
        raise ValueError("Invalid independent Gregorian date")
    previous = year - 1
    return 365 * previous + previous // 4 - previous // 100 + previous // 400 + sum(lengths[:month - 1]) + day - 1


def instant_number(value):
    parts = re.fullmatch(r"(\d{4}-\d{2}-\d{2})T(\d{2}):(\d{2}):(\d{2})(?:\.(\d{1,6}))?(Z|[+-]\d{2}:\d{2})", value)
    if parts is None:
        raise ValueError("Invalid independent offset instant")
    day, hour, minute, second, fraction, offset = parts.groups()
    hour, minute, second = int(hour), int(minute), int(second)
    if hour > 23 or minute > 59 or second > 59:
        raise ValueError("Invalid independent clock")
    zone = 0
    if offset != "Z":
        h, m = (int(p) for p in offset[1:].split(":"))
        if h > 23 or m > 59:
            raise ValueError("Invalid independent offset")
        zone = (h * 60 + m) * 60 * (1 if offset[0] == "+" else -1)
    whole = civil_number(day) * 86400 + hour * 3600 + minute * 60 + second - zone
    return whole * 1_000_000 + int((fraction or "").ljust(6, "0"))


def expected(start, end, convention, days):
    if convention == "ELAPSED_24_HOUR_DAYS":
        left, right, unit = instant_number(end) - instant_number(start), days * 86_400_000_000, "microseconds"
    elif convention in {"CIVIL_DATE_GAP", "CLEAR_CIVIL_DAYS"}:
        gap = civil_number(end) - civil_number(start)
        left = gap if convention == "CIVIL_DATE_GAP" else max(0, gap - 1)
        right, unit = days, "civil_days"
    else:
        raise ValueError("Unknown oracle convention")
    return {"status": "YES" if left >= right else "NO",
            "exact_comparison": {"left": str(left), "right": str(right), "operator": "GE",
                                 "unit": unit, "convention": convention}}


def verify(calculation):
    target = expected(calculation["start"]["value"], calculation["end"]["value"],
                      calculation["convention"], calculation["days"])
    if calculation["status"] != target["status"] or calculation["exact_comparison"] != target["exact_comparison"]:
        raise ValueError("Calendar result disagrees with independent integer oracle")
    return target
