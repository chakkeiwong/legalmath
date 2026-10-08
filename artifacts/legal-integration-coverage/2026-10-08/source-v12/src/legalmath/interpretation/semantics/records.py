"""Immutable meaning/evidence records; location checks do not prove legal support."""
from datetime import date
from typing import Annotated, Literal
from pydantic import BaseModel, ConfigDict, Field, model_validator
from ...canonical import canonical, digest, loads
from ...errors import LegalMathError

Hash = Annotated[str, Field(pattern=r"^[0-9a-f]{64}$")]
Text = Annotated[str, Field(min_length=1,max_length=20000)]
Modality = Literal["MUST","MUST_NOT","SHOULD","SHOULD_NOT","MAY","DESCRIPTIVE","UNCERTAIN"]
Role = Literal["majority","concurrence","dissent","finding","reasoning","allegation","submission","dictum","regulator","unknown"]
RECORDS = "legalmath.semantic-records.v1"

class Record(BaseModel):
    model_config = ConfigDict(extra="forbid",strict=True,frozen=True)
    def identity(self):
        return digest(self.model_dump(mode="json"))

class Interval(Record):
    start: str | None
    end: str | None
    @model_validator(mode="after")
    def ordered(self):
        for value in (self.start,self.end):
            if value is not None and date.fromisoformat(value).isoformat()!=value:
                raise ValueError("Use complete ISO dates or an unknown bound")
        if self.start is not None and self.end is not None and self.start>self.end:
            raise ValueError("Reversed interval")
        return self

class Scope(Record):
    actor: Text | None
    activity: Text | None
    product: Text | None
    component: Text | None
    interval: Interval

class SourceSpan(Record):
    source_hash: Hash
    edition: Text
    unit_id: Text
    unit_hash: Hash
    locator: Text
    start: int = Field(ge=0)
    end: int = Field(ge=1)
    quote: Text
    request_hash: Hash
    role: Role
    @model_validator(mode="after")
    def bounds(self):
        if self.end<=self.start or self.end-self.start != len(self.quote):
            raise ValueError("Unicode half-open span length mismatch")
        return self
    def verify(self,unit_text,source_hash,request_hash):
        if (self.source_hash!=source_hash or self.request_hash!=request_hash
                or self.unit_hash!=digest(unit_text) or self.end>len(unit_text)
                or unit_text[self.start:self.end]!=self.quote):
            raise LegalMathError("E_REFERENCE",details="Span differs from bound source/request")
        return self

class Support(Record):
    positive: tuple[Text,...]
    negative: tuple[Text,...]
    @property
    def state(self):
        return ("conflict" if self.positive and self.negative else
                "true" if self.positive else "false" if self.negative else "unknown")
    def __bool__(self):
        raise TypeError("Evidence support cannot be implicitly converted to truth")

class Premise(Record):
    id: Text
    statement: Text
    status: Literal["declared","unresolved","source-assertion","derived"]
    dependencies: tuple[Text,...]

class Proposition(Record):
    id: Text
    statement: Text
    scope: Scope
    modality: Modality
    sources: tuple[SourceSpan,...]
    warrant: Text
    meaning: Literal["proposed","conditional","unsupported"]
    applicability: Literal["declared","unknown","out-of-scope"]
    support: Support
    formal_consequence: Text | None
    publication_date: str | None
    effective: Interval
    event: Interval
    knowledge_date: str | None
    dependencies: tuple[Premise,...]
    @model_validator(mode="after")
    def dates(self):
        Interval(start=self.publication_date,end=self.publication_date)
        Interval(start=self.knowledge_date,end=self.knowledge_date)
        return self

class Priority(Record):
    stronger: Text
    weaker: Text
    premise: Premise

class Settings(Record):
    semantics: Literal["grounded","preferred"]
    ordering: Literal["none","last-link","weakest-link"]
    priorities: tuple[Priority,...]
    max_arguments: int = Field(ge=1,le=500)
    max_extensions: int = Field(ge=1,le=4096)
    timeout_seconds: int = Field(ge=1,le=30)
    @model_validator(mode="after")
    def explicit(self):
        if self.ordering=="none" and self.priorities:
            raise ValueError("Priorities require an explicit ordering")
        return self

class Clause(Record):
    id: Text
    actor: Text
    action: Text
    modality: Modality
    trigger: Text
    object: Text
    standard: Text
    scope: Scope
    sources: tuple[SourceSpan,...]
    relations: tuple[Premise,...]
    assumptions: tuple[Premise,...]
    warrant: Text

class Branch(Record):
    version: Literal["legalmath.semantic-records.v1"] = RECORDS
    proposal_id: Text
    source_hash: Hash
    question_hash: Hash
    legacy_reading_hash: Hash | None
    clauses: tuple[Clause,...]
    settings: Settings
    assumptions: tuple[Premise,...]
    origin: Literal["retained-proposal","sourced-development-nomination","synthetic-specification"]
    unresolved: tuple[Premise,...]

Reason = Literal["unknown-fact","unknown-applicability","unknown-interpretation",
                 "conflicting-evidence","conflicting-extensions","unsupported-lowering","unfinished"]
class Outcome(Record):
    query_id: Text
    branch_id: Hash
    extension_ids: tuple[Text,...]
    value: Literal["true","false","unknown","conflict","out-of-scope"]
    completion: Literal["complete","incomplete"]
    lowering: Literal["supported","unsupported","not-requested"]
    reasons: tuple[Reason,...]
    witnesses: tuple[Text,...]
    @model_validator(mode="after")
    def reasons_valid(self):
        if tuple(sorted(set(self.reasons)))!=self.reasons:
            raise ValueError("Reasons must be unique and canonically ordered")
        if self.completion=="incomplete" and "unfinished" not in self.reasons:
            raise ValueError("Incomplete work requires an unfinished reason")
        if self.lowering=="unsupported" and "unsupported-lowering" not in self.reasons:
            raise ValueError("Unsupported lowering requires a reason")
        return self

class LegacyEnvelope(Record):
    version: Literal["legalmath.legacy-semantic-envelope.v1"] = "legalmath.legacy-semantic-envelope.v1"
    kind: Literal["Packet","Reading","AtomicClaim","historical-units"]
    original_json: str = Field(min_length=1,max_length=2_000_000)
    original_hash: Hash
    unresolved_fields: tuple[Text,...]
    @model_validator(mode="after")
    def check_original(self):
        if digest(loads(self.original_json.encode()))!=self.original_hash:
            raise ValueError("Legacy payload identity differs")
        return self
    def restore(self):
        return loads(self.original_json.encode())

def legacy_envelope(value,kind):
    from ..contracts import Packet,parse
    from ..search.models import Reading
    from ..assurance.semantics import AtomicClaim
    if kind in ("Packet","Reading","AtomicClaim"):
        parse({"Packet":Packet,"Reading":Reading,"AtomicClaim":AtomicClaim}[kind],value)
    elif kind=="historical-units":
        if set(value)!={"units"} or not value["units"] or any(
                not isinstance(u.get("text"),str) or not u.get("unit_id") for u in value["units"]):
            raise ValueError("Invalid historical units packet")
        if len({u["unit_id"] for u in value["units"]})!=len(value["units"]):
            raise ValueError("Duplicate source units")
    else:
        raise ValueError("Unknown legacy profile")
    return LegacyEnvelope(kind=kind,original_json=canonical(value).decode(),original_hash=digest(value),
                          unresolved_fields=("meaning","applicability","actor","validity","opinion-role"))
