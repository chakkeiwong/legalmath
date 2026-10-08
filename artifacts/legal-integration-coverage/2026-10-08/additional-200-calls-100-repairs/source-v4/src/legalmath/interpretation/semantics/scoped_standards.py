"""Explicit recorded-event adapter and branch attachments for semantic v3.

Evidence bytes establish identity only. Neither a recorded predicate nor a
supplied premise establishes the truth of a legal or factual classification.
"""
from typing import Literal
from pydantic import Field, model_validator
from ...canonical import canonical, digest, loads, raw_digest
from ...errors import LegalMathError
from .records import Record, Text, Hash, Interval, Scope, Premise
from .standards import Standard, Requirement, Assessment, PremiseEvidence, evaluate, _scope

PROFILE = "legalmath.scoped-standards.v1"
EventKind = Literal["appointment", "supervision", "discrepancy", "ownership-assertion",
    "incident", "remediation", "replacement", "termination", "migration", "correction",
    "reconciliation", "ledger-entry", "terms-change", "terms-acceptance",
    "customer-access", "trust-relationship"]
KINDS = EventKind.__args__


def recorded_requirement(kind):
    if kind not in KINDS:
        raise ValueError("Unknown recorded event kind")
    return Requirement(id="recorded." + kind, kind="observed-fact",
        statement="A " + kind + " event is recorded for the exact assessed identities, "
        "with declared validity covering the assessment interval and known by its cutoff; "
        "this does not establish legal sufficiency or the underlying event's truth.")


class Document(Record):
    text: Text
    sha256: Hash

    @model_validator(mode="after")
    def bytes_match(self):
        if raw_digest(self.text.encode("utf-8")) != self.sha256:
            raise ValueError("Evidence document bytes differ from identity")
        return self


class Event(Record):
    id: Text
    kind: EventKind
    positive: bool
    scope: Scope  # Declared validity, not inferred from occurrence time.
    provider: Text
    jurisdiction: Text
    event: Interval
    known_on: str | None
    evidence_hash: Hash
    completeness: Premise | None = None
    admission: Literal["supplied", "synthetic"]

    @model_validator(mode="after")
    def date(self):
        Interval(start=self.known_on, end=self.known_on)
        return self


class Attachment(Record):
    id: Text
    reading_hash: Hash
    question_hash: Hash
    rule_ids: tuple[Text, ...] = Field(min_length=1, max_length=64)
    warrant: Text
    status: Literal["proposed"] = "proposed"


class Inputs(Record):
    profile: Literal["legalmath.scoped-standards.v1"] = PROFILE
    packet_hash: Hash
    catalogue: dict[str, dict]
    standards: tuple[Standard, ...] = Field(min_length=1, max_length=64)
    assessment: Assessment
    documents: tuple[Document, ...] = Field(max_length=1024)
    observations: tuple[Event, ...] = Field(max_length=1024)
    premises: tuple[PremiseEvidence, ...] = Field(max_length=1024)
    attachments: tuple[Attachment, ...] = Field(max_length=64)

    @model_validator(mode="after")
    def identities(self):
        if len(self.observations) + len(self.premises) > 1024:
            raise ValueError("Total evidence exceeds 1024")
        for values, key in ((self.documents, "sha256"), (self.observations, "id"),
                (self.premises, "id"), (self.attachments, "id"), (self.standards, "id")):
            if len({getattr(v, key) for v in values}) != len(values):
                raise ValueError("Duplicate input identity")
        docs = {d.sha256 for d in self.documents}
        if any(e.evidence_hash not in docs for e in (*self.observations, *self.premises)):
            raise ValueError("Evidence document missing")
        reserved = {recorded_requirement(k).id: recorded_requirement(k) for k in KINDS}
        for rule in self.standards:
            for requirement in rule.requirements:
                if requirement.id.startswith("recorded.") and reserved.get(requirement.id) != requirement:
                    raise ValueError("Recorded predicates cannot be renamed as evaluative requirements")
        if any(p.id.startswith("observation.") or p.requirement_id.startswith("recorded.") for p in self.premises):
            raise ValueError("Recorded predicates require the observation adapter")
        known = {r.id for r in self.standards}
        for a in self.attachments:
            if len(set(a.rule_ids)) != len(a.rule_ids) or not set(a.rule_ids) <= known:
                raise ValueError("Invalid attachment rules")
        return self


def parse(value):
    try:
        return Inputs.model_validate_json(canonical(value))
    except (ValueError, TypeError) as exc:
        raise LegalMathError("E_SCHEMA", details=str(exc)) from exc


def adapt(inputs):
    """Retain every event and exclusion; emit only narrow recorded predicates."""
    evidence = list(inputs.premises)
    records = []
    definitions = {p.id for r in inputs.standards for p in r.requirements}
    for event in inputs.observations:
        requirement = recorded_requirement(event.kind)
        premise = PremiseEvidence(id="observation." + event.id, requirement_id=requirement.id,
            kind="observed-fact", positive=event.positive, scope=event.scope,
            provider=event.provider, jurisdiction=event.jurisdiction, known_on=event.known_on,
            evidence_hash=event.evidence_hash, basis=requirement.statement,
            dependencies=(event.identity(),), admission=event.admission)
        state, reasons = _scope(premise, inputs.assessment)
        reasons = list(reasons)
        start, end = event.event.start, event.event.end
        if start is None or end is None:
            reasons.append("unknown-event-interval")
        else:
            if inputs.assessment.known_by is not None and end > inputs.assessment.known_by:
                reasons.append("event-after-cutoff")
            if event.known_on is not None and end > event.known_on:
                reasons.append("event-after-knowledge-date")
            if inputs.assessment.scope.interval.end is not None and end > inputs.assessment.scope.interval.end:
                reasons.append("event-after-assessment")
            valid = event.scope.interval
            if (valid.start is not None and start < valid.start) or (valid.end is not None and end > valid.end):
                reasons.append("event-outside-validity")
        if not event.positive and (event.completeness is None or event.completeness.status != "declared"):
            reasons.append("missing-completeness-premise")
        if requirement.id not in definitions:
            reasons.append("unmatched-recorded-predicate")
        admitted = state == "declared" and not reasons
        if admitted:
            evidence.append(premise)
        records.append({"observation": event.model_dump(mode="json"), "observation_hash": event.identity(),
            "requirement": requirement.model_dump(mode="json"), "admitted": admitted,
            "reasons": sorted(set(reasons)), "derived_premise": premise.model_dump(mode="json") if admitted else None})
    return evidence, records


def compute(value, packet, candidates, questions, rows):
    inputs = parse(value)
    if inputs.packet_hash != digest(packet):
        raise LegalMathError("E_REFERENCE", details="Standards source packet differs")
    evidence, events = adapt(inputs)
    try:
        evaluation = evaluate(inputs.standards, packet, inputs.catalogue, inputs.assessment, evidence)
    except ValueError as exc:
        raise LegalMathError("E_REFERENCE", details=str(exc)) from exc
    attachments = {}
    for a in inputs.attachments:
        matched = [cid for cid in candidates if digest(candidates[cid]) == a.reading_hash
            and digest(questions[cid]) == a.question_hash]
        if not matched:
            raise LegalMathError("E_REFERENCE", details="Attachment reading/question missing")
        for cid in matched:
            attachments.setdefault(cid, []).append(a)
    results = {r["rule_id"]: r for r in evaluation["results"]}
    branch_rows = []
    used = set()
    for row in rows:
        cid = row["candidate_id"]
        selected = attachments.get(cid, [])
        rule_ids = sorted({rule for a in selected for rule in a.rule_ids})
        used.update(rule_ids)
        branch_rows.append({"candidate_id": cid, "branch_id": digest(row["branch"]),
            "reading_hash": digest(candidates[cid]), "question_hash": digest(questions[cid]),
            "attachments": [a.model_dump(mode="json") for a in selected],
            "results": [results[r] for r in rule_ids],
            "unresolved": ["source-to-rule-and-attachment-meaning-not-established"] +
                ([] if selected else ["no-standards-attachment"]),
            "legacy_formula_relationship": "NOT_ESTABLISHED", "standards_lowering": "NOT_IMPLEMENTED"})
    return loads(canonical({"profile": PROFILE, "inputs_hash": inputs.identity(),
        "observation_admission": events, "premise_evidence": [p.model_dump(mode="json") for p in evidence],
        "evaluation": evaluation, "branches": branch_rows,
        "unattached_rules": sorted(set(results) - used),
        "legal_correctness": "NOT_ESTABLISHED", "release_eligible": False}))
