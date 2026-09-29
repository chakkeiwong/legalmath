"""Source-first independent annotations; model proposals cannot become reference labels."""
from ...canonical import digest
from ...errors import LegalMathError
from ..contracts import Strict,Text,Id,Hash,parse
from pydantic import Field
from typing import Literal


class Annotation(Strict):
    packet_hash: Hash
    source_unit_id: Id
    duty: Text
    alternatives: list[Text] = Field(min_length=1,max_length=20)
    scope: Text
    exceptions: list[Text] = Field(max_length=20)
    effective_time: Text
    missing_authorities: list[Text] = Field(max_length=20)
    uncertainty: Text


class Adjudication(Strict):
    accepted_readings: list[Text] = Field(max_length=30)
    unresolved: bool
    reason: Text


def assign(service,caller,key,run_id,reviewers):
    def operation(con):
        service._owner(con,caller,run_id)
        run=service._run(con,run_id,True)
        if service._list(con,run_id,'annotation-assignment'):
            raise LegalMathError('E_JOB_STATE',details='An annotation assignment is immutable')
        if run['candidate_ids'] or service._list(con,run_id,'search-request'):
            raise LegalMathError('E_AUTHORITY',details='Blind annotation assignment must precede model generation')
        if len(reviewers)<2 or len(reviewers)!=len(set(reviewers)) or caller in reviewers:raise LegalMathError('E_AUTHORITY')
        for reviewer in reviewers:service.lc.require(con,reviewer,'meaning')
        value={'run_id':run_id,'packet_hash':run['source_packet_hash'],'reviewers':reviewers,
               'author':caller,'assigned_before_candidates':True,'independence':'REQUIRES_HUMAN_ATTESTATION'}
        service._save(con,'annotation-assignment',value,'assignment');return value
    return service.db.mutate(caller,key,{'op':'annotation.assign','run':run_id,'reviewers':reviewers},operation)


def reviewer_packet(service,reviewer,run_id):
    with service.db.connect() as con:
        service.lc.require(con,reviewer,'meaning')
        assignment=service._get(con,run_id,'annotation-assignment','assignment')
        if reviewer not in assignment['reviewers']:raise LegalMathError('E_AUTHORITY')
        packet=service.db.get(con,assignment['packet_hash'])
    return {'packet_hash':assignment['packet_hash'],'source_packet':packet,
            'instructions':'Independently identify duties, scope, exceptions, alternatives and unresolved authorities. No candidate answers are supplied.'}


def submit(service,reviewer,key,run_id,annotations,attests_independent):
    values=[parse(Annotation,a) for a in annotations]
    def operation(con):
        service.lc.require(con,reviewer,'meaning')
        assignment=service._get(con,run_id,'annotation-assignment','assignment')
        if reviewer not in assignment['reviewers'] or attests_independent is not True:raise LegalMathError('E_AUTHORITY')
        if service._list(con,run_id,'reference-freeze') or any(r['reviewer']==reviewer for r in service._list(con,run_id,'annotation')):
            raise LegalMathError('E_JOB_STATE')
        run=service._run(con,run_id)
        current=con.execute('SELECT packet_hash FROM interpretation_sources WHERE source_key=?',(service._packet(con,run)['source_key'],)).fetchone()[0]
        if current!=assignment['packet_hash']:raise LegalMathError('E_STALE_REVIEW')
        units={u['unit_id'] for u in service.db.get(con,current)['units']}
        if not values or any(v['packet_hash']!=current or v['source_unit_id'] not in units for v in values):raise LegalMathError('E_REFERENCE')
        value={'run_id':run_id,'reviewer':reviewer,'annotations':values,'independence_attestation':True,
               'authority':'LOCAL_REVIEWER_ATTESTATION_NOT_VERIFIED_HUMAN_IDENTITY'}
        service._save(con,'annotation',value,reviewer);return value
    return service.db.mutate(reviewer,key,{'op':'annotation.submit','run':run_id,'annotations':values,'attestation':attests_independent},operation)


def freeze(service,adjudicator,key,run_id,dispositions,rationale):
    """Every source unit retains one or more admissible readings or explicit uncertainty."""
    def operation(con):
        service.lc.require(con,adjudicator,'meaning')
        assignment=service._get(con,run_id,'annotation-assignment','assignment')
        current=con.execute('SELECT packet_hash FROM interpretation_sources WHERE source_key=?',
            (service.db.get(con,assignment['packet_hash'])['source_key'],)).fetchone()[0]
        if current!=assignment['packet_hash']:raise LegalMathError('E_STALE_REVIEW')
        if adjudicator in assignment['reviewers'] or adjudicator==assignment['author']:raise LegalMathError('E_AUTHORITY')
        annotations=service._list(con,run_id,'annotation')
        if {a['reviewer'] for a in annotations}!=set(assignment['reviewers']):raise LegalMathError('E_DEPENDENCY')
        units={u['unit_id'] for u in service.db.get(con,assignment['packet_hash'])['units']}
        if set(dispositions)!=units or not rationale.strip():raise LegalMathError('E_REFERENCE')
        for value in dispositions.values():
            parse(Adjudication,value)
            if not value['accepted_readings'] and not value['unresolved']:raise LegalMathError('E_SCHEMA')
        if service._list(con,run_id,'reference-freeze'):raise LegalMathError('E_JOB_STATE')
        value={'run_id':run_id,'packet_hash':assignment['packet_hash'],'adjudicator':adjudicator,
               'annotation_hashes':[digest(a) for a in annotations],'dispositions':dispositions,'rationale':rationale,
               'legal_accuracy_certified':False}
        service._save(con,'reference-freeze',value,'freeze');return value
    return service.db.mutate(adjudicator,key,{'op':'annotation.freeze','run':run_id,'dispositions':dispositions,'rationale':rationale},operation)
