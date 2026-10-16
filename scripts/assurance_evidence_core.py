"""Bounded successor accounting, source locators, and response validation."""
from collections import Counter
from copy import deepcopy
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Literal
import fcntl
import json
import os
import re
import tempfile

from pydantic import Field
from legalmath.canonical import canonical, digest, raw_digest
from legalmath.errors import LegalMathError
from legalmath.interpretation.contracts import Strict, parse
from legalmath.interpretation.assurance.semantics import check_quotes
from legalmath.interpretation.assurance import supplemental_repair as repair
from legalmath.interpretation.search.models import Quote

BASE = Path("artifacts/assurance-gap-continuation/2026-10-02")
OLD = Path("artifacts/assurance-gap-continuation/2026-10-01")
PLAN = Path("docs/plans/assurance-evidence-closure-100-calls.md")
LIMITS = {"P1": 24, "P2": 16, "P3": 36, "P4": 8}
ROLES = ("structure-reader", "exception-challenger")
PROFILE = "legalmath.evidence-closure-master.v1"
BRIDGE_ID = "node.210068a368d2d851d97f6b2c"

def now():
    return datetime.now(timezone.utc).isoformat()

def fail(code, detail):
    raise LegalMathError(code, details=detail)

def read(path):
    def unique(pairs):
        value = {}
        for k, v in pairs:
            if k in value:
                fail("E_INTEGRITY", "Duplicate JSON field")
            value[k] = v
        return value
    return json.loads(Path(path).read_text(), object_pairs_hook=unique,
                      parse_constant=lambda x: fail("E_SCHEMA", "Nonfinite JSON"))

def write_text(path, text):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp = tempfile.mkstemp(prefix=path.name+".tmp.", dir=path.parent)
    try:
        with os.fdopen(fd, "w") as stream:
            stream.write(text)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temp, path)
        fd = os.open(path.parent, os.O_RDONLY)
        try:
            os.fsync(fd)
        finally:
            os.close(fd)
    finally:
        if os.path.exists(temp):
            os.unlink(temp)

def save(path, value):
    write_text(path, json.dumps(value, indent=2, ensure_ascii=False)+"\n")

def receipt(path, root):
    return {"path": str(Path(path).resolve().relative_to(Path(root).resolve())),
            "sha256": raw_digest(Path(path).read_bytes())}

def checked(ref, root):
    path = (Path(root)/ref["path"]).resolve()
    if not path.is_relative_to(Path(root).resolve()) or raw_digest(path.read_bytes()) != ref["sha256"]:
        fail("E_INTEGRITY", "Changed or foreign receipt: "+ref["path"])
    return path

def code_material(root):
    names = [p for folder in ("src", "scripts", "tests") for p in (Path(root)/folder).rglob("*")
             if p.is_file() and not any(part in ("__pycache__", ".pytest_cache") for part in p.parts) and p.suffix not in (".pyc", ".pyo")]
    return {str(p.relative_to(root)): raw_digest(p.read_bytes()) for p in sorted(names)}

class EvidenceAllowance:
    """The append-only reservation journal is authoritative; a crash never refunds."""
    maximum = 100
    def __init__(self, root, task=None, phase=None, issues=(), correction=False):
        self.root = Path(root)
        self.grant_path = self.root/BASE/"authorization.json"
        self.grant_bytes = self.grant_path.read_bytes()
        self.grant = read(self.grant_path)
        self.path = self.grant_path.parent/"allowance.json"
        self.journal = self.path.parent/"reservations"
        self.task, self.phase = task, phase
        self.issues, self.correction = tuple(sorted(issues)), correction
        self.verify()

    def _load(self):
        entries = sorted(self.journal.glob("*.json"))
        rows, previous = [], raw_digest(self.grant_bytes)
        start = None
        for i, path in enumerate(entries, 1):
            row = read(path)
            if path.name != f"{i:04}.json" or row["previous_hash"] != previous:
                fail("E_INTEGRITY", "Reservation journal missing or changed")
            previous = digest(row)
            rows.append(row["call"])
            start = start or row["call"]["issued_at"]
        value = {"authorization_hash": raw_digest(self.grant_bytes), "maximum": 100,
                 "starts_at": start,
                 "ends_at": (datetime.fromisoformat(start)+timedelta(hours=48)).isoformat() if start else None,
                 "calls": rows}
        if self.path.exists():
            old = read(self.path)
            prefix = old.get("calls", [])
            if (old.get("authorization_hash") != value["authorization_hash"] or old.get("maximum") != 100
                    or len(prefix) > len(rows) or prefix != rows[:len(prefix)]
                    or (prefix and (old.get("starts_at") != value["starts_at"] or old.get("ends_at") != value["ends_at"]))):
                fail("E_INTEGRITY", "Ledger/journal mismatch")
        return value

    def verify(self):
        g = self.grant
        if (self.grant_path.read_bytes() != self.grant_bytes or g["profile"] != PROFILE
                or g["maximum"] != 100 or g["phase_limits"] != LIMITS or g["repair_reserve"] != 16
                or g["maximum_attempts_per_issue"] != 2 or g["window_hours"] != 48
                or len(g["allowed_issues"]) != len(set(g["allowed_issues"]))):
            fail("E_AUTHORITY", "Changed/invalid successor authorization")
        for ref in g["predecessors"]:
            checked(ref, self.root)
        ledger = self._load()
        counts, phases, repairs = Counter(), Counter(), 0
        for i, row in enumerate(ledger["calls"], 1):
            if (row["slot"] != i or row["phase"] not in LIMITS or not row["issues"]
                    or len(set(row["issues"])) != len(row["issues"])
                    or not set(row["issues"]) <= set(g["allowed_issues"])
                    or type(row["repair"]) is not bool
                    or not re.fullmatch("[0-9a-f]{64}", row["request_hash"])):
                fail("E_INTEGRITY", "Invalid reservation")
            at = datetime.fromisoformat(row["issued_at"])
            if not datetime.fromisoformat(ledger["starts_at"]) <= at < datetime.fromisoformat(ledger["ends_at"]):
                fail("E_INTEGRITY", "Reservation outside authorized window")
            counts.update(row["issues"])
            if row["repair"]:
                repairs += 1
            else:
                phases[row["phase"]] += 1
        if (len(ledger["calls"]) > 100 or repairs > 16 or any(n > 2 for n in counts.values())
                or any(n > LIMITS[p] for p, n in phases.items())):
            fail("E_INTEGRITY", "Recorded quota exceeded")
        return {"used": len(ledger["calls"]), "maximum": 100, "phases": dict(phases),
                "repair_calls": repairs, "issue_spending": dict(counts),
                "starts_at": ledger["starts_at"], "ends_at": ledger["ends_at"]}

    def reserve(self, request_hash):
        if (not self.task or self.phase not in LIMITS or not self.issues
                or len(set(self.issues)) != len(self.issues)
                or not set(self.issues) <= set(self.grant["allowed_issues"])
                or not re.fullmatch("[0-9a-f]{64}", request_hash)):
            fail("E_AUTHORITY", "Undeclared call")
        with self.path.with_suffix(".lock").open("a") as lock:
            fcntl.flock(lock, fcntl.LOCK_EX)
            status, ledger = self.verify(), self._load()
            at = datetime.now(timezone.utc)
            if ledger["ends_at"] and at >= datetime.fromisoformat(ledger["ends_at"]):
                fail("E_RESOURCE_LIMIT", "Successor live window expired")
            if status["used"] >= 100 or any(status["issue_spending"].get(i, 0) >= 2 for i in self.issues):
                fail("E_RESOURCE_LIMIT", "Total or canonical issue attempts exhausted")
            if self.correction:
                if status["repair_calls"] >= 16:
                    fail("E_RESOURCE_LIMIT", "Repair reserve exhausted")
            elif status["phases"].get(self.phase, 0) >= LIMITS[self.phase]:
                fail("E_RESOURCE_LIMIT", "Phase allocation exhausted")
            slot = len(ledger["calls"])+1
            self.journal.mkdir(exist_ok=True)
            previous = digest(read(self.journal/f"{slot-1:04}.json")) if slot > 1 else raw_digest(self.grant_bytes)
            call = {"slot": slot, "request_hash": request_hash, "task": self.task, "phase": self.phase,
                    "issues": list(self.issues), "repair": self.correction, "issued_at": at.isoformat()}
            save(self.journal/f"{slot:04}.json", {"previous_hash": previous, "call": call})
            save(self.path, self._load())
            return slot

def locate_repeated_quotes(parent, quotes):
    units = []
    for quote in dict.fromkeys(quotes):
        for match in re.finditer(re.escape(quote), parent["text"]):
            start, end = match.span()
            units.append({"unit_id": f'{parent["unit_id"]}.span.{start}.{end}', "text": quote,
                          "parent_unit_id": parent["unit_id"], "parent_text_hash": digest(parent["text"]),
                          "start": start, "end": end,
                          "qualification": "Occurrence locator only; read the complete retained parent for all conditions and exceptions."})
    return units

def verify_packet(packet):
    units = {u["unit_id"]: u for u in packet["units"]}
    if len(units) != len(packet["units"]):
        fail("E_REFERENCE", "Duplicate source unit")
    for u in packet["units"]:
        if "parent_unit_id" not in u:
            continue
        parent = units.get(u["parent_unit_id"])
        if (parent is None or digest(parent["text"]) != u["parent_text_hash"]
                or type(u["start"]) is not int or type(u["end"]) is not int
                or not 0 <= u["start"] < u["end"] <= len(parent["text"])
                or parent["text"][u["start"]:u["end"]] != u["text"]):
            fail("E_INTEGRITY", "Detached quotation locator")
    return packet

class Finding(Strict):
    question_id: str
    status: Literal["SUPPORTED_UNDER_STATED_SCOPE", "PARTIALLY_SUPPORTED", "UNRESOLVED", "SOURCE_MISMATCH"]
    answer: str = Field(min_length=1, max_length=2400)
    evidence: list[Quote] = Field(max_length=5)
    qualifications: list[str] = Field(min_length=1, max_length=6)
    needed_evidence: list[str] = Field(max_length=6)
    original_question_answered: bool

class ReviewResponse(Strict):
    binding_hash: str
    findings: list[Finding] = Field(min_length=1, max_length=4)
    legal_correctness: Literal["NOT_ESTABLISHED"]

class QuestionUpdate(Strict):
    reading_id: str
    question_id: str
    status: Literal["SOURCE_NOW_AVAILABLE", "ANSWERED_UNDER_STATED_PREMISES", "REMAINS_OPEN"]
    evidence: list[Quote] = Field(max_length=2)
    explanation: str = Field(min_length=1, max_length=700)

class ReadingUpdate(Strict):
    reading_id: str
    reading_hash: str
    disposition: Literal["RETAIN_CONDITIONAL", "RETAIN_UNFORMALIZED", "CHALLENGED"]
    explanation: str = Field(min_length=1, max_length=1800)
    evidence: list[Quote] = Field(min_length=1, max_length=4)
    added_assumptions: list[str] = Field(max_length=8)
    remaining_questions: list[str] = Field(max_length=10)
    required_program_repairs: list[str] = Field(max_length=6)

class PropagationResponse(Strict):
    binding_hash: str
    reading_updates: list[ReadingUpdate] = Field(min_length=1, max_length=2)
    question_updates: list[QuestionUpdate] = Field(max_length=64)
    obligation_updates: list[Finding] = Field(max_length=10)
    legal_correctness: Literal["NOT_ESTABLISHED"]

class QuestionGroup(Strict):
    reading_id: str
    question_ids: list[str] = Field(min_length=1, max_length=64)
    status: Literal["SOURCE_NOW_AVAILABLE", "ANSWERED_UNDER_STATED_PREMISES", "REMAINS_OPEN"]
    evidence: list[Quote] = Field(max_length=2)
    explanation: str = Field(min_length=1, max_length=350)

class GroupedPropagationResponse(Strict):
    binding_hash: str
    reading_updates: list[ReadingUpdate] = Field(min_length=1, max_length=2)
    question_groups: list[QuestionGroup] = Field(min_length=1, max_length=24)
    obligation_updates: list[Finding] = Field(max_length=10)
    legal_correctness: Literal["NOT_ESTABLISHED"]


def validate_findings(rows, expected, packet):
    ids = [r["question_id"] for r in rows]
    if len(ids) != len(set(ids)) or set(ids) != set(expected):
        fail("E_REFERENCE", "Missing, repeated or foreign finding")
    verify_packet(packet)
    for row in rows:
        check_quotes(row["evidence"], packet)
        if row["status"] != "UNRESOLVED" and not row["evidence"]:
            fail("E_REFERENCE", "Substantive answer lacks source quote")
        if row["status"] in ("UNRESOLVED", "SOURCE_MISMATCH") and not row["needed_evidence"]:
            fail("E_REFERENCE", "Open issue lacks needed evidence")
        if row["status"] != "SUPPORTED_UNDER_STATED_SCOPE" and row["original_question_answered"]:
            fail("E_REFERENCE", "Qualified finding claimed full closure")

def validate_response(value, request):
    if request["kind"] == "formal_repair":
        return repair.validate_assessment(value, request["binding_hash"], request["source_packet"],
                                          request["readings"], request["selected"])
    grouped = request["kind"] == "propagation_grouped"
    if grouped:
        value = parse(GroupedPropagationResponse, value)
        expanded = [{**{k:v for k,v in group.items() if k != "question_ids"}, "question_id": q}
                    for group in value["question_groups"] for q in group["question_ids"]]
        value = {**{k:v for k,v in value.items() if k != "question_groups"}, "question_updates": expanded}
    typ = PropagationResponse if request["kind"].startswith("propagation") else ReviewResponse
    value = parse(typ, value)
    if value["binding_hash"] != request["binding_hash"]:
        fail("E_REFERENCE", "Wrong review binding")
    packet = request["source_packet"]
    if typ is ReviewResponse:
        validate_findings(value["findings"], [q["id"] for q in request["questions"]], packet)
        return value
    selected = request["selected"]
    actual = [r["reading_id"] for r in value["reading_updates"]]
    if len(actual) != len(set(actual)) or set(actual) != set(selected):
        fail("E_REFERENCE", "Every selected reading needs a disposition")
    for row in value["reading_updates"]:
        old = request["prior_assessments"][row["reading_id"]]
        if row["reading_hash"] != request["reading_hashes"][row["reading_id"]]:
            fail("E_REFERENCE", "Wrong reading identity")
        check_quotes(row["evidence"], packet)
        if row["disposition"] == "RETAIN_CONDITIONAL" and old["formalization"] is None:
            fail("E_REFERENCE", "Cannot retain a nonexistent formalization")
        if row["disposition"] == "RETAIN_UNFORMALIZED" and old["formalization"] is not None:
            fail("E_REFERENCE", "Cannot silently remove a program; challenge with a repair")
        if row["required_program_repairs"] and row["disposition"] != "CHALLENGED":
            fail("E_REFERENCE", "Required program repair vetoes unchanged retention")
    expected = {(r["reading_id"], r["question_id"]) for r in request["question_inventory"]}
    actual = [(r["reading_id"], r["question_id"]) for r in value["question_updates"]]
    if len(actual) != len(set(actual)) or set(actual) != expected:
        fail("E_REFERENCE", "Each original and prior-assessment question needs a disposition")
    for row in value["question_updates"]:
        check_quotes(row["evidence"], packet)
        if row["status"] != "REMAINS_OPEN" and not row["evidence"]:
            fail("E_REFERENCE", "Question resolution lacks source evidence")
    validate_findings(value["obligation_updates"], [r["id"] for r in request["obligations"]], packet)
    return value
