"""Retrieve evidence bytes and typed assertions; never certify their truth."""
from datetime import datetime
import hashlib
import json
from pathlib import Path
import re

from ..canonical import canonical, loads


def sha(data):
    return hashlib.sha256(data).hexdigest()


def instant(value):
    if not isinstance(value, str):
        raise ValueError("Explicit ISO timestamp required")
    t = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if t.tzinfo is None or t.utcoffset() is None:
        raise ValueError("Timezone-aware timestamp required")
    return t


def fields(value, expected):
    if not isinstance(value, dict) or set(value) != set(expected):
        raise ValueError("Unexpected or missing fields: " + str(expected))


class Store:
    def __init__(self, directory):
        self.directory = Path(directory).resolve()

    def path(self, identity):
        if not isinstance(identity, str) or not re.fullmatch(r"[0-9a-f]{64}", identity):
            raise ValueError("SHA-256 content identity required")
        path = (self.directory / identity).resolve()
        if not path.is_relative_to(self.directory):
            raise ValueError("Evidence escapes store")
        return path

    def put(self, data):
        if not isinstance(data, bytes):
            data = canonical(data)
        identity = sha(data)
        path = self.path(identity)
        path.parent.mkdir(parents=True, exist_ok=True)
        if path.exists():
            self.get(identity)
        else:
            path.write_bytes(data)
        return identity

    def get(self, identity):
        data = self.path(identity).read_bytes()
        if sha(data) != identity:
            raise ValueError("Evidence content changed")
        return data

    def json(self, identity):
        return loads(self.get(identity))


SOURCE_FIELDS = {"blob", "kind", "media_type", "origin", "recorded_at",
                 "effective_from", "effective_until", "fresh_until", "dependencies",
                 "supersedes", "provenance"}


class Registry:
    def __init__(self, store, records):
        self.store, self.records = store, records
        if not isinstance(records, dict):
            raise ValueError("Source registry required")
        for key, row in records.items():
            fields(row, SOURCE_FIELDS)
            if not isinstance(key, str) or not key:
                raise ValueError("Source identifier required")
            store.path(row["blob"])
            if row["kind"] not in {"law", "facts", "policy", "route", "sanctions", "specification"}:
                raise ValueError("Unknown evidence kind")
            if row["provenance"] not in {"official_retrieval", "supplied", "synthetic"}:
                raise ValueError("Unknown evidence provenance")
            if not row["origin"] or not row["media_type"]:
                raise ValueError("Evidence origin and media type required")
            instant(row["recorded_at"])
            for name in ("effective_from", "effective_until", "fresh_until"):
                if row[name] is not None:
                    instant(row[name])
            if (row["effective_from"] is not None and row["effective_until"] is not None
                    and instant(row["effective_from"]) >= instant(row["effective_until"])):
                raise ValueError("Reversed source interval")
            for name in ("dependencies", "supersedes"):
                if (not isinstance(row[name], list) or any(not isinstance(x, str) or not x for x in row[name])
                        or len(set(row[name])) != len(row[name])):
                    raise ValueError("Unique source identifiers required")

    def check(self, identifiers, effective_at, known_at):
        effective, known = instant(effective_at), instant(known_at)
        problems, visited, active = [], set(), set()

        def visit(key):
            if key in active:
                problems.append(key + ": source dependency cycle")
                return
            if key in visited:
                return
            visited.add(key)
            if key not in self.records:
                problems.append(key + ": missing source")
                return
            active.add(key)
            row = self.records[key]
            try:
                self.store.get(row["blob"])
            except (OSError, ValueError):
                problems.append(key + ": missing or changed bytes")
            if instant(row["recorded_at"]) > known:
                problems.append(key + ": not known at assessment time")
            if row["effective_from"] is None:
                problems.append(key + ": legal/factual effective date not established")
            elif effective < instant(row["effective_from"]):
                problems.append(key + ": not yet effective")
            if row["effective_until"] is not None and effective >= instant(row["effective_until"]):
                problems.append(key + ": no longer effective")
            if row["fresh_until"] is None or known >= instant(row["fresh_until"]):
                problems.append(key + ": freshness not established")
            for successor, other in self.records.items():
                if (key in other["supersedes"] and instant(other["recorded_at"]) <= known
                        and (other["effective_from"] is None or instant(other["effective_from"]) <= effective)):
                    # Even an incompletely documented amendment prevents silent reuse.
                    problems.append(key + ": amendment requires reassessment: " + successor)
            for dependency in row["dependencies"]:
                visit(dependency)
            active.remove(key)

        for key in identifiers:
            visit(key)
        return {"sources": sorted(visited), "issues": sorted(set(problems))}

    def quote(self, source, fragment):
        if not isinstance(fragment, str) or not fragment.strip():
            raise ValueError("Nonempty source span required")
        row = self.records[source]
        text = self.store.get(row["blob"]).decode("utf-8")
        # Whitespace normalization only; no semantic/fuzzy match.
        if " ".join(fragment.split()) not in " ".join(text.split()):
            raise ValueError("Source span absent")
        return {"source": source, "blob": row["blob"], "span": fragment,
                "entailment": "NOT_ESTABLISHED"}


def pointer(document, path):
    if not isinstance(path, str) or (path and not path.startswith("/")):
        raise ValueError("RFC 6901 pointer required")
    value = document
    for token in path.split("/")[1:] if path else []:
        if re.search(r"~(?![01])", token):
            raise ValueError("Invalid pointer escape")
        token = token.replace("~1", "/").replace("~0", "~")
        if isinstance(value, list):
            if not re.fullmatch(r"0|[1-9][0-9]*", token):
                raise ValueError("Invalid array index")
            value = value[int(token)]
        elif isinstance(value, dict):
            value = value[token]
        else:
            raise ValueError("Pointer does not address an evidence value")
    return value


def facts(registry, assertions, declarations, effective_at, known_at):
    """Each assertion addresses actual JSON bytes; conflicting values survive."""
    if not isinstance(assertions, dict) or set(assertions) - set(declarations):
        raise ValueError("Unknown fact name; quality labels are not inputs")
    observations = {}
    for name, typ in declarations.items():
        rows = assertions.get(name, [])
        if not isinstance(rows, list):
            raise ValueError("Fact assertions must be a list")
        values, issues, sources = [], [], set()
        for row in rows:
            fields(row, {"source", "pointer"})
            checked = registry.check([row["source"]], effective_at, known_at)
            issues.extend(checked["issues"])
            sources.update(checked["sources"])
            if checked["issues"]:
                continue
            source = registry.records[row["source"]]
            if source["kind"] not in {"facts", "policy", "route"} or source["media_type"] != "application/json":
                issues.append(name + ": a typed factual document is required")
                continue
            try:
                value = pointer(registry.store.json(source["blob"]), row["pointer"])
                if not ((typ == "bool" and type(value) is bool)
                        or (typ == "integer" and type(value) is int and value >= 0)):
                    raise ValueError("Wrong factual type or negative quantity")
                values.append(value)
            except (ValueError, KeyError, IndexError, TypeError, UnicodeDecodeError):
                issues.append(name + ": missing or invalid factual value")
        status = "CONFLICT" if len(set(values)) > 1 else "UNKNOWN" if issues or not values else "KNOWN"
        observations[name] = {"status": status, "type": typ,
                              "value": values[0] if status == "KNOWN" else None,
                              "issues": sorted(set(issues)), "sources": sorted(sources),
                              "truth_of_assertion": "NOT_ESTABLISHED"}
    return observations
