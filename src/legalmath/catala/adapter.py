"""Input boundary and result envelope for independently authored Catala pilots.

This module never imports or calls the RuleIR evaluator. Shared schema/type/time
validation is a declared common boundary, not independent semantic evidence.
"""
from copy import deepcopy
from decimal import Decimal
import hashlib
from pathlib import Path
import re

from ..canonical import digest
from ..domain import eligible, timestamp
from ..errors import diagnostic
from ..ir.load import schema_errors
from ..ir.typecheck import validate_snapshot


class UnsupportedProfile(ValueError):
    pass


FIELDS = ("status", "type", "value", "mode", "diagnostics", "reason_codes",
          "missing_inputs", "blocking_inputs")


def native_integer(value):
    if type(value) is int:
        return value
    if type(value) is str and re.fullmatch(r"0|-?[1-9][0-9]*", value):
        return int(value)
    if isinstance(value, Decimal) and value.is_finite() and value == value.to_integral_value():
        return int(value)
    raise ValueError("Catala integer response must be exact")


def projection(result):
    return {key: result[key] for key in FIELDS if key in result}


def prepare(case, profile):
    """Validate an exact reviewed bundle and retain unavailable facts explicitly."""
    bundle, snapshot = case["bundle"], case["snapshot"]
    valid_at, known_at = timestamp(case["valid_at"]), timestamp(case["known_at"])
    mode = case.get("mode", "draft")
    if mode != "draft":
        raise UnsupportedProfile("Catala pilot accepts draft mode only")
    binding = profile["bundles"].get(digest(bundle))
    if binding is None or case["rule_id"] != binding["rule_id"]:
        raise UnsupportedProfile("Bundle/rule has no reviewed Catala implementation")
    errors = schema_errors("fact-snapshot", snapshot, "/snapshot")
    if not errors:
        errors = validate_snapshot(bundle, snapshot)
    if errors:
        raise ValueError("Invalid fact snapshot: " + str(errors))
    typ = bundle["rules"][0]["type"]
    base = {"type": typ, "mode": mode, "diagnostics": [], "reason_codes": [],
            "missing_inputs": [], "blocking_inputs": []}
    packet = {"scope": binding["scope"], "inputs": {}, "base": base,
              "preflight": None, "bundle_hash": digest(bundle),
              "snapshot_hash": digest(snapshot), "valid_at": valid_at,
              "known_at": known_at, "rule_id": case["rule_id"],
              "source_span_ids": bundle["rules"][0]["source_span_ids"],
              "source_hashes": sorted({s["raw_sha256"] for s in bundle["source_spans"]}),
              "evidence_ids": []}
    if not eligible(bundle["valid_from"], bundle["valid_until"], valid_at):
        base.update(status="ERROR", reason_codes=["E_VERSION_TIME"],
                    diagnostics=[diagnostic("E_VERSION_TIME", "/valid_at")])
        packet["preflight"] = "version"
        return packet
    facts = snapshot["facts"]
    conflicts = sorted(name for name in binding["dependencies"]
                       if facts[name]["status"] == "conflict")
    if conflicts:
        base.update(status="CONFLICT", reason_codes=["INPUT_CONFLICT"],
                    blocking_inputs=conflicts)
        packet["preflight"] = "input_conflict"
        return packet

    def read(name):
        fact = facts[name]
        usable = (fact["status"] == "known"
                  and eligible(fact["valid_from"], fact["valid_until"], valid_at)
                  and fact["recorded_at"] <= known_at)
        if usable:
            packet["evidence_ids"].extend(fact["evidence_ids"])
            return True, fact["value"]
        base["missing_inputs"].append(name)
        base["reason_codes"].append(fact.get("reason", "STALE" if
            fact.get("recorded_at", "") <= known_at else "MISSING"))
        return False, None

    scope = bundle["rules"][0]["scope"]
    if scope["op"] == "fact":
        known, value = read(scope["name"])
        if not known or not value:
            base["status"] = "UNKNOWN" if not known else "OUT_OF_SCOPE"
            if not known:
                base["reason_codes"].append("SCOPE_UNKNOWN")
                base["blocking_inputs"] = list(base["missing_inputs"])
            packet["preflight"] = "scope"
            return packet
    mapping = {"Financial": [("portfolio_known", "portfolio_cents", "portfolio"),
                              ("assets_known", "assets_cents", "net_assets_ex_home")],
               "Exceptions": [("first_known", "first_applies", "a"),
                               ("second_known", "second_applies", "b")]}
    for known_key, value_key, name in mapping[binding["scope"]]:
        known, value = read(name)
        packet["inputs"][known_key] = known
        # Payload is explicitly masked by *known in Catala; it is never promoted
        # to a known fact. Tests vary masked payloads to check independence.
        packet["inputs"][value_key] = (value if known else
            ("0" if binding["scope"] == "Financial" else False))
    return packet


def finish(packet, native, engine, implementation=None):
    result = deepcopy(packet["base"])
    if packet["preflight"] is None:
        if not isinstance(native, dict) or "decision" not in native:
            raise ValueError("Catala response is missing its decision")
        code = native_integer(native["decision"])
        allowed = {"Financial": {-1, 0, 1}, "Exceptions": {-1, 2, 3}}
        if code not in allowed[packet["scope"]]:
            raise ValueError("Invalid Catala decision for profile")
        result["status"] = {-1: "UNKNOWN", 0: "FALSE", 1: "TRUE",
                            2: "CONFLICT", 3: "VALUE"}[code]
        if code in (0, 1):
            result["value"] = code == 1
        elif code == 3:
            result["value"] = str(native_integer(native["amount"]))
        elif code == 2:
            result["reason_codes"] = ["MULTIPLE_EXCEPTIONS"]
        if code in (-1, 2):
            result["blocking_inputs"] = list(result["missing_inputs"])
    for key in ("missing_inputs", "blocking_inputs", "reason_codes"):
        result[key] = sorted(set(result[key]))
    for key in ("bundle_hash", "snapshot_hash", "valid_at", "known_at", "rule_id",
                "source_span_ids", "source_hashes"):
        result[key] = deepcopy(packet[key])
    result.update(engine_version=engine, evidence_ids=sorted(set(packet["evidence_ids"])),
                  execution_layer=packet["preflight"] or "catala",
                  trace_format="catala-pilot-source-map.v1", release_eligible=False)
    result["implementation"] = {"adapter_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                                **(implementation or {})}
    result["result_hash"] = digest(result)
    return result
