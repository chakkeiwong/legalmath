"""Narrow, sourced edition precedence and continuing-duty evidence."""
from copy import deepcopy
from datetime import date
from ...canonical import digest
from ...errors import LegalMathError
from ...events.replay import replay


def verify_anchor(anchor, documents):
    doc = documents.get(anchor.get('document_id'))
    if not doc or anchor.get('source_sha256') != doc['source_sha256']:
        raise LegalMathError('E_STALE_REVIEW')
    start, end = anchor.get('start'), anchor.get('end')
    if (type(start) is not int or type(end) is not int or not 0 <= start < end <= len(doc['text'])
            or doc['text'][start:end] != anchor.get('quote')):
        raise LegalMathError('E_REFERENCE')
    return anchor


def precedence(provisions, relationships, documents, *, question, at):
    """Only a sourced, scoped, dated assertion may nominate priority.

    Validating an assertion's anchor does not prove its legal reading. Cycles,
    missing intervals and unsupported assertions cannot select an authority.
    """
    when = date.fromisoformat(at); ids=set(provisions); edges=[]; unresolved=[]
    if not ids: raise LegalMathError('E_REFERENCE')
    for r in relationships:
        if r['higher'] not in ids or r['lower'] not in ids or r['higher']==r['lower']:
            raise LegalMathError('E_REFERENCE')
        if r['question'] != question: continue
        if not r.get('evidence') or not r.get('effective_from'):
            unresolved.append({'kind':'UNSOURCED_OR_UNDATED_PRIORITY','relationship':r});continue
        for a in r['evidence']: verify_anchor(a,documents)
        begin=date.fromisoformat(r['effective_from'])
        end=date.fromisoformat(r['effective_until']) if r.get('effective_until') else None
        if end is not None and end<=begin:raise LegalMathError('E_TIME')
        if when>=begin and (end is None or when<end): edges.append(r)
    outgoing={x:[] for x in ids}
    for r in edges:outgoing[r['higher']].append(r['lower'])
    visited=set();active=set()
    def cyclic(node):
        if node in active:return True
        if node in visited:return False
        active.add(node)
        if any(cyclic(n) for n in outgoing[node]):return True
        active.remove(node);visited.add(node);return False
    if any(cyclic(n) for n in sorted(ids)):
        unresolved.append({'kind':'PRIORITY_CYCLE'})
    lower={r['lower'] for r in edges}
    possible=sorted(ids-lower)
    status='CONDITIONALLY_ORDERED' if len(possible)==1 and not unresolved else 'UNRESOLVED_PRIORITY'
    return {'status':status,'selected':possible[0] if status=='CONDITIONALLY_ORDERED' else None,
            'active_relationships':edges,'findings':unresolved,'question':question,'at':at,
            'interpretation_of_priority_proved':False,'release_eligible':False}


def bilingual_pair(left, right, documents, *, relationship, assessment, residuals):
    verify_anchor(left,documents);verify_anchor(right,documents)
    a,b=documents[left['document_id']],documents[right['document_id']]
    if a['language']==b['language'] or a['authority_id']!=b['authority_id']:
        raise LegalMathError('E_REFERENCE')
    if not relationship or not assessment:
        raise LegalMathError('E_SCHEMA')
    return {'left':left,'right':right,'relationship':relationship,'assessment':assessment,
            'residuals':list(residuals),'status':'PROPOSED_PROVISION_ALIGNMENT',
            'semantic_equivalence_proved':False,'release_eligible':False,
            'binding':digest({'left':left,'right':right,'documents':documents})}


def replay_authority_bound_duty(request, authority_at_opening, current_authority):
    historical=replay(deepcopy(request))
    if not authority_at_opening or not current_authority:
        status='AUTHORITY_UNKNOWN'
    elif authority_at_opening != current_authority:
        status='AUTHORITY_CHANGED_REINVESTIGATION_REQUIRED'
    else: status='CONDITIONAL_DUTY_REPLAY'
    return {'status':status,'historical':historical,'authority_at_opening':authority_at_opening,
            'current_authority':current_authority,'current_assurance_usable':status=='CONDITIONAL_DUTY_REPLAY',
            'automatic_obligation_migration':False,'release_eligible':False}
