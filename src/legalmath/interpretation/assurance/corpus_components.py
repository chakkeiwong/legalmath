"""Consume independent scoped corpus reviews without declaring the corpus complete.

Source research has no answer prerequisite. An answer-use review binds only its
own answer. Final aggregation still requires all four original questions.
"""
from copy import deepcopy
from datetime import datetime
from legalmath.canonical import digest
from .bounded_context import require
from . import corpus_review as corpus

PROFILE = 'independent-corpus-review-components.v1'

def context(root, expected):
    require(expected.get('profile') == PROFILE and isinstance(expected.get('scope'), str)
        and expected['scope'].strip(), 'Missing independent corpus review scope', 'E_INTEGRITY')
    when = datetime.fromisoformat(expected['as_of'].replace('Z', '+00:00'))
    require(when.tzinfo is not None, 'Corpus as-of time needs timezone', 'E_INTEGRITY')
    require(set(expected['required_propositions']) == corpus.QUESTIONS,
        'Lost original question population', 'E_INTEGRITY')
    for ids in expected['required_propositions'].values():
        require(isinstance(ids,list) and ids and all(isinstance(i,str) and i for i in ids)
            and len(ids) == len(set(ids)), 'Invalid proposition population', 'E_INTEGRITY')
    require(expected.get('sources'), 'Empty corpus source population', 'E_INTEGRITY')
    for ref in expected['sources'].values(): corpus.checked_file(root, ref)
    fidelity = corpus.read(root, expected['fidelity'])
    require(fidelity.get('fidelity_reconciled') is True and fidelity.get('evidence'),
        'Corpus fidelity remains unqualified', 'E_INTEGRITY')
    for ref in fidelity['evidence']: corpus.checked_file(root, ref)
    return digest(expected), fidelity

def envelope(root, expected, reference, kind):
    identity, fidelity = context(root, expected)
    value = corpus.read(root, reference)
    require(value.get('profile') == PROFILE and value.get('kind') == kind
        and value.get('context_hash') == identity and value.get('scope') == expected['scope']
        and value.get('as_of') == expected['as_of'], 'Stale corpus component', 'E_INTEGRITY')
    require(isinstance(value.get('reviewer'),str) and value['reviewer'].strip()
        and bool(corpus.checked_file(root,value['review_note']).strip()),
        'Missing substantive component review', 'E_INTEGRITY')
    return value, fidelity

def result(kind, remaining, reference, **extra):
    return dict(profile=PROFILE, kind=kind, review_complete=True,
        status='QUALIFIED' if not remaining else 'REVIEWED_WITH_LIMITATIONS',
        qualified=not remaining, remaining=remaining, review=reference,
        corpus_acceptance_complete=False, legal_correctness_established=False, **extra)

def source_review(root, expected, reference):
    value, fidelity = envelope(root,expected,reference,'source')
    row=value['review']; sid=row['source_id']
    require(sid in expected['sources'] and row['source']==expected['sources'][sid]
        and row.get('version'), 'Foreign source component', 'E_INTEGRITY')
    remaining=[]
    for duty in ('applicability','later_treatment'):
        finding=row[duty]
        require(finding.get('status') in ('QUALIFIED','UNRESOLVED','REJECTED')
            and isinstance(finding.get('finding'),str) and finding['finding'].strip(),
            'Missing substantive source finding', 'E_INTEGRITY')
        # Even limitations retain the exact evidence searched or inspected.
        require(finding.get('search_evidence'), 'Missing dated research evidence', 'E_INTEGRITY')
        for ref in finding['search_evidence']: corpus.checked_file(root,ref)
        if finding['status']=='QUALIFIED':
            corpus.support(root,finding['primary_evidence'],expected['sources'],set(expected['sources']),fidelity)
        else: remaining.append(sid+': '+duty+' '+finding['status'])
    return result('source',remaining,reference,source_id=sid)

def answer_review(root, expected, answer, reference):
    value, fidelity=envelope(root,expected,reference,'answer')
    row=value['review']; q=row['question']
    require(q in corpus.QUESTIONS and row['answer']==answer, 'Stale answer component', 'E_INTEGRITY')
    answer_value=corpus.read(root,answer)
    props=row['propositions']; ids=[p['id'] for p in props]
    require(len(ids)==len(set(ids)) and set(ids)==set(expected['required_propositions'][q]),
        'Incomplete proposition population', 'E_INTEGRITY')
    remaining=[]
    for p in props:
        require(p.get('status') in ('SUPPORTED','UNRESOLVED','REJECTED')
            and isinstance(p.get('reason'),str) and p['reason'].strip()
            and isinstance(p.get('source_ids'),list) and p['source_ids']
            and set(p['source_ids'])<=set(expected['sources']), 'Invalid proposition finding', 'E_INTEGRITY')
        if p['status']=='SUPPORTED':
            corpus.support(root,p['primary_evidence'],expected['sources'],set(p['source_ids']),fidelity)
            corpus.answer_support(answer_value,p.get('answer_evidence'))
        else: remaining.append(q+': '+p['id']+' '+p['status'])
    return result('answer',remaining,reference,question=q,answer=answer)

def aggregate(root, expected, sources, answers):
    identity,_=context(root,expected)
    require(set(sources)<=set(expected['sources']) and set(answers)<=corpus.QUESTIONS,
        'Foreign corpus component key', 'E_INTEGRITY')
    remaining=[]; checked=[]
    for sid in sorted(expected['sources']):
        if sid not in sources:
            remaining.append('Missing source review: '+sid); continue
        row=source_review(root,expected,sources[sid])
        require(row['source_id']==sid,'Wrong source review slot','E_INTEGRITY')
        checked.append(row);remaining+=row['remaining']
    for q in sorted(corpus.QUESTIONS):
        if q not in answers:
            remaining.append('Missing answer review: '+q);continue
        item=answers[q];row=answer_review(root,expected,item['answer'],item['review'])
        require(row['question']==q,'Wrong answer review slot','E_INTEGRITY')
        checked.append(row);remaining+=row['remaining']
    return dict(profile=PROFILE,context_hash=identity,components=checked,remaining=remaining,
        review_population_complete=len(checked)==len(expected['sources'])+len(corpus.QUESTIONS),
        ready_for_final_controls=not remaining,corpus_acceptance_complete=False,
        legal_correctness_established=False)

def final_context(root, expected, answers):
    """Bridge independently reviewed components to the unchanged final validator."""
    context(root,expected)
    require(set(answers)==corpus.QUESTIONS,'Final corpus still needs four answers','E_INTEGRITY')
    value=deepcopy(expected);value['profile']=corpus.PROFILE;value['answers']=answers
    corpus.expected_context(root,value)
    return value

def consume(root, registration, *, fidelity, reconciled_sources):
    """Actual corpus-handler entry: retain incomplete work without requiring answers."""
    expected=corpus.read(root,registration['expected_context'])
    require(corpus.read(root,expected['fidelity'])==fidelity,
        'Components do not bind current fidelity reconciliation','E_INTEGRITY')
    require(all(expected['sources'].get(k)==v for k,v in reconciled_sources.items()),
        'Components omit reconciled sources','E_INTEGRITY')
    manifest=corpus.read(root,registration['components'])
    require(manifest.get('profile')==PROFILE and manifest.get('context_hash')==context(root,expected)[0],
        'Foreign corpus component manifest','E_INTEGRITY')
    outcome=aggregate(root,expected,manifest['sources'],manifest['answers'])
    # Components are useful evidence while final qualification is still blocked.
    outcome['status']='BLOCKED'
    outcome['remaining'] += ['Final positive, wrong-source and false-attribution controls']
    return outcome
