"""Source-bound authority applicability and treatment, separate from legal truth.

Graph checks determine which proposed priority arguments are structurally usable
under their declared premises. They never turn a citation or model label into a
binding holding, or prune an interpretation without a separate disposition.
"""
from datetime import date
from typing import Literal
from pydantic import Field
from ...canonical import digest
from ...errors import LegalMathError
from ..contracts import Strict, Id, Text, parse
from ..search.models import Quote
from .semantics import check_quotes


class AuthorityReason(Strict):
    authority_id: Id
    source_kind: Literal['CIRCULAR','FAQ','CODE','CASE','LEGISLATION']
    proposition: Text
    text_role: Literal['OPERATIVE_PROVISION','OFFICIAL_ANSWER','HOLDING','SUBMISSION','COMMENTARY','UNDETERMINED']
    role_basis: list[Quote] = Field(min_length=1,max_length=12)
    jurisdiction: Text
    actor_class: Text
    relevant_factors: list[Text] = Field(max_length=20)
    applicability: Literal['PROPOSED_APPLICABLE','INAPPLICABLE','UNRESOLVED']
    applicability_basis: list[Quote] = Field(max_length=12)
    effective_from: str | None
    effective_until: str | None
    temporal_basis: list[Quote] = Field(max_length=12)
    treatment: Literal['NO_TREATMENT_ESTABLISHED','AFFIRMED','DISTINGUISHED','OVERRULED','SUPERSEDED','CONFLICTING']
    treatment_basis: list[Quote] = Field(max_length=12)
    assumptions: list[Text] = Field(max_length=20)


class PriorityReason(Strict):
    priority_id: Id
    preferred: Id
    displaced: Id
    rationale: Text
    evidence: list[Quote] = Field(min_length=1,max_length=12)
    premise_status: Literal['PROPOSED','SOURCE_EXPRESS','DISPUTED']


class AuthorityArguments(Strict):
    authorities: list[AuthorityReason] = Field(min_length=1,max_length=32)
    priorities: list[PriorityReason] = Field(max_length=64)
    unresolved: list[Text] = Field(max_length=32)


def evaluate(value,packet,*,at,jurisdiction,actor_class):
    value=parse(AuthorityArguments,value)
    def checked_date(text):
        try:
            parsed=date.fromisoformat(text)
            if parsed.isoformat()!=text:raise ValueError('Noncanonical date')
            return parsed
        except (ValueError,TypeError):raise LegalMathError('E_TIME',details='Authority date must be an exact Gregorian YYYY-MM-DD') from None
    when=checked_date(at[:10])
    authorities={a['authority_id']:a for a in value['authorities']}
    if len(authorities)!=len(value['authorities']) or len({p['priority_id'] for p in value['priorities']})!=len(value['priorities']):
        raise LegalMathError('E_DUPLICATE_ID')
    findings=[];eligible=[]
    for aid,a in authorities.items():
        for k in ('role_basis','applicability_basis','temporal_basis','treatment_basis'):check_quotes(a[k],packet)
        reasons=[]
        if a['source_kind']=='CASE' and a['text_role']!='HOLDING':reasons.append('HOLDING_NOT_ESTABLISHED')
        if a['text_role'] in ('SUBMISSION','COMMENTARY','UNDETERMINED'):reasons.append('NON_OPERATIVE_TEXT')
        if a['jurisdiction']!=jurisdiction or a['actor_class']!=actor_class:reasons.append('CONTEXT_MISMATCH')
        if a['applicability']!='PROPOSED_APPLICABLE' or not a['applicability_basis']:reasons.append('APPLICABILITY_UNRESOLVED')
        start=checked_date(a['effective_from']) if a['effective_from'] else None
        end=checked_date(a['effective_until']) if a['effective_until'] else None
        if end and (not start or end<=start):raise LegalMathError('E_TIME')
        if start is None or not a['temporal_basis']:reasons.append('EFFECTIVENESS_UNRESOLVED')
        elif when<start or (end is not None and when>=end):reasons.append('OUTSIDE_DECLARED_INTERVAL')
        if a['treatment']!='NO_TREATMENT_ESTABLISHED' and not a['treatment_basis']:
            raise LegalMathError('E_REFERENCE',details='Treatment assertion has no source')
        if a['treatment'] in ('DISTINGUISHED','OVERRULED','SUPERSEDED','CONFLICTING'):reasons.append('ADVERSE_OR_CONFLICTING_TREATMENT')
        if reasons:findings.append({'authority_id':aid,'reasons':reasons})
        else:eligible.append(aid)
    edges=[]
    for p in value['priorities']:
        check_quotes(p['evidence'],packet)
        if p['preferred'] not in authorities or p['displaced'] not in authorities or p['preferred']==p['displaced']:
            raise LegalMathError('E_REFERENCE')
        if p['premise_status']!='SOURCE_EXPRESS' or not {p['preferred'],p['displaced']}<=set(eligible):
            findings.append({'priority_id':p['priority_id'],'reasons':['PRIORITY_PREMISE_NOT_ESTABLISHED']})
        edges.append((p['preferred'],p['displaced']))
    # Transitive reachability exposes cycles even when each individual edge has
    # an authentic quote. A cycle cannot be broken by insertion order or a score.
    reach={a:set() for a in authorities}
    for a,b in edges:reach[a].add(b)
    for _ in authorities:
        for a in authorities:
            reach[a]|={v for b in tuple(reach[a]) for v in reach[b]}
    cycle=sorted(a for a in authorities if a in reach[a])
    if cycle:findings.append({'reasons':['PRIORITY_CYCLE'],'authority_ids':cycle})
    return {'profile':'authority-arguments.v1','input_hash':digest(value),'source_packet_hash':digest(packet),
            'considered':list(authorities),'conditionally_eligible':sorted(eligible),'findings':findings,
            'priorities':value['priorities'],'unresolved':value['unresolved'],
            'status':'AUTHORITY_QUESTIONS_RETAINED' if findings or value['unresolved'] else 'DECLARED_PREMISES_CHECKED',
            'binding_legal_priority_established':False,'pruned_interpretations':[],'release_eligible':False}
