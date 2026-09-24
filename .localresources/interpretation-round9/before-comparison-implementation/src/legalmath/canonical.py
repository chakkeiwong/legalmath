"""canonical_v1: exact, deliberately narrower than arbitrary JSON."""
import hashlib
import json

from .errors import BoundaryError

LIMIT = 9007199254740991
MAX_BYTES = 20 * 1024 * 1024


def _check(value, depth=0):
    if depth > 128:
        raise BoundaryError("E_RESOURCE_LIMIT")
    if value is None or type(value) is bool:
        return
    if type(value) is int:
        if abs(value) > LIMIT:
            raise BoundaryError("E_SCHEMA")
    elif type(value) is str:
        if any(0xD800 <= ord(c) <= 0xDFFF for c in value):
            raise BoundaryError("E_SCHEMA")
    elif type(value) is list:
        for item in value:
            _check(item, depth + 1)
    elif type(value) is dict:
        for key, item in value.items():
            if type(key) is not str or not key.isascii():
                raise BoundaryError("E_SCHEMA")
            _check(item, depth + 1)
    else:
        raise BoundaryError("E_SCHEMA")


def canonical(value):
    _check(value)
    data = json.dumps(value, sort_keys=True, ensure_ascii=False, allow_nan=False,
                      separators=(",", ":")).encode("utf-8")
    if len(data) > MAX_BYTES:
        raise BoundaryError("E_RESOURCE_LIMIT")
    return data


def digest(value):
    return hashlib.sha256(canonical(value)).hexdigest()


def raw_digest(data):
    return hashlib.sha256(data).hexdigest()


def _pairs(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise BoundaryError("E_DUPLICATE_ID")
        result[key] = value
    return result


def _invalid(_):
    raise BoundaryError("E_SCHEMA")


def loads(data):
    if len(data) > MAX_BYTES:
        raise BoundaryError("E_RESOURCE_LIMIT")
    try:
        value = json.loads(data, object_pairs_hook=_pairs, parse_float=_invalid,
                           parse_constant=_invalid,
                           parse_int=lambda s: _invalid(s) if s == "-0" else int(s))
        canonical(value)
        return value
    except (ValueError, UnicodeError, RecursionError) as exc:
        raise BoundaryError("E_SCHEMA") from exc
