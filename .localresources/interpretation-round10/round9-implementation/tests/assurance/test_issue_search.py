from copy import deepcopy
from pathlib import Path

import pytest

from legalmath.canonical import digest
from legalmath.errors import LegalMathError
from legalmath.interpretation.assurance.issue_search import (
    validate_issue,hypothesis_request,validate_hypotheses,merge_hypotheses,
    distinguish,audit_request,validate_audit,
)
from legalmath.interpretation.search.formal import Comparisons
from tests.assurance.test_output_semantics import inputs,AT,JDK


def data():
    packet,reading=inputs()
    packet['units'][0]['text']='A genuine family arrangement that is not a business or has a profit objective should ordinarily receive this guidance.'
    packet['selected_slice']='Under the proposed parse, does the qualified guidance antecedent apply?'
    reading['subject']=packet['selected_slice']
    reading['citations']=[{'unit_id':'p1','quote':packet['units'][0]['text']}]
    reading['formalization']['facts']=[{'name':name,'type':'bool','meaning':meaning,'unit':'truth value','source_unit_ids':['p1'],
        'requires_judgment':True} for name,meaning in [('genuine','The arrangement is genuine'),('business','The arrangement is run as a business'),('profit','It has a profit objective')]]
    reading['formalization']['result']='(and genuine (not (or business profit)))'
    reading['assumptions']=['Negation scopes over both business and profit alternatives; this predicate does not establish exemption.']
    issue={'issue_id':'fixture.negation','source_packet_hash':digest(packet),'question':packet['selected_slice'],
        'target':reading['citations'],'facts':deepcopy(reading['formalization']['facts']),
        'abstraction_assumptions':['The vocabulary supplies antecedent facts, not a legal conclusion.'],
        'retained_qualifications':['Should ordinarily remains qualified guidance, not an unconditional exemption.']}
    reading['assumptions']+=issue['abstraction_assumptions']+issue['retained_qualifications']
    return packet,reading,issue


def response(reading):return {'readings':[reading],'vocabulary_concerns':[],'questions':['Fixture ambiguity remains open.']}


def test_blind_breadth_requests_do_not_receive_peers_and_challenger_must():
    p,r,issue=data()
    for role in ('syntax-reader','context-reader'):
        assert 'prior_hypotheses' not in hypothesis_request(issue,p,role)
        with pytest.raises(LegalMathError):hypothesis_request(issue,p,role,prior={})
    with pytest.raises(LegalMathError):hypothesis_request(issue,p,'missing-reading-challenger')
    assert hypothesis_request(issue,p,'missing-reading-challenger',prior={'a':r})['prior_hypotheses']=={'a':r}


@pytest.mark.parametrize('defect',['quote','vocabulary','subject','convention','no-assumption','undeclared-fact'])
def test_generation_cannot_hide_disputed_meaning_in_changed_facts(defect):
    p,r,issue=data();bad=deepcopy(r)
    if defect=='quote':bad['citations'][0]['quote']='Invented source rule'
    elif defect=='vocabulary':bad['formalization']['facts'][1]['meaning']='The answer to this whole disputed issue'
    elif defect=='subject':bad['subject']='Is the office legally exempt?'
    elif defect=='convention':bad['statement']='[TRUE_IS_COMPLIANT] This is compliance.'
    elif defect=='no-assumption':bad['assumptions']=[]
    else:bad['formalization']['result']='not_declared'
    with pytest.raises(LegalMathError):validate_hypotheses(response(bad),issue,p,AT)


def test_identical_votes_do_not_inflate_executable_diversity_and_limits_are_visible():
    p,r,issue=data();other=deepcopy(r);other['local_id']='other';other['distinction']='Independent fixture repetition'
    merged=merge_hypotheses({'syntax-reader':response(r),'context-reader':response(other)},issue,p,AT)
    assert len(merged['candidates'])==1 and merged['distinct_encoded_expressions']==1
    assert len(next(iter(merged['origins'].values())))==2 and not merged['legal_diversity_established']
    other['formalization']['result']='(and genuine (or (not business) profit))'
    capped=merge_hypotheses({'syntax-reader':response(r),'context-reader':response(other)},issue,p,AT,maximum=1)
    assert len(capped['deferred'])==1 and capped['deferred'][0]['reading']==other


def test_all_distinctions_replay_in_java_and_unknown_conflict_are_retained(tmp_path):
    p,r,issue=data();rival=deepcopy(r);rival['local_id']='rival'
    rival['formalization']['result']='(and genuine (or (not business) profit))'
    rival['assumptions']=['Negation applies only to business; profit is the second disjunct.',
                         *issue['abstraction_assumptions'],*issue['retained_qualifications']]
    duplicate=deepcopy(r);duplicate['statement']+=' Same formula expressed with additional prose.'
    merged=merge_hypotheses({'syntax-reader':response(r),'context-reader':response(rival),
        'missing-reading-challenger':response(duplicate)},issue,p,AT)
    checker=Comparisons(tmp_path/'java',JDK,AT)
    result=distinguish(issue,p,merged['candidates'],checker)
    assert result['java_cases']==192 and result['comparisons'][0]['status']=='DIFFERENT'
    assert result['ranked_scenarios'][0]['score']==1 and len(result['behavior_groups'])==2
    assert not result['release_eligible'] and not result['legal_source_commitment_resolved']
    for rows in result['outputs'].values():
        statuses={row['java']['status'] for row in rows}
        assert statuses=={'TRUE','FALSE','UNKNOWN','CONFLICT'}
    request=audit_request(issue,p,merged['candidates'],result,'source-critic')
    assert len(request['distinguishing_scenarios'])==4
    candidates=merged['candidates']
    value={'judgments':[{'candidate_id':cid,'judgment':'UNRESOLVED_READING','source_evidence':r['citations'],
         'rationale':'Both attachments are proposed in a deliberately ambiguous fixture.',
         'unresolved_question':'Which attachment is intended?'} for cid in candidates],
         'missed_readings':[],'vocabulary_concerns':[],'questions':['No source-supported priority established.']}
    assert validate_audit(value,p,candidates)==value
    value['judgments'].pop()
    with pytest.raises(LegalMathError):validate_audit(value,p,candidates)


def test_capacity_is_rejected_before_any_java_build(tmp_path):
    p,r,issue=data();checker=Comparisons(tmp_path/'java',JDK,AT)
    with pytest.raises(LegalMathError):distinguish(issue,p,{'a':r},checker,maximum_cases=1)
    assert not (tmp_path/'java').exists()


def test_discrepancies_require_semantic_reconsideration_and_uncertainty_survives_limit():
    from legalmath.interpretation.assurance.issue_search import reconsideration_required,uncertainty_report
    p,r,issue=data();merged=merge_hypotheses({'syntax-reader':response(r)},issue,p,AT)
    cid=next(iter(merged['candidates']))
    review={'judgments':[{'candidate_id':cid,'judgment':'SUPPORTED_READING','source_evidence':r['citations'],
        'rationale':'Fixture support.','unresolved_question':None}], 'missed_readings':[], 'vocabulary_concerns':[], 'questions':[]}
    assert not reconsideration_required({'a':review})
    assert reconsideration_required({'a':review},merged)
    assert uncertainty_report(merged,{'a':review},2,2)['retry_limit_reached']
    for field in ('missed_readings','vocabulary_concerns','questions'):
        challenged=deepcopy(review);challenged[field]=['An unresolved source question.']
        assert reconsideration_required({'a':challenged})
        result=uncertainty_report(merged,{'a':challenged},2,2)
        assert result['retry_limit_reached'] and result['status']=='UNCERTAINTY_RETAINED'
        assert not result['release_eligible'] and result['all_reviews']['a']==challenged
    with pytest.raises(LegalMathError):hypothesis_request(issue,p,'discrepancy-reviser')
    assert hypothesis_request(issue,p,'discrepancy-reviser',prior={'criticism':'Missing parse'})['prior_hypotheses']


def test_missing_expression_gets_capacity_before_repeated_prose_variants():
    p,r,issue=data();a=deepcopy(r);a['statement']+=' A differently phrased explanation.'
    b=deepcopy(r);b['formalization']['result']='(and genuine (or (not business) profit))'
    merged=merge_hypotheses({'syntax-reader':response(r),'context-reader':response(a),
        'missing-reading-challenger':response(b)},issue,p,AT,maximum=2)
    assert len(merged['candidates'])==2 and len(merged['deferred'])==1
    assert {v['formalization']['result'] for v in merged['candidates'].values()}=={
        r['formalization']['result'],b['formalization']['result']}
    assert merged['deferred'][0]['reading']==a


def test_invalid_proposal_survives_repair_without_silent_scope_or_formula_edit(tmp_path):
    from legalmath.interpretation.assurance.recovery import invalid_generation_proposals
    from legalmath.interpretation.assurance.checkpoints import seal
    from legalmath.interpretation.assurance.monitor import save
    p,r,issue=data();bad=deepcopy(r)
    bad['statement']='Missing output marker; the proposed antecedent has two alternatives.'
    bad['formalization']['scope']='Prose is not an executable expression'
    bad['formalization']['result']='(and genuine (or (not business) (not profit)))'
    attempt=tmp_path/'attempt-001';attempt.mkdir()
    save(attempt/'request.json',hypothesis_request(issue,p,'syntax-reader'))
    save(attempt/'response.json',{'value':response(bad)})
    save(attempt/'outcome.json',{'status':'FAILED','error':'E_SCHEMA','details':'Invalid scope'})
    seal(attempt)
    result=invalid_generation_proposals(tmp_path,issue,p)
    assert result['records'][0]['original_reading']==bad
    assert not result['semantic_edits_performed'] and result['unvalidated_proposals']==1
    other=deepcopy(issue);other['question']='Changed question'
    with pytest.raises(LegalMathError):invalid_generation_proposals(tmp_path,other,p)
    save(attempt/'response.json',{'value':response(r)})
    with pytest.raises(LegalMathError):invalid_generation_proposals(tmp_path,issue,p)


def test_nonexecutable_interpretation_is_retained_without_an_invented_java_answer(tmp_path):
    from legalmath.interpretation.assurance.issue_search import reconsideration_required
    p,r,issue=data();r['formalization']=None
    r['questions']=['The supplied facts cannot express this plausible source qualification.']
    merged=merge_hypotheses({'syntax-reader':response(r)},issue,p,AT)
    assert len(merged['candidates'])==1 and merged['distinct_encoded_expressions']==0
    checker=Comparisons(tmp_path,JDK,AT);report=distinguish(issue,p,merged['candidates'],checker)
    assert report['java_cases']==0 and not report['outputs'] and report['unencoded_candidates']
    request=audit_request(issue,p,merged['candidates'],report,'source-critic')
    assert request['unencoded_candidates'] and len(request['candidates'])==1
    cid=next(iter(merged['candidates']))
    review={'judgments':[{'candidate_id':cid,'judgment':'SUPPORTED_READING','source_evidence':r['citations'],
        'rationale':'Source support does not supply an implementation.','unresolved_question':None}],
        'missed_readings':[],'vocabulary_concerns':[],'questions':[]}
    merged['concerns']=[]
    assert reconsideration_required({'critic':review},merged)
    r['questions']=[]
    with pytest.raises(LegalMathError):validate_hypotheses(response(r),issue,p,AT)
