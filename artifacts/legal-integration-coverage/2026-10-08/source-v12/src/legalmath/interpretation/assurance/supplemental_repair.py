"""Bounded supplemental investigation without resetting historical evidence."""
from collections import Counter
from copy import deepcopy
from datetime import datetime, timezone
import fcntl
from itertools import product
from pathlib import Path
import re
import time
from typing import Literal

from pydantic import Field
from ...canonical import canonical, digest, loads, raw_digest
from ...errors import LegalMathError
from ..contracts import Strict, parse
from ..search.models import Quote, Formalization, Reading, commitment
from . import conditional_elimination as logic
from .challenge_contract import DIMENSIONS
from .semantics import check_quotes
from .diversity import save

PROFILE = "legalmath.supplemental-assurance.v1"
POOL_V1 = "legalmath.exact-context-pool.v1"
POOL = "legalmath.exact-context-pool.v2"
PHASE_LIMITS = {"coverage": 12, "assessment": 40, "authority": 8, "integration": 24}
MAXIMUM = 100
RESERVE = 16


def fail(code, reason):
    raise LegalMathError(code, details=reason)


def encode(request):
    """Pool repeated strings, leaving the complete source literal."""
    if "context_encoding" in request or "context_texts" in request:
        fail("E_SCHEMA", "Reserved context encoding field")
    counts = Counter()
    def count(value):
        if isinstance(value, str):
            if len(value) >= 24:
                counts[value] += 1
        elif isinstance(value, dict):
            if set(value) == {"text_ref"} or set(value) in (
                    {"record_columns","record_rows"},{"record_columns","record_entries"}):
                fail("E_SCHEMA", "Ambiguous original context reference")
            for v in value.values():
                count(v)
        elif isinstance(value, list):
            for v in value:
                count(v)
    for k, value in request.items():
        if k != "source_packet":
            count(value)
    texts = [s for s, n in counts.items() if n > 1 and (n-1)*len(s) > n*22]
    indices = {s: i for i, s in enumerate(texts)}
    def visit(value):
        if isinstance(value, str) and value in indices:
            return {"text_ref": indices[value]}
        if isinstance(value, dict):
            result={k: visit(v) for k, v in value.items()}
            records=list(result.values())
            if len(records)>=2 and all(isinstance(v,dict) for v in records):
                columns=list(records[0])
                if columns and all(set(v)==set(columns) for v in records):
                    table={"record_columns":columns,
                           "record_entries":{k:[v[c] for c in columns] for k,v in result.items()}}
                    if len(canonical(table))<len(canonical(result)):return table
            return result
        if isinstance(value, list):
            result=[visit(v) for v in value]
            if len(result)>=2 and all(isinstance(v,dict) for v in result):
                columns=list(result[0])
                if columns and all(set(v)==set(columns) for v in result):
                    table={"record_columns":columns,"record_rows":[[v[c] for c in columns] for v in result]}
                    if len(canonical(table))<len(canonical(result)):return table
            return result
        return deepcopy(value)
    wire = {k: deepcopy(v) if k == "source_packet" else visit(v) for k, v in request.items()}
    wire["context_texts"] = texts
    wire["context_encoding"] = {
        "profile": POOL,
        "instructions": (
            "The complete source_packet is literal. Elsewhere an object with ONLY text_ref "
            "means the exact full string context_texts[text_ref], indexed from zero. "
            "An object with ONLY record_columns and record_rows is a list of records: "
            "each row supplies values for the named columns in order. An object with "
            "ONLY record_columns and record_entries is a dictionary of records: each "
            "entry key remains its original ID and its row supplies those column values. "
            "These tables nest recursively and preserve every field and value. "
            "Resolve recursively before interpreting the task; these are not summaries. "
            "Read all candidates and original questions, including unselected context. "
            "Return ordinary strings and the original literal identities, never text_ref objects. "
            "Do not calculate hashes. This encoding conveys no legal authority."
        ),
    }
    if decode(wire, digest(request)) != request:
        fail("E_INTEGRITY", "Exact context round trip changed the request")
    return wire


def decode(wire, expected_hash):
    value = deepcopy(wire)
    marker = value.pop("context_encoding", None)
    if not isinstance(marker, dict) or marker.get("profile") not in (POOL_V1,POOL):
        fail("E_INTEGRITY", "Unknown context encoding")
    texts = value.pop("context_texts", None)
    if not isinstance(texts, list) or any(not isinstance(t, str) for t in texts) or len(set(texts)) != len(texts):
        fail("E_INTEGRITY", "Invalid context text pool")
    used = set()
    def visit(v):
        if isinstance(v, dict):
            if marker["profile"]==POOL and set(v) in (
                    {"record_columns","record_rows"},{"record_columns","record_entries"}):
                columns=v["record_columns"]
                if (not isinstance(columns,list) or not columns or
                        any(not isinstance(c,str) for c in columns) or len(set(columns))!=len(columns)):
                    fail("E_INTEGRITY","Invalid record table columns")
                def record(row):
                    if not isinstance(row,list) or len(row)!=len(columns):
                        fail("E_INTEGRITY","Invalid record table row")
                    return visit(dict(zip(columns,row)))
                if "record_rows" in v:
                    if not isinstance(v["record_rows"],list):fail("E_INTEGRITY","Invalid record table")
                    return [record(row) for row in v["record_rows"]]
                if not isinstance(v["record_entries"],dict):fail("E_INTEGRITY","Invalid record entries")
                return {k:record(row) for k,row in v["record_entries"].items()}
            if set(v) == {"text_ref"}:
                index = v["text_ref"]
                if type(index) is not int or not 0 <= index < len(texts):
                    fail("E_INTEGRITY", "Invalid pooled text index")
                used.add(index)
                return texts[index]
            return {k: visit(x) for k, x in v.items()}
        if isinstance(v, list):
            return [visit(x) for x in v]
        return v
    result = {k: v if k == "source_packet" else visit(v) for k, v in value.items()}
    if used != set(range(len(texts))) or digest(result) != expected_hash:
        fail("E_INTEGRITY", "Context differs from the independently held original")
    return result


def spending_key(key):
    if key.startswith(("coverage.", "integration.")):
        return "challenge." + key.split(".", 1)[1]
    return key


class SupplementalAllowance:
    """One explicit supplemental authorization, independent of unused old quota."""

    def __init__(self, authorization, *, task=None, phase=None, issues=(), repair=False):
        self.grant_path = Path(authorization).resolve()
        self.grant_bytes = self.grant_path.read_bytes()
        self.grant = loads(self.grant_bytes)
        if (self.grant.get("profile") != PROFILE or self.grant.get("maximum") != MAXIMUM
                or not self.grant.get("authorization") or not self.grant.get("predecessors")
                or self.grant.get("ledger") != "allowance.json"
                or self.grant.get("phase_limits") != PHASE_LIMITS
                or self.grant.get("repair_reserve") != RESERVE
                or self.grant.get("maximum_new_attempts_per_issue") != 2):
            fail("E_AUTHORITY", "Invalid supplemental authorization")
        self.path = self.grant_path.parent / self.grant["ledger"]
        self.maximum = MAXIMUM
        self.task, self.phase, self.issues, self.repair = task, phase, tuple(sorted(issues)), repair
        self.verify()

    def _load(self):
        return loads(self.path.read_bytes()) if self.path.exists() else {
            "authorization_hash": raw_digest(self.grant_bytes), "maximum": MAXIMUM, "calls": []}

    def verify(self):
        if self.grant_path.read_bytes() != self.grant_bytes:
            fail("E_INTEGRITY", "Authorization changed")
        for ref in self.grant["predecessors"]:
            p = self.grant_path.parent / ref["path"]
            if raw_digest(p.read_bytes()) != ref["sha256"]:
                fail("E_INTEGRITY", "Historical checkpoint changed")
        value = self._load()
        if (set(value) != {"authorization_hash", "maximum", "calls"}
                or value["authorization_hash"] != raw_digest(self.grant_bytes)
                or value["maximum"] != MAXIMUM or not isinstance(value["calls"], list)
                or len(value["calls"]) > MAXIMUM):
            fail("E_INTEGRITY", "Supplemental ledger changed")
        spent = Counter()
        phases = Counter()
        repairs = 0
        for slot, row in enumerate(value["calls"], 1):
            if (set(row) != {"slot", "request_hash", "issued_at_ns", "task", "phase", "issues", "repair"}
                    or row["slot"] != slot or not re.fullmatch("[0-9a-f]{64}", row["request_hash"])
                    or not str(row["issued_at_ns"]).isdigit()
                    or row["phase"] not in PHASE_LIMITS or type(row["repair"]) is not bool
                    or not row["issues"] or len(set(row["issues"])) != len(row["issues"])):
                fail("E_INTEGRITY", "Invalid supplemental reservation")
            spent.update(spending_key(k) for k in row["issues"])
            if row["repair"]:
                repairs += 1
            else:
                phases[row["phase"]] += 1
        if any(n > 2 for n in spent.values()) or repairs > RESERVE or any(
                n > PHASE_LIMITS[p] for p, n in phases.items()):
            fail("E_INTEGRITY", "Recorded supplemental limit exceeded")
        return {"used": len(value["calls"]), "maximum": MAXIMUM, "phases": dict(phases),
                "repair_calls": repairs, "issue_spending": dict(spent),
                "authorization_hash": raw_digest(self.grant_bytes)}

    def reserve(self, request_hash):
        if (not isinstance(request_hash, str) or not re.fullmatch("[0-9a-f]{64}", request_hash)
                or not self.task or self.phase not in PHASE_LIMITS or not self.issues
                or len(set(self.issues)) != len(self.issues)
                or not set(self.issues) <= set(self.grant.get("allowed_issues", []))):
            fail("E_AUTHORITY", "Call is outside a declared task")
        with self.path.with_suffix(".lock").open("a") as lock:
            fcntl.flock(lock, fcntl.LOCK_EX)
            status = self.verify()
            if datetime.now(timezone.utc) >= datetime.fromisoformat(self.grant["ends_at"]):
                fail("E_RESOURCE_LIMIT", "Supplemental execution window expired")
            if status["used"] >= MAXIMUM or any(status["issue_spending"].get(spending_key(k), 0) >= 2 for k in self.issues):
                fail("E_RESOURCE_LIMIT", "Supplemental total or issue ceiling exhausted")
            if self.repair:
                if status["repair_calls"] >= RESERVE:
                    fail("E_RESOURCE_LIMIT", "Supplemental repair reserve exhausted")
            elif status["phases"].get(self.phase, 0) >= PHASE_LIMITS[self.phase]:
                fail("E_RESOURCE_LIMIT", "Supplemental phase ceiling exhausted")
            value = self._load()
            slot = len(value["calls"]) + 1
            value["calls"].append({"slot": slot, "request_hash": request_hash,
                "issued_at_ns": str(time.time_ns()), "task": self.task, "phase": self.phase,
                "issues": list(self.issues), "repair": self.repair})
            save(self.path, value)
            return slot


class DimensionReview(Strict):
    dimension: Literal["actor", "scope", "quantifier", "negation", "exception", "time", "definition", "authority", "output"]
    status: Literal["PROPOSED_SUPPORTED", "CHALLENGED", "OPEN"]
    evidence: list[Quote] = Field(max_length=3)
    explanation: str = Field(min_length=1, max_length=3000)


class Premise(Strict):
    when: str = Field(min_length=1, max_length=4000)
    expected: bool
    evidence: list[Quote] = Field(min_length=1, max_length=4)
    rationale: str = Field(min_length=1, max_length=3000)


class Assessment(Strict):
    reading_id: str
    reading_hash: str
    disposition: Literal["CONDITIONAL_FORMALIZATION", "QUALIFIED_UNFORMALIZED", "CHALLENGED"]
    dimensions: list[DimensionReview] = Field(min_length=9, max_length=9)
    formalization: Formalization | None
    premises: list[Premise] = Field(max_length=8)
    added_assumptions: list[str] = Field(max_length=12)
    unresolved_questions: list[str] = Field(max_length=12)
    related_readings: list[str] = Field(max_length=12)
    relationship_explanation: str = Field(min_length=1, max_length=3000)


class AssessmentResponse(Strict):
    binding_hash: str
    assessments: list[Assessment] = Field(min_length=1, max_length=3)
    newly_proposed_readings: list[Reading] = Field(max_length=2)


def validate_assessment(value, binding, packet, candidates, selected):
    value = parse(AssessmentResponse, value)
    if value["binding_hash"] != binding:
        fail("E_REFERENCE", "Assessment response has wrong binding identity")
    rows = value["assessments"]
    if len(rows) != len(selected) or {r["reading_id"] for r in rows} != set(selected):
        fail("E_REFERENCE", "Missing, duplicated or foreign reading assessment")
    known_units = {u["unit_id"] for u in packet["units"]}
    for row in rows:
        reading = candidates[row["reading_id"]]
        if row["reading_hash"] != commitment(reading):
            fail("E_REFERENCE", "Assessment attached to a different reading")
        if {d["dimension"] for d in row["dimensions"]} != set(DIMENSIONS):
            fail("E_REFERENCE", "Missing or repeated assessment dimension")
        for finding in row["dimensions"]:
            check_quotes(finding["evidence"], packet)
            if finding["status"] != "OPEN" and not finding["evidence"]:
                fail("E_REFERENCE", "Substantive dimension finding lacks source evidence")
        if not set(row["related_readings"]) <= set(candidates):
            fail("E_REFERENCE", "Unknown related reading")
        formal = row["formalization"]
        if formal is None:
            if row["premises"] or row["disposition"] == "CONDITIONAL_FORMALIZATION" or not row["unresolved_questions"]:
                fail("E_REFERENCE", "Unformalized assessment has no explicit unresolved frontier")
            continue
        names = logic.names_checked([f["name"] for f in formal["facts"]])
        if formal["result_type"] != "bool" or any(f["type"] != "bool" for f in formal["facts"]):
            fail("E_UNSUPPORTED_PROFILE", "This increment declares only total Boolean formalizations")
        if any(not set(f["source_unit_ids"]) <= known_units for f in formal["facts"]):
            fail("E_REFERENCE", "Formal fact cites an unknown source unit")
        logic.parse_boolean(formal["scope"], names)
        logic.parse_boolean(formal["result"], names)
        if len(row["premises"]) < 2 or {p["expected"] for p in row["premises"]} != {False, True}:
            fail("E_REFERENCE", "Formalization requires independent positive and negative obligations")
        for premise in row["premises"]:
            check_quotes(premise["evidence"], packet)
            guard = logic.parse_boolean(premise["when"], names)
            scope = logic.parse_boolean(formal["scope"], names)
            assignments = [dict(zip(names, values)) for values in product((False, True), repeat=len(names))]
            if not any(logic.evaluate(guard, a) for a in assignments):
                fail("E_REFERENCE", "Formal premise has an unsatisfiable guard")
            if any(logic.evaluate(guard, a) and not logic.evaluate(scope, a) for a in assignments):
                fail("E_REFERENCE", "Formal premise must explicitly include its scope")
    for reading in value["newly_proposed_readings"]:
        check_quotes(reading["citations"], packet)
    return value


def formal_evidence(packet, reading, question, assessment):
    derived = deepcopy(reading)
    derived["formalization"] = assessment["formalization"]
    derived["assumptions"] = list(dict.fromkeys([*reading["assumptions"], *assessment["added_assumptions"]]))
    derived["questions"] = list(dict.fromkeys([*reading["questions"], *assessment["unresolved_questions"]]))
    obligations = [{"obligation_id": "supplemental." + digest(p), "packet_hash": digest(packet),
        "question_hash": digest(question), "when": p["when"], "expected": p["expected"],
        "evidence": p["evidence"], "premise_status": "PROPOSED_FORMAL_PREMISE",
        "rationale": p["rationale"]} for p in assessment["premises"]]
    certificate = logic.check(packet, derived, question, obligations)
    logic.verify(certificate, packet, derived, question, obligations)
    return {"original_reading_hash": commitment(reading), "derived_reading": derived,
            "question": question, "obligations": obligations, "certificate": certificate,
            "source_entailment": "NOT_ESTABLISHED", "original_reading_replaced": False}
