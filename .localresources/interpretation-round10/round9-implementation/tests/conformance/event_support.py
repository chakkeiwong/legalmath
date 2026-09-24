"""Explicit migration of old partial fixtures into attributed profile requests."""
from copy import deepcopy
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def event_cases():
    cases = json.loads((ROOT / "docs/specs/v0.1/fixtures/event-cases.json").read_text())
    result = []
    for old in cases:
        events = deepcopy(old["events"])
        header = {**old["stream_header"], "stream_id": old["stream_id"], "profile": old["profile"],
            "actor": "synthetic.bank", "action": "synthetic.review", "obligation_id": "synthetic.duty", "initial_snapshot": None}
        for e in events:
            if e["kind"] == "obligation.opened": e["source_bundle_hash"] = "a" * 64
            if e["kind"] == "watermark": e["complete_from"] = "2026-09-01T00:00:00.000000Z"
        request = {"header": header, "events": events, "valid_at": old["valid_at"], "known_at": old["known_at"], "completeness": old.get("completeness")}
        result.append({"id": old["id"], "request": request, "expected": old["expected"]})
    return result
