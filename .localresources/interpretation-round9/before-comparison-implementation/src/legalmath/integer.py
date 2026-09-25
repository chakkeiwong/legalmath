"""Arbitrary decimal strings without changing Python's global int digit limit."""
CHUNK = 1000
BASE = 10 ** CHUNK


def parse(text):
    negative = text.startswith("-")
    digits = text[1:] if negative else text
    value = 0
    for i in range(0, len(digits), CHUNK):
        part = digits[i:i + CHUNK]
        value = value * (10 ** len(part)) + int(part)
    return -value if negative else value


def decimal(value):
    if value == 0:
        return "0"
    sign = "-" if value < 0 else ""
    value = abs(value)
    parts = []
    while value:
        value, remainder = divmod(value, BASE)
        parts.append(str(remainder))
    return sign + parts[-1] + "".join(p.zfill(CHUNK) for p in reversed(parts[:-1]))
