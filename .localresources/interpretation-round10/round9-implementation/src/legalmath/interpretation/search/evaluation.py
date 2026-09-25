"""Paired, complete accounting; abstention is visible and never an accuracy win."""
from math import comb
from ...errors import LegalMathError
from ...canonical import digest


def compare_frozen(service,caller,baseline,candidate,references):
    """Load held-out labels from the distinct-reviewer adjudication path.

    A reference maps an evaluation case to a run_id and source_unit_id. Open
    adjudication questions are unadjudicated, even when provisional readings exist.
    This never verifies that registry entries belong to actual independent humans.
    """
    labels={};hashes={}
    with service.db.connect() as con:
        service.lc.require(con,caller,'meaning')
        for case,ref in references.items():
            freeze=service._get(con,ref['run_id'],'reference-freeze','freeze')
            disposition=freeze['dispositions'].get(ref['source_unit_id'])
            if disposition is None:raise LegalMathError('E_REFERENCE')
            labels[case]={'source_hash':freeze['packet_hash'],
                          'accepted':None if disposition['unresolved'] else disposition['accepted_readings']}
            hashes[case]=digest(freeze)
    return {**compare_runs(baseline,candidate,labels),'reference_freeze_hashes':hashes,
            'reference_authority':'LOCAL_REVIEWER_ATTESTATIONS; HUMAN_IDENTITY_NOT_VERIFIED'}


def compare_runs(baseline,candidate,reference):
    # Reference verdicts are supplied only after adjudication, never derived from model agreement.
    if set(baseline)!=set(candidate) or set(reference)!=set(candidate):raise LegalMathError('E_REFERENCE')
    counts={arm:{'unsafe_clean':0,'correct_clean':0,'blocked':0,'unadjudicated':0} for arm in ('baseline','candidate')}
    improved=worsened=0
    for ident,ref in reference.items():
        a,b=baseline[ident],candidate[ident]
        if a['source_hash']!=b['source_hash'] or a['budget']!=b['budget'] or ref['source_hash']!=a['source_hash']:
            raise LegalMathError('E_INTEGRITY',details='Paired source/budget mismatch')
        for label,row in [('baseline',a),('candidate',b)]:
            if row['status'] not in ('CLEAN','BLOCKED'):raise LegalMathError('E_SCHEMA')
            if ref['accepted'] is None:counts[label]['unadjudicated']+=1
            elif row['status']=='BLOCKED':counts[label]['blocked']+=1
            else:counts[label]['correct_clean' if row['decision'] in ref['accepted'] else 'unsafe_clean']+=1
        if ref['accepted'] is not None:
            unsafe=lambda r:r['status']=='CLEAN' and r['decision'] not in ref['accepted']
            improved+=int(unsafe(a) and not unsafe(b));worsened+=int(unsafe(b) and not unsafe(a))
    n=improved+worsened
    # Exact paired binary sign probability is descriptive unless reference units are independent.
    numerator=min(2**n,2*sum(comb(n,k) for k in range(min(improved,worsened)+1))) if n else 1
    return {'counts':counts,'paired_unsafe_reductions':improved,'paired_unsafe_increases':worsened,
            'exact_discordance_probability':{'numerator':str(numerator),'denominator':str(2**n if n else 1)},
            'ranking_supported':False,'promotion_eligible':False,
            'remaining_requirements':['Independent reviewed reference','Circular-family clustering','Predeclared coverage and unsafe-result thresholds'],
            'interpretation':'Blocking everything can reduce unsafe clean outcomes without demonstrating useful interpretation accuracy.'}
