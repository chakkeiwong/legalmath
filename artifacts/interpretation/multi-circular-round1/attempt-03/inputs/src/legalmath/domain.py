"""Scalar and explicit assessment-time validation, independent of HTTP."""
from datetime import date, datetime
import re

from .errors import BoundaryError

TIME = re.compile(r"[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}\.[0-9]{6}Z\Z")
INTEGER = re.compile(r"(?:0|-?[1-9][0-9]*)\Z")
IDENTIFIER = re.compile(r"[a-z][a-z0-9_.-]*\Z")


def timestamp(value):
    if not isinstance(value, str) or not TIME.fullmatch(value):
        raise BoundaryError("E_TIME")
    try:
        datetime.fromisoformat(value)
    except ValueError as exc:
        raise BoundaryError("E_TIME") from exc
    return value


def interval(start, end):
    timestamp(start)
    if end is not None and timestamp(end) <= start:
        raise BoundaryError("E_TIME")


def eligible(start, end, at):
    return start <= at and (end is None or at < end)


def scalar(typ, value):
    if typ == "bool":
        return type(value) is bool
    if typ in ("integer", "money_hkd"):
        return type(value) is str and bool(INTEGER.fullmatch(value))
    if typ == "date" and type(value) is str and re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}", value):
        try:
            date.fromisoformat(value)
            return True
        except ValueError:
            pass
    return False
