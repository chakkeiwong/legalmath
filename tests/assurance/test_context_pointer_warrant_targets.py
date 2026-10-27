from copy import deepcopy
from pathlib import Path
import json
import pytest
from jsonschema import validate, ValidationError
from legalmath.canonical import digest
from legalmath.errors import LegalMathError
from legalmath.interpretation.assurance.integration_contract import evidence_file
from legalmath.interpretation.assurance.monitor import save
from legalmath.interpretation.assurance.phased import capacity_checkpoint, context_disposition as context, review_repair
from legalmath.interpretation.search.providers import Completion
from tests.assurance.test_context_need_disposition import setup
from tests.assurance.test_source_review_repair import decision
from tests.assurance.test_bounded_product import envelope


@pytest.mark.parametrize('path', ['$.payload.answer.unresolved[4]','/payload/answer/conclusion',
    'conclusion','/missing','/unresolved/99'])
def test_context_schema_rejects_foreign_answer_paths(tmp_path,path):
    args=setup(tmp_path)
    value=deepcopy(args[-1])
    value['need_dispositions'][1]['answer_evidence']['path']=path
    with pytest.raises(ValidationError): validate(value,args[5])


def test_schema_exposes_exact_escaped_leaf_pointers(tmp_path):
    args=setup(tmp_path)
    answer={'one/two':{'tilde~key':['exact retained sentence']}}
    shape=context.schema(args[6],answer)
    paths=shape['properties']['need_dispositions']['items']['properties']['answer_evidence']['properties']['path']['enum']
    assert paths==['','/one~1two/tilde~0key/0']
    context.answer_quote(answer,paths[1],'retained sentence')
    with pytest.raises(LegalMathError): context.answer_quote(answer,paths[1],'invented sentence')


def test_actual_failed_canary_path_contract_is_reproduced_without_relabeling():
    root=Path(__file__).resolve().parents[2]
    folder=root/'artifacts/legal-mission-control/2026-10-23/p14-deployment/live/arms/p14/baseline'
    call=folder/'calls/audit-context-disposition-p14-f27ee3e41f98d678fc3e4711'
    request=json.loads((call/'request.json').read_text())
    raw=json.loads((call/'raw.json').read_text())['value']
    before=(call/'result.json').read_bytes()
    assert json.loads(before)['reason']=='Ambiguous numbered citation'
    answer=request['payload']['answer']; rows=request['payload']['prior_needs']
    with pytest.raises(ValidationError): validate(raw,context.schema(rows,answer))
    paths=[r['answer_evidence']['path'] for r in raw['need_dispositions']]
    assert paths==['$.payload.answer.conclusion','$.payload.answer.unresolved[4]']
    for pointer,row in zip(['/conclusion','/unresolved/4'],raw['need_dispositions']):
        context.answer_quote(answer,pointer,row['answer_evidence']['quote'])
    assert (call/'result.json').read_bytes()==before


def install_followup(p, value):
    save(p.root/'targets.json',value)
    save(p.root/'target-checkpoint.json',dict(profile=capacity_checkpoint.PROFILE,
        input_hash=p.route.input_hash,calls={},
        warrant_target_followup=evidence_file(p.root/'targets.json',p.root)))
    p.capacity_checkpoint=evidence_file(p.root/'target-checkpoint.json',p.root)


def test_exact_exclusion_preserves_verdict_and_refuses_altered_result(tmp_path):
    p,item,answer,initial,*_=setup(tmp_path)
    value=dict(considered=[item['id']],issues=['Dependency unnecessary'],verdict='REJECT')
    result=dict(status='VALIDATED',value=dict(decisions=[dict(issue_id='issue-0',disposition='WARRANTED',
        reason='Valid dependency objection, no answer defect.')]))
    save(tmp_path/'result.json',result)
    rule=dict(result=evidence_file(tmp_path/'result.json',tmp_path),value_hash=digest(result['value']),
        answer_hash=digest(answer),review_hash=digest(value),issue_ids=['issue-0'])
    followup=dict(profile='reviewed-warrant-target-followup.v1',retained_warrant_keys=['warrant-exact'],
                  exclusions={'warrant-exact':rule})
    install_followup(p,followup)
    assert review_repair.correction_issues(p,'warrant-exact',answer,value,result)==(set(),{'issue-0'})
    assert result['value']['decisions'][0]['disposition']=='WARRANTED'
    assert review_repair.correction_issues(p,'different',answer,value,result)==({'issue-0'},set())
    changed=deepcopy(result);changed['value']['decisions'][0]['reason']='Different'
    with pytest.raises(LegalMathError): review_repair.correction_issues(p,'warrant-exact',answer,value,changed)
    with pytest.raises(LegalMathError): review_repair.correction_issues(p,'warrant-exact',{'changed':True},value,result)


@pytest.mark.parametrize('damage',[None,'dependency','false_quote','foreign_path','unknown'])
def test_new_warrant_targets_and_full_reasons_reach_correction(tmp_path,damage):
    args=setup(tmp_path);p,item,answer=args[:3]
    source=p.route.records[item['origin_id']]
    rejected=dict(status='VALIDATED',value={**decision(source,'REJECT'),
        'considered':[item['id']],'issues':['The answer has an evidence-description error.']})
    install_followup(p,dict(profile='reviewed-warrant-target-followup.v1',retained_warrant_keys=[],exclusions={}))
    def complete(request,shape,settings):
        row=dict(issue_id='issue-0',disposition='WARRANTED',basis='DELIVERED_SOURCE',
            reason='Correct the supplied evidence description while preserving actual-client uncertainty.',
            support=[dict(record_id=source['id'],quote=source['text'],locator='')],blocking_source_gaps=[],
            correction_target='ANSWER_DEFECT',answer_evidence=dict(path='/conclusion',quote=answer['conclusion']))
        if damage=='dependency': row['correction_target']='DEPENDENCY_ONLY'
        if damage=='false_quote': row['answer_evidence']['quote']='Invented fact'
        if damage=='foreign_path': row['answer_evidence']['path']='$.conclusion'
        if damage=='unknown': row['correction_target']='UNDETERMINED'
        return Completion(dict(considered=request['required_considered'],source_gaps=[],
            assertion_bindings=[],decisions=[row]),{})
    p.provider.complete=complete
    assessed,warranted,settled=p.review_warrants('p14',envelope()['original_questions'][0],
        dict(value=answer),[rejected],[])
    if damage:
        assert assessed[0]['result']['status']=='FAILED' and not warranted and not settled
    else:
        assert settled, assessed
        assert warranted[0]['issue_assessments'][0]['answer_evidence']['path']=='/conclusion'
        assert 'actual-client uncertainty' in warranted[0]['issue_assessments'][0]['reason']
        assert warranted[0]['issues']==rejected['value']['issues']
