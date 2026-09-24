"""Rebuild the proposed contract schemas and fixed conformance inputs, offline.

This is document tooling, not the RuleIR interpreter. Expected results below are
hand-specified examples; do not replace them with calls to a future interpreter.
"""
from copy import deepcopy
from pathlib import Path
import hashlib
import json

ROOT = Path(__file__).resolve().parents[1]
DEST = ROOT / "docs/specs/v0.1"
ID = {"type": "string", "pattern": "^[a-z][a-z0-9_.-]*$"}
STR = {"type": "string", "minLength": 1}
HASH = {"type": "string", "pattern": "^[0-9a-f]{64}$"}
INT = {"type": "string", "pattern": "^(0|-?[1-9][0-9]*)$"}
TIME = {"type": "string", "format": "date-time", "pattern": r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{6}Z$"}
DATE = {"type": "string", "format": "date"}
TYPES = {"enum": ["bool", "integer", "money_hkd", "date"]}
REF = {"$ref": "#/$defs/expr"}


def obj(props, required=None):
    return {"type": "object", "properties": props,
            "required": list(props) if required is None else required,
            "additionalProperties": False}


def arr(item, minimum=0):
    return {"type": "array", "items": item, "minItems": minimum}


def nullable(item):
    return {"anyOf": [item, {"type": "null"}]}


def typed_values(props):
    return {"oneOf": [obj({**props, "type": {"const": typ}, "value": val})
                      for typ, val in [("bool", {"type": "boolean"}),
                                       ("integer", INT), ("money_hkd", INT), ("date", DATE)]]}


def write(name, data):
    path = DEST / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n")


def schema(name, body):
    return {"$schema": "https://json-schema.org/draft/2020-12/schema",
            "$id": "https://legalmath.invalid/spec/0.1/" + name, **body}


expressions = [typed_values({"node_id": ID, "op": {"const": "literal"}})]
for op in ["fact", "rule"]:
    expressions.append(obj({"node_id": ID, "op": {"const": op}, "name": ID}))
for op in ["all", "any"]:
    expressions.append(obj({"node_id": ID, "op": {"const": op}, "args": arr(REF, 1)}))
expressions.append(obj({"node_id": ID, "op": {"const": "not"}, "arg": REF}))
for op in ["compare", "add", "sub"]:
    props = {"node_id": ID, "op": {"const": op}, "left": REF, "right": REF}
    if op == "compare":
        props["cmp"] = {"enum": ["eq", "ge", "gt"]}
    expressions.append(obj(props))
expressions.append(obj({"node_id": ID, "op": {"const": "scale"}, "arg": REF,
                        "numerator": {"type": "string", "pattern": "^(0|[1-9][0-9]*)$"},
                        "denominator": {"type": "string", "pattern": "^[1-9][0-9]*$"}}))
expressions.append(obj({"node_id": ID, "op": {"const": "if"}, "condition": REF, "then": REF, "else": REF}))
exception = obj({"exception_id": ID, "guard": REF, "value": REF,
                 "interpretation_id": ID, "source_span_ids": arr(ID, 1)})
expressions.append(obj({"node_id": ID, "op": {"const": "default"}, "base": REF, "exceptions": arr(exception)}))
span = obj({"id": ID, "source_id": STR, "raw_sha256": HASH, "text_sha256": HASH,
            "page": {"type": "integer", "minimum": 1},
            "start": {"type": "integer", "minimum": 0},
            "end": {"type": "integer", "minimum": 1}, "quote_sha256": HASH})
interpretation = obj({"id": ID, "statement": STR,
                      "basis": {"enum": ["source_explicit", "reviewer_interpretation", "bank_policy", "synthetic_test"]},
                      "source_span_ids": arr(ID, 1), "issue_ids": arr(ID)})
bundle = obj({"spec_version": {"const": "0.1"}, "bundle_id": ID,
              "valid_from": TIME, "valid_until": nullable(TIME),
              "source_spans": arr(span, 1), "interpretations": arr(interpretation, 1),
              "facts": arr(obj({"name": ID, "type": TYPES, "description": STR})),
              "rules": arr(obj({"id": ID, "type": TYPES, "scope": REF, "body": REF,
                                 "interpretation_id": ID, "source_span_ids": arr(ID, 1)}), 1)})
bundle["$defs"] = {"expr": {"oneOf": expressions}}
write("rule-bundle.schema.json", schema("rule-bundle", bundle))

known = typed_values({"status": {"const": "known"}, "evidence_ids": arr(ID, 1),
                      "valid_from": TIME, "valid_until": nullable(TIME), "recorded_at": TIME})
unknown = obj({"status": {"const": "unknown"}, "type": TYPES,
               "reason": {"enum": ["MISSING", "STALE", "UNREVIEWED_ASSESSMENT", "ORDER_UNRESOLVED"]}})
conflict = obj({"status": {"const": "conflict"}, "type": TYPES, "evidence_ids": arr(ID, 2)})
snapshot = obj({"subject_id": ID, "facts": {"type": "object", "propertyNames": ID,
                                               "additionalProperties": {"oneOf": [known, unknown, conflict]}}})
write("fact-snapshot.schema.json", schema("fact-snapshot", snapshot))

statuses = ["TRUE", "FALSE", "VALUE", "UNKNOWN", "CONFLICT", "OUT_OF_SCOPE", "ERROR"]
trace = obj({"node_id": ID, "op": STR, "children": arr(ID), "type": nullable(TYPES),
             "status": {"enum": statuses + ["SKIPPED"]},
             "value": {"type": ["boolean", "string"]}, "evidence_ids": arr(ID), "source_span_ids": arr(ID)},
            ["node_id", "op", "children", "type", "status", "evidence_ids", "source_span_ids"])
result = obj({"status": {"enum": statuses}, "type": nullable(TYPES),
              "value": {"type": ["boolean", "string"]}, "reason_codes": arr(STR),
              "mode": {"enum": ["draft", "production", "replay"]},
              "diagnostics": arr(obj({"code": STR, "pointer": {"type": "string"}, "message": STR})),
              "missing_inputs": arr(ID), "blocking_inputs": arr(ID), "trace": arr(trace),
              "bundle_hash": HASH, "snapshot_hash": HASH, "engine_version": STR,
              "valid_at": TIME, "known_at": TIME, "result_hash": HASH},
             ["status", "type", "mode", "diagnostics", "reason_codes", "missing_inputs", "blocking_inputs", "trace",
              "bundle_hash", "snapshot_hash", "engine_version", "valid_at", "known_at", "result_hash"])
result["allOf"] = [
    {"if": {"properties": {"status": {"const": status}}},
     "then": {"properties": {"type": {"const": "bool"}, "value": {"const": value}}, "required": ["value"]}}
    for status, value in [("TRUE", True), ("FALSE", False)]] + [
    {"if": {"properties": {"status": {"const": "VALUE"}}},
     "then": {"properties": {"type": {"enum": ["integer", "money_hkd", "date"]}}, "required": ["value"]}},
    {"if": {"properties": {"status": {"enum": ["UNKNOWN", "CONFLICT", "OUT_OF_SCOPE", "ERROR"]}}},
     "then": {"not": {"required": ["value"]}}},
    {"if": {"properties": {"status": {"const": "VALUE"}, "type": {"enum": ["integer", "money_hkd"]}}},
     "then": {"properties": {"value": {"type": "string", "pattern": "^(0|-?[1-9][0-9]*)$"}}}},
    {"if": {"properties": {"status": {"const": "VALUE"}, "type": {"const": "date"}}},
     "then": {"properties": {"value": {"type": "string", "format": "date"}}}}]
write("evaluation.schema.json", schema("evaluation", result))

AT = "2026-09-01T00:00:00.000000Z"
START = "2023-07-28T00:00:00.000000Z"
raw = ROOT / ".localresources/sfc/23EC35-annex1.pdf"
text = (ROOT / ".localresources/sfc/23EC35-annex1.txt").read_text().removeprefix("\ufeff").replace("\r\n", "\n").replace("\r", "\n")
start = text.index("3.1 An SPI should")
end = text.index("3.2 When", start)
needle = text[start:end]
anchor = {"id": "spi.annex1.3.1", "source_id": "23EC35/annex1",
          "raw_sha256": hashlib.sha256(raw.read_bytes()).hexdigest(),
          "text_sha256": hashlib.sha256(text.encode()).hexdigest(),
          "page": text[:start].count("\f") + 1, "start": start, "end": start + len(needle),
          "quote_sha256": hashlib.sha256(needle.encode()).hexdigest()}
write("fixtures/source-anchor.json", {"span": anchor,
      "raw_path": ".localresources/sfc/23EC35-annex1.pdf", "text_path": ".localresources/sfc/23EC35-annex1.txt"})


def lit(node, value, typ="bool"):
    return {"node_id": node, "op": "literal", "type": typ, "value": value}


def fact(node, name):
    return {"node_id": node, "op": "fact", "name": name}


def compare(node, left, right, cmp="ge"):
    return {"node_id": node, "op": "compare", "cmp": cmp, "left": left, "right": right}


def make_bundle(name, declarations, body, typ="bool", scope=None, synthetic=True):
    return {"spec_version": "0.1", "bundle_id": name, "valid_from": START, "valid_until": None,
            "source_spans": [anchor], "interpretations": [{"id": "meaning.main",
            "statement": "Synthetic language conformance example; not an additional SFC rule." if synthetic else
                         "Annex 1 paragraph 3.1 financial subcondition only; wealth definitions, applicability and legal effectiveness require review. The validity interval is a synthetic test setting.",
            "basis": "synthetic_test" if synthetic else "reviewer_interpretation",
            "source_span_ids": [anchor["id"]], "issue_ids": [] if synthetic else
                ["issue.wealth_definitions", "issue.applicability", "issue.effective_interval"]}],
            "facts": [{"name": k, "type": t, "description": k} for k, t in declarations],
            "rules": [{"id": name, "type": typ, "scope": scope or lit("scope.true", True),
                       "body": body, "interpretation_id": "meaning.main", "source_span_ids": [anchor["id"]]}]}


financial = make_bundle("spi.financial", [("portfolio", "money_hkd"), ("net_assets_ex_home", "money_hkd")],
    {"node_id": "financial.or", "op": "any", "args": [
        compare("portfolio.ge", fact("portfolio.input", "portfolio"), lit("portfolio.threshold", "4000000000", "money_hkd")),
        compare("assets.ge", fact("assets.input", "net_assets_ex_home"), lit("assets.threshold", "8000000000", "money_hkd"))]}, synthetic=False)
write("fixtures/spi-financial.bundle.json", financial)


def entry(value, typ="money_hkd"):
    if value is None:
        return {"status": "unknown", "type": typ, "reason": "MISSING"}
    if value == "CONFLICT":
        return {"status": "conflict", "type": typ, "evidence_ids": ["evidence.one", "evidence.two"]}
    return {"status": "known", "type": typ, "value": value,
            "evidence_ids": ["evidence.synthetic"], "valid_from": START,
            "valid_until": None, "recorded_at": AT}


cases = []


def case(name, b, facts, status, value=None, reasons=None, mutation=None):
    expected = {"status": status}
    if value is not None:
        expected["value"] = value
    if reasons:
        expected["reason_codes_include"] = reasons
    cases.append({"id": name, "bundle": b, "rule_id": b["rules"][0]["id"],
                  "snapshot": {"subject_id": "synthetic.client", "facts": facts},
                  "valid_at": AT, "known_at": AT, "expected": expected,
                  "mutation_detected": mutation, "basis": "engineering_conformance"})


for name, p, n, status, mutation in [
    ("f01", "4000000000", "0", "TRUE", "ge_to_gt"),
    ("f02", "3999999999", "0", "FALSE", "round_to_whole_dollars"),
    ("f03", "0", "8000000000", "TRUE", "or_to_and"),
    ("f04", "0", "7999999999", "FALSE", "assets_ge_to_gt_or_round"),
    ("f05", "4100000000", "8100000000", "TRUE", None),
    ("f06", None, "9000000000", "TRUE", "unknown_always_blocks"),
    ("f07", None, "7000000000", "UNKNOWN", "unknown_to_zero"),
    ("f08", "4100000000", None, "TRUE", "unknown_always_blocks"),
    ("f09", "3900000000", None, "UNKNOWN", "unknown_to_zero"),
    ("f10", None, None, "UNKNOWN", "unknown_to_false"),
    ("f11", "0", "-1", "FALSE", None),
    ("f12", "CONFLICT", "9000000000", "CONFLICT", "ignore_conflict_on_other_route")]:
    case(name, financial, {"portfolio": entry(p), "net_assets_ex_home": entry(n)}, status,
         True if status == "TRUE" else False if status == "FALSE" else None,
         ["INPUT_CONFLICT"] if status == "CONFLICT" else None, mutation)

for op, values in [("all", [(False, None, "FALSE"), (True, None, "UNKNOWN"), (True, True, "TRUE")]),
                   ("any", [(True, None, "TRUE"), (False, None, "UNKNOWN"), (False, False, "FALSE")])]:
    for index, (a, b, status) in enumerate(values):
        bund = make_bundle("logic." + op, [("a", "bool"), ("b", "bool")],
                           {"node_id": "combine", "op": op, "args": [fact("a.ref", "a"), fact("b.ref", "b")]})
        case(f"logic.{op}.{index}", bund, {"a": entry(a, "bool"), "b": entry(b, "bool")}, status)
for a, status in [(True, "FALSE"), (False, "TRUE"), (None, "UNKNOWN")]:
    bund = make_bundle("logic.not", [("a", "bool")], {"node_id": "neg", "op": "not", "arg": fact("a.ref", "a")})
    case("logic.not." + str(a).lower(), bund, {"a": entry(a, "bool")}, status)
excluded_middle = make_bundle("logic.excluded_middle", [("a", "bool")], {"node_id": "or", "op": "any", "args": [
    fact("a.ref", "a"), {"node_id": "neg", "op": "not", "arg": fact("a.ref2", "a")}]})
case("logic.excluded_middle", excluded_middle, {"a": entry(None, "bool")}, "UNKNOWN", mutation="classical_completion_substitution")

for a, b, status, value in [(False, False, "VALUE", "0"), (True, False, "VALUE", "10"),
                           (False, True, "VALUE", "10"), (True, True, "CONFLICT", None),
                           (None, False, "UNKNOWN", None), (True, None, "UNKNOWN", None)]:
    body = {"node_id": "default", "op": "default", "base": lit("base", "0", "integer"), "exceptions": [
        {"exception_id": k, "guard": fact(k + ".guard", k), "value": lit(k + ".value", "10", "integer"),
         "interpretation_id": "meaning.main", "source_span_ids": [anchor["id"]]} for k in ["a", "b"]]}
    bund = make_bundle("exception.test", [("a", "bool"), ("b", "bool")], body, "integer")
    case("exception." + str(a).lower() + "." + str(b).lower(), bund,
         {"a": entry(a, "bool"), "b": entry(b, "bool")}, status, value,
         ["MULTIPLE_EXCEPTIONS"] if status == "CONFLICT" else None)
for condition, status in [(False, "OUT_OF_SCOPE"), (None, "UNKNOWN")]:
    bund = deepcopy(financial)
    bund["facts"].append({"name": "scope", "type": "bool", "description": "Synthetic scope"})
    bund["rules"][0]["scope"] = fact("scope.ref", "scope")
    case("scope." + str(condition).lower(), bund, {"scope": entry(condition, "bool"),
         "portfolio": entry("5000000000"), "net_assets_ex_home": entry("0")}, status)
for money, denom, status, value in [("100", "2", "VALUE", "50"), ("101", "2", "ERROR", None)]:
    bund = make_bundle("money.scale", [], {"node_id": "scale", "op": "scale",
        "arg": lit("amount", money, "money_hkd"), "numerator": "1", "denominator": denom}, "money_hkd")
    case("scale." + money, bund, {}, status, value, ["E_INEXACT_SCALE"] if status == "ERROR" else None)
body = {"node_id": "net", "op": "sub", "left": {"node_id": "less_liabilities", "op": "sub",
        "left": lit("assets", "12000000000", "money_hkd"), "right": lit("liabilities", "1500000000", "money_hkd")},
        "right": lit("home", "3000000000", "money_hkd")}
case("net_assets.example", make_bundle("net.assets", [], body, "money_hkd"), {}, "VALUE", "7500000000", mutation="omit_primary_home")
ifbody = {"node_id": "choose", "op": "if", "condition": fact("condition", "a"),
          "then": lit("yes", True), "else": lit("no", True)}
case("if.unknown_equal_branches", make_bundle("if.test", [("a", "bool")], ifbody), {"a": entry(None, "bool")}, "UNKNOWN")
expired = deepcopy(cases[0])
expired["id"] = "time.version"
expired["bundle"]["valid_until"] = AT
expired["expected"] = {"status": "ERROR", "reason_codes_include": ["E_VERSION_TIME"]}
cases.append(expired)
write("fixtures/decision-cases.json", {"description": "Expected projections, not full response objects. All values synthetic; normative interpretations unapproved.", "cases": cases})

invalid = []
for ident, path, value, stage, code in [
    ("unknown_operator", ["rules", 0, "body", "op"], "python_eval", "schema", "E_SCHEMA"),
    ("money_float", ["rules", 0, "body", "args", 0, "right", "value"], 4000000000.0, "schema", "E_SCHEMA"),
    ("negative_zero", ["rules", 0, "body", "args", 0, "right", "value"], "-0", "schema", "E_SCHEMA"),
    ("missing_fact", ["rules", 0, "body", "args", 0, "left", "name"], "absent", "semantic", "E_REFERENCE"),
    ("wrong_type", ["facts", 0, "type"], "date", "semantic", "E_TYPE"),
    ("duplicate_node", ["rules", 0, "body", "args", 1, "node_id"], "portfolio.ge", "semantic", "E_DUPLICATE_ID")]:
    invalid.append({"id": ident, "base": "spi-financial.bundle.json", "path": path, "replacement": value,
                    "rejected_at": stage, "expected_code": code})
write("fixtures/invalid-cases.json", invalid)

event_cases = [
 {"id": "consent.withdraw", "profile": "consent", "initial": "NOT_ESTABLISHED",
  "events": [{"kind": "consent.granted", "sequence": 1}, {"kind": "consent.withdrawn", "sequence": 2}],
  "expected": {"state": "WITHDRAWN", "generation": 1}},
 {"id": "consent.regrant", "profile": "consent", "initial": "NOT_ESTABLISHED",
  "events": [{"kind": "consent.granted", "sequence": 1}, {"kind": "consent.withdrawn", "sequence": 2}, {"kind": "consent.granted", "sequence": 3}],
  "expected": {"state": "ACTIVE", "generation": 2}},
]
for ident, performed, watermark, status, breached in [
 ("on_time", "2026-09-01T23:59:59.999999Z", "2026-09-02T00:00:00.000000Z", "SATISFIED_ON_TIME", False),
 ("at_deadline", "2026-09-02T00:00:00.000000Z", "2026-09-02T00:00:00.000000Z", "PERFORMED_LATE", True),
 ("no_record_incomplete", None, None, "OPEN", False),
 ("no_record_complete", None, "2026-09-02T00:00:00.000000Z", "BREACHED", True),
 ("before_activation", "2026-08-31T23:59:59.000000Z", "2026-09-02T00:00:00.000000Z", "BREACHED", True),
 ("late_performance", "2026-09-03T00:00:00.000000Z", "2026-09-03T00:00:00.000000Z", "PERFORMED_LATE", True)]:
    events = [{"kind": "obligation.opened", "occurred_at": AT, "activation": AT,
               "deadline": "2026-09-02T00:00:00.000000Z", "sequence": 1}]
    if performed:
        events.append({"kind": "obligation.performed", "occurred_at": performed, "sequence": 2})
    if watermark:
        events.append({"kind": "watermark", "occurred_at": watermark, "complete_through": watermark, "sequence": 3})
    event_cases.append({"id": "duty." + ident, "profile": "achievement", "events": events,
                        "expected": {"status": status, "breached": breached}})
for c in event_cases:
    c.update({"stream_id": "synthetic.stream", "ordering_authority": "synthetic.connector",
              "valid_at": "2026-09-04T00:00:00.000000Z", "known_at": "2026-09-04T00:00:00.000000Z"})
    c["stream_header"] = {"inception": "2026-08-31T00:00:00.000000Z",
                          "subject": "synthetic.client", "category": "synthetic.category",
                          "profile_version": "0.1", "ordering_authority": "synthetic.connector"}
    if c["profile"] == "consent":
        c["completeness"] = {"complete_from": c["stream_header"]["inception"],
                             "complete_through": c["valid_at"], "recorded_at": c["known_at"],
                             "evidence_id": c["id"] + ".stream-completeness"}
    for e in c["events"]:
        e.update({"id": c["id"] + ".e" + str(e["sequence"]), "stream_id": c["stream_id"],
                  "recorded_at": "2026-09-04T00:00:00.000000Z", "actor": "synthetic.bank",
                  "action": "synthetic.review", "subject": "synthetic.client", "category": "synthetic.category",
                  "evidence_id": c["id"] + ".evidence" + str(e["sequence"]), "obligation_id": "synthetic.duty"})
        e.setdefault("occurred_at", "2026-09-01T00:00:0" + str(e["sequence"]) + ".000000Z")
write("fixtures/event-cases.json", event_cases)
release_cases = [
 {"id": "release.good", "state": "APPROVED", "author": "author", "meaning_reviewer": "legal", "implementation_reviewer": "eng", "issues": 0, "dependencies": 0, "evidence_matches": True, "expected": "RELEASED"},
 {"id": "release.self_review", "state": "APPROVED", "author": "legal", "meaning_reviewer": "legal", "implementation_reviewer": "eng", "issues": 0, "dependencies": 0, "evidence_matches": True, "expected": "E_RELEASE_BLOCKED"},
 {"id": "release.open_issue", "state": "APPROVED", "author": "author", "meaning_reviewer": "legal", "implementation_reviewer": "eng", "issues": 1, "dependencies": 0, "evidence_matches": True, "expected": "E_RELEASE_BLOCKED"},
 {"id": "release.stale_evidence", "state": "APPROVED", "author": "author", "meaning_reviewer": "legal", "implementation_reviewer": "eng", "issues": 0, "dependencies": 0, "evidence_matches": False, "expected": "E_RELEASE_BLOCKED"}]
for c in release_cases:
    c["premises"] = {"explicit_effective_interval": True, "applicable_scope_reviewed": True,
                     "source_hashes_valid": True, "evidence_report_passes": True,
                     "expected_revision_matches": True, "no_overlapping_release": True}
write("fixtures/release-cases.json", release_cases)
print(json.dumps({"decision_cases": len(cases), "invalid_cases": len(invalid), "event_cases": len(event_cases), "schemas": 3}))
