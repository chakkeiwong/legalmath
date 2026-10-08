"""Source-bound conditional standards; no rule establishes its own legal sufficiency.

The finite evaluator computes a sufficient implication under supplied premises.
Failure of an antecedent never proves the negation of the consequence. There is
no rule chaining, legal priority, closed-world negation or automatic admission of
quotations as interpretive or factual evidence.
"""
from typing import Literal
from pydantic import Field, model_validator
from .records import Record, Text, Hash, Scope, Interval, SourceSpan, Modality, Support
from ...canonical import digest

PROFILE = "legalmath.conditional-standards.v1"
Kind = Literal["observed-fact", "authority-premise", "inference-premise", "source-assertion"]


class Requirement(Record):
    id: Text
    statement: Text
    kind: Kind


class Standard(Record):
    id: Text
    question: Text
    consequence: Text
    modality: Modality
    sources: tuple[SourceSpan, ...] = Field(min_length=1, max_length=16)
    requirements: tuple[Requirement, ...] = Field(min_length=2, max_length=32)
    warrant: Text
    limits: tuple[Text, ...] = Field(min_length=1)
    status: Literal["proposed-conditional-rule"] = "proposed-conditional-rule"

    @model_validator(mode="after")
    def boundary(self):
        ids = [p.id for p in self.requirements]
        if len(ids) != len(set(ids)):
            raise ValueError("Duplicate requirement")
        kinds = {p.kind for p in self.requirements}
        if not {"authority-premise", "inference-premise"} <= kinds:
            raise ValueError("Explicit applicability and interpretation premises required")
        return self


class Assessment(Record):
    scope: Scope
    provider: Text | None
    jurisdiction: Text | None
    known_by: str | None

    @model_validator(mode="after")
    def dates(self):
        Interval(start=self.known_by, end=self.known_by)
        return self


class PremiseEvidence(Record):
    id: Text
    requirement_id: Text
    kind: Kind
    positive: bool
    scope: Scope
    provider: Text
    jurisdiction: Text
    known_on: str | None
    evidence_hash: Hash
    basis: Text
    dependencies: tuple[Hash, ...]
    admission: Literal["supplied", "synthetic"]

    @model_validator(mode="after")
    def dates(self):
        Interval(start=self.known_on, end=self.known_on)
        return self


def _scope(evidence, assessment):
    reasons = []
    for actual, expected in (
        (evidence.scope.actor, assessment.scope.actor),
        (evidence.provider, assessment.provider),
        (evidence.scope.product, assessment.scope.product),
        (evidence.scope.component, assessment.scope.component),
        (evidence.scope.activity, assessment.scope.activity),
        (evidence.jurisdiction, assessment.jurisdiction),
    ):
        if actual is None or expected is None:
            reasons.append("unknown-identity")
        elif actual != expected:
            return "out-of-scope", ["different-identity"]
    if evidence.known_on is None or assessment.known_by is None:
        reasons.append("unknown-knowledge-date")
    elif evidence.known_on > assessment.known_by:
        return "out-of-scope", ["learned-after-cutoff"]
    actual, expected = evidence.scope.interval, assessment.scope.interval
    if None in (actual.start, actual.end, expected.start, expected.end):
        reasons.append("unknown-interval")
    elif actual.start > expected.start or actual.end < expected.end:
        reasons.append("incomplete-period-coverage")
    return ("unknown", sorted(set(reasons))) if reasons else ("declared", [])


def _validate_sources(standards, packet, catalogue):
    units = packet.get("units", [])
    texts = {u["unit_id"]: u["text"] for u in units}
    if not texts or len(texts) != len(units):
        raise ValueError("Empty or duplicate source units")
    packet_hash = digest(packet)
    for rule in standards:
        for source in rule.sources:
            if source.unit_id not in texts or source.unit_id not in catalogue:
                raise ValueError("Missing bound source edition")
            metadata = catalogue[source.unit_id]
            if (source.edition != metadata["edition"] or source.role != metadata["role"]):
                raise ValueError("Source edition or role differs")
            source.verify(texts[source.unit_id], packet_hash, digest(rule.question))


def evaluate(standards, packet, catalogue, assessment, evidence):
    """Return replayable conditional computations, not legal truth labels."""
    standards, evidence = tuple(standards), tuple(evidence)
    if not 1 <= len(standards) <= 64 or len(evidence) > 1024:
        raise ValueError("Finite standards profile exceeded")
    if len({r.id for r in standards}) != len(standards):
        raise ValueError("Duplicate standard")
    if len({e.id for e in evidence}) != len(evidence):
        raise ValueError("Duplicate premise evidence")
    # A shared identifier must have exactly one meaning across the inventory.
    definitions = {}
    for rule in standards:
        for requirement in rule.requirements:
            if requirement.id in definitions and definitions[requirement.id] != requirement:
                raise ValueError("Shared premise has incompatible definitions")
            definitions[requirement.id] = requirement
    _validate_sources(standards, packet, catalogue)
    results = []
    for rule in standards:
        premises, reasons = [], []
        for requirement in rule.requirements:
            positive, negative, excluded = [], [], []
            for item in evidence:
                if item.requirement_id != requirement.id:
                    continue
                state, detail = _scope(item, assessment)
                if item.kind != requirement.kind:
                    state, detail = "unknown", ["evidence-kind-mismatch"]
                if state != "declared":
                    excluded.append({"id": item.id, "scope": state, "reasons": detail})
                else:
                    (positive if item.positive else negative).append(item.id)
            support = Support(positive=tuple(sorted(positive)), negative=tuple(sorted(negative)))
            premises.append({"requirement": requirement.model_dump(mode="json"),
                "support": support.model_dump(mode="json"), "state": support.state,
                "excluded": sorted(excluded, key=lambda r: r["id"])})
            if support.state == "unknown":
                reasons.append({"premise": requirement.id, "reason": "missing-premise"})
            elif support.state == "false":
                reasons.append({"premise": requirement.id, "reason": "negative-antecedent"})
            elif support.state == "conflict":
                reasons.append({"premise": requirement.id, "reason": "conflicting-premise"})
        fired = all(p["state"] == "true" for p in premises)
        results.append({"rule_id": rule.id, "rule_hash": rule.identity(),
            "status": "CONDITIONALLY_DERIVED" if fired else "NOT_DERIVED",
            "question": rule.question, "consequence": rule.consequence,
            "modality": rule.modality, "premises": premises, "reasons": reasons,
            "limits": list(rule.limits), "opposite_consequence": "NOT_ESTABLISHED",
            "legal_correctness": "NOT_ESTABLISHED"})
    identity = {"profile": PROFILE, "packet_hash": digest(packet), "catalogue_hash": digest(catalogue),
        "standards": [r.identity() for r in standards], "assessment": assessment.identity(),
        "evidence": [e.identity() for e in evidence]}
    return {"profile": PROFILE, "identity": identity, "results": results,
        "unmatched_evidence": sorted(e.id for e in evidence if e.requirement_id not in definitions),
        "evidence_admission": "Supplied scoped premises; their truth and source interpretation are not established",
        "english_fidelity": "NOT_ESTABLISHED", "legal_correctness": "NOT_ESTABLISHED",
        "release_eligible": False}


def verify(receipt, standards, packet, catalogue, assessment, evidence):
    expected = evaluate(standards, packet, catalogue, assessment, evidence)
    if receipt != expected:
        raise ValueError("Conditional standards receipt differs from recomputation")
    return {"status": "PASS", "profile": PROFILE, "receipt_hash": digest(receipt),
            "scope": "Deterministic recomputation under supplied premises"}
