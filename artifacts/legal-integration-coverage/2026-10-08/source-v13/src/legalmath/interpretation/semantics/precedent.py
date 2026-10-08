"""Source-bound precedent mechanics; a classifier cannot establish ratio or force."""
from dataclasses import dataclass
import re
from typing import Literal
from .records import SourceSpan, Interval
from ...canonical import digest

@dataclass(frozen=True)
class JudgmentManifest:
    judgment_id: str
    official_origin: str
    source_hash: str
    court: str | None
    jurisdiction: str | None
    decision_date: str | None
    procedural_context: str | None
    opinion_boundaries: tuple[str, ...]
    fields_unverified: tuple[str, ...]
    acquired: bool = False

@dataclass(frozen=True)
class Passage:
    passage_id: str
    span: SourceSpan
    speaker: str
    role: str
    text: str

@dataclass(frozen=True)
class Proposition:
    proposition_id: str
    statement: str
    role: Literal["issue","holding","factual-finding","reasoning","dictum","submission","unknown"]
    passage_ids: tuple[str, ...]
    warrant: str
    role_status: Literal["proposed","source-backed","unresolved"] = "unresolved"

@dataclass(frozen=True)
class Factor:
    factor_id: str
    name: str
    value: str
    source_proposition_ids: tuple[str, ...]
    relevance_warrant: str
    status: Literal["proposed","unresolved"] = "unresolved"

@dataclass(frozen=True)
class Authority:
    proposition_id: str
    jurisdiction: str | None
    court_level: str | None
    binding: bool | None
    persuasive: bool | None
    temporal_scope: Interval
    premise_ids: tuple[str, ...]
    status: Literal["supported","conditional","unknown"] = "unknown"

@dataclass(frozen=True)
class Treatment:
    judgment_id: str
    later_judgment_id: str | None
    treatment: Literal["followed","distinguished","criticised","overruled","unknown"]
    source_ids: tuple[str, ...]
    date: str | None
    status: Literal["source-backed","unresolved"] = "unresolved"

@dataclass(frozen=True)
class Move:
    kind: Literal["analogy","distinction","counterexample"]
    source_factor_ids: tuple[str, ...]
    target_proposition_id: str
    explanation: str
    status: Literal["proposed","unresolved"] = "unresolved"

@dataclass(frozen=True)
class Citation:
    raw: str
    parsed: bool
    report: str | None
    year: str | None
    court: str | None
    number: str | None
    reason: str | None

def parse_citation(raw):
    m = re.fullmatch(r"\[(\d{4})\]\s+(UKSC|UKHL)\s+(\d+)", raw.strip())
    if not m:
        return Citation(raw,False,None,None,None,None,"unsupported citation syntax/coverage")
    return Citation(raw,True,None,m.group(1),m.group(2),m.group(3),None)

def validate_case(packet, question_hash, manifest, passages, propositions, factors, moves):
    """Check source/role/reference integrity; semantic role nomination stays proposed."""
    if manifest.source_hash != digest(packet):
        raise ValueError("Judgment source identity mismatch")
    units={u["unit_id"]:u["text"] for u in packet["units"]}
    by_id={p.passage_id:p for p in passages}
    props={p.proposition_id:p for p in propositions}
    facts={f.factor_id:f for f in factors}
    if len(by_id)!=len(passages) or len(props)!=len(propositions) or len(facts)!=len(factors):
        raise ValueError("Duplicate case identity")
    for p in passages:
        p.span.verify(units[p.span.unit_id],manifest.source_hash,question_hash)
        if p.role!=p.span.role or not p.speaker or p.text!=p.span.quote:
            raise ValueError("Misattributed passage role/text")
    for p in propositions:
        if p.role not in ("issue","holding","factual-finding","reasoning","dictum","submission","unknown"):
            raise ValueError("Unknown proposed proposition role")
        if not p.warrant or not p.passage_ids or not set(p.passage_ids)<=set(by_id):
            raise ValueError("Missing source warrant")
        if p.role_status=="source-backed" and p.role in ("holding","factual-finding"):
            roles={by_id[x].role for x in p.passage_ids}
            if roles & {"submission","allegation","dissent","unknown"}:
                raise ValueError("A submission/dissent cannot establish a court holding/finding")
    for f in factors:
        if not f.relevance_warrant or not f.source_proposition_ids or not set(f.source_proposition_ids)<=set(props):
            raise ValueError("Factor needs a proposition and relevance warrant")
    for move in moves:
        if move.target_proposition_id not in props or not set(move.source_factor_ids)<=set(facts) or not move.explanation:
            raise ValueError("Transfer move lacks factors/proposition")
    return {"status":"SOURCE_REFERENCES_CHECKED","ratio":"NOT_ESTABLISHED","legal_force":"NOT_ESTABLISHED"}

def assess_authority(manifest, proposition, authority, treatments, as_of):
    Interval(start=as_of,end=as_of)
    reasons=[]
    if not manifest.acquired: reasons.append("missing-official-judgment")
    if not manifest.court or not manifest.jurisdiction: reasons.append("unknown-jurisdiction-hierarchy")
    if authority.proposition_id != proposition.proposition_id: raise ValueError("Wrong authority target")
    if not authority.premise_ids or authority.status!="supported": reasons.append("unresolved-authority-premises")
    if manifest.decision_date is None or manifest.decision_date>as_of: reasons.append("unknown-or-later-decision")
    if not treatments or any(t.treatment=="unknown" or t.status!="source-backed" for t in treatments):
        reasons.append("subsequent-treatment-unresolved")
    if any(t.treatment=="overruled" and t.date is not None and t.date<=as_of for t in treatments):
        reasons.append("overruled-by-assessment-date")
    return {"status":"UNRESOLVED" if reasons else "CONDITIONAL_ON_DECLARED_AUTHORITY_PREMISES",
            "reasons":sorted(set(reasons)),"binding_established":False}

def comparison(manifest, propositions, factors, moves):
    if not manifest.acquired:
        return {"status":"REAL_CASE_PENDING","missing":"official judgment acquisition and verified authority fields",
                "manifest":manifest.__dict__}
    return {"status":"MECHANICS_ONLY","propositions":len(propositions),"factors":len(factors),"moves":len(moves),
            "legal_force":"UNKNOWN_UNTIL_JURISDICTION_AND_TREATMENT_PREMISES"}
