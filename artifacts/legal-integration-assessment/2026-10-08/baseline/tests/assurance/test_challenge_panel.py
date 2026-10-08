from copy import deepcopy
import pytest
from legalmath.canonical import digest, loads
from legalmath.errors import LegalMathError
from legalmath.interpretation.assurance import challenge_panel as panel, readable_tables
from legalmath.interpretation.assurance.diversity import save
from tests.search.support import FunctionProvider
from .test_challenge_contract import inputs
from .test_continuation_references import encode_quotes


def decode(request):
    if 'challenge_encoding' in request:
        from legalmath.interpretation.assurance import readable_challenges
        return readable_challenges.decode(request,expected_request_hash=request['input_encoding']['original_request_hash'])
    return readable_tables.decode(request,expected_request_hash=request['input_encoding']['original_request_hash']) if 'input_encoding' in request else request


def response(wire, *, differs=False, premise=False):
    request=decode(wire); role=request['role']; p=request['source_packet']
    selected=set(request['selected_obligation_ids']); e=[{'unit_id':p['units'][0]['unit_id'],'quote':p['units'][0]['text']}]
    result={'binding_hash':request['binding_hash'],'answers':[
        {k:o[k] for k in ('obligation_id','candidate_hash','question_hash')} |
        {'status':'PROPOSED_SUPPORTED', 'evidence':e,
         'rationale':role if differs else 'Controlled explanation', 'followup_question':None}
        for o in request['obligations'] if o['obligation_id'] in selected],
        'alternative_readings':[],'unrepresented_concerns':[],'proposed_formal_premises':[]}
    if premise:
        cid=next(iter(request['candidates']));q=request['questions'][cid]
        result['proposed_formal_premises']=[{'candidate_id':cid,'question_hash':digest(q),
            'when':'discount','expected':False,'evidence':e,'rationale':'Declared mathematical mutation challenge'}]
    return encode_quotes(result,request['source_references'])


def test_full_context_and_round_first_blindness_with_bounded_followup(tmp_path):
    p,r,q,_=inputs(); provider=FunctionProvider(lambda req:response(req,differs=True))
    result=panel.run(p,r,q,dict.fromkeys(panel.ROLES,provider),tmp_path,batch_size=4,rounds=2)
    assert len(provider.requests)==12 and result['followup_limit_reached']
    assert len(result['response_differences'])==9 and result['execution_complete']
    first=[decode(req) for req in provider.requests[:6]]
    assert all('prior_round_evidence' not in req for req in first)
    assert all(req['source_packet']==p and req['candidates']==r for req in first)
    second=[decode(req) for req in provider.requests[6:]]
    assert all(req['prior_round_evidence']==second[0]['prior_round_evidence'] for req in second)
    assert all(len(req['selected_obligation_ids'])<=4 for req in first+second)
    assert panel.verify(tmp_path,p,r,q)==result

    assert panel.run(p,r,q,dict.fromkeys(panel.ROLES,provider),tmp_path,batch_size=4,rounds=2)==result
    assert len(provider.requests)==12


def test_unanimous_readers_do_not_hide_formal_exception_counterexample(tmp_path):
    p,r,q,_=inputs();r['candidate.a']['formalization']['result']='gift'
    provider=FunctionProvider(lambda req:response(req,premise=True))
    result=panel.run(p,r,q,dict.fromkeys(panel.ROLES,provider),tmp_path,rounds=2)
    assert not result['response_differences']
    assert result['formal_checks'][0]['certificate']['status']=='CONDITIONALLY_REJECTED'
    assert result['formal_checks'][0]['certificate']['witnesses']
    assert result['retained_candidate_ids']==['candidate.a'] and not result['legal_candidates_removed']
    assert result['followup_limit_reached']
    assert not result['methods']['statistical_independence_established']
    assert result['methods']['distinct_configured_routes']==1
    assert panel.verify(tmp_path,p,r,q)==result
    later=[decode(req) for req in provider.requests if decode(req).get('round')==2]
    assert later and all(req['independent_formal_checks']['candidate.a']['witnesses'] for req in later)
    assert all(req['declared_grammar_alternatives']['candidate.a']['expressions'] for req in later)


def test_invalid_response_keeps_full_denominator_and_spends_attempt(tmp_path):
    p,r,q,_=inputs()
    def bad(req):
        value=response(req);value['answers'].pop();return value
    provider=FunctionProvider(bad)
    result=panel.run(p,r,q,dict.fromkeys(panel.ROLES,provider),tmp_path,rounds=3)
    assert len(provider.requests)==6 and not result['execution_complete']
    assert len(result['missing_perspectives'])==9 and len(result['failed_actions'])==6
    assert all(v['spent']==3 for counts in result['issue_histories'].values() for v in counts.values())
    assert panel.verify(tmp_path,p,r,q)==result


def test_global_action_exhaustion_does_not_invent_answers(tmp_path):
    p,r,q,_=inputs();provider=FunctionProvider(lambda req:response(req,differs=True))
    result=panel.run(p,r,q,dict.fromkeys(panel.ROLES,provider),tmp_path,rounds=3,maximum_actions=2)
    assert len(provider.requests)==2 and result['failed_actions'] and not result['execution_complete']
    assert panel.verify(tmp_path,p,r,q)==result


def test_forged_summary_cannot_replace_actual_model_answer(tmp_path):
    p,r,q,_=inputs();provider=FunctionProvider(response)
    result=panel.run(p,r,q,dict.fromkeys(panel.ROLES,provider),tmp_path,rounds=1)
    history=loads((tmp_path/'history.json').read_bytes());history[0]['value']['answers'][0]['rationale']='Forged'
    save(tmp_path/'history.json',history)
    with pytest.raises(LegalMathError):panel.verify(tmp_path,p,r,q)


def test_changed_batch_boundary_cannot_reset_same_panel(tmp_path):
    p,r,q,_=inputs();provider=FunctionProvider(response)
    panel.run(p,r,q,dict.fromkeys(panel.ROLES,provider),tmp_path,batch_size=12,rounds=1)
    with pytest.raises(LegalMathError):panel.run(p,r,q,dict.fromkeys(panel.ROLES,provider),tmp_path,batch_size=4,rounds=1)


def test_role_names_do_not_create_independent_families():
    a=FunctionProvider(response);b=FunctionProvider(response)
    summary=panel.method_dependencies(panel.configuration(dict(zip(panel.ROLES,(a,b)))))
    assert summary['distinct_configured_routes']==1
    assert not summary['distinct_model_families_established']


def test_live_route_without_shared_allowance_is_rejected(tmp_path):
    a=FunctionProvider(response);a.live=True
    with pytest.raises(LegalMathError):panel.configuration(dict.fromkeys(panel.ROLES,a))


def test_deleted_history_cannot_hide_an_executed_disagreement(tmp_path):
    p,r,q,_=inputs();provider=FunctionProvider(lambda req:response(req,differs=True))
    panel.run(p,r,q,dict.fromkeys(panel.ROLES,provider),tmp_path,rounds=2)
    history=loads((tmp_path/'history.json').read_bytes());history=history[:-2]
    save(tmp_path/'history.json',history)
    with pytest.raises(LegalMathError):panel.verify(tmp_path,p,r,q)


def test_new_profile_inherits_original_spending_and_stops_failed_pilot(tmp_path):
    p,r,q,_=inputs();provider=FunctionProvider(response)
    first=panel.run(p,r,q,dict.fromkeys(panel.ROLES,provider),tmp_path/'original',rounds=1)
    inherited={role:{oid:{**row,'evidence_hash':'a'*64} for oid,row in rows.items()}
               for role,rows in first['issue_histories'].items()}
    second=panel.run(p,r,q,dict.fromkeys(panel.ROLES,provider),tmp_path/'repair',rounds=1,
                     input_profile='readable-challenges.v1',inherited_issues=inherited)
    assert all(row['spent']==2 for rows in second['issue_histories'].values() for row in rows.values())
    assert all(second['issue_histories'][role][oid]['started_ms']==row['started_ms']
               for role,rows in inherited.items() for oid,row in rows.items())
    bad=FunctionProvider(lambda req:{})
    result=panel.run(p,r,q,dict.fromkeys(panel.ROLES,bad),tmp_path/'pilot',rounds=1,
                     batch_size=4,input_profile='readable-challenges.v1',pilot_guard=True)
    assert len(bad.requests)==2 and result['pilot_stopped'] and not result['execution_complete']
    assert panel.verify(tmp_path/'pilot',p,r,q)==result


def test_wrong_model_identity_is_recorded_and_partial_recovery_uses_no_calls(tmp_path):
    p,r,q,_=inputs()
    def stale(req):
        value=response(req);value['binding_hash']='0'*64;return value
    provider=FunctionProvider(stale)
    result=panel.run(p,r,q,dict.fromkeys(panel.ROLES,provider),tmp_path,rounds=1,pilot_guard=True)
    assert len(provider.requests)==2 and all(r['error']=='E_REFERENCE' for r in result['history'])
    assert not result['execution_complete']
    history=loads((tmp_path/'history.json').read_bytes())
    save(tmp_path/'history.json',history[:-1])
    recovered=panel.recover_partial(tmp_path,p,r,q)
    assert len(provider.requests)==2 and len(recovered['history'])==2
    assert recovered['journal_actions']==2 and not recovered['execution_complete']
