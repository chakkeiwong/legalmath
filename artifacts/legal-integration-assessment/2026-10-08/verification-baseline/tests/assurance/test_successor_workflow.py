from copy import deepcopy
from pathlib import Path
import tempfile
import pytest
from legalmath.errors import LegalMathError
from legalmath.interpretation.assurance.complete_investigation import CompleteInvestigation,verify
from tests.search.support import FunctionProvider
from tests.search.test_formal import AT
from .test_integration import responder,source,settings


def complete_responder(request):
    task=request['task'];p=request['source_packet'];e=[{'unit_id':p['units'][0]['unit_id'],'quote':p['units'][0]['text']}]
    if task=='DEFINE_EXACT_QUESTIONS':
        return {'assignments':[{'candidate_id':cid,'assignment_status':'PROPOSED',
            'question':{'control_id':'gift.'+str(i),'question':'Is this gift offer prohibited?',
                'unit_of_assessment':'one offer','actor':'distributor','temporal_basis':'declared fixture date',
                'result_kind':'PROHIBITED','true_means':'gift prohibited','false_means':'this prohibition not established',
                'source_evidence':e}} for i,cid in enumerate(request['candidates'])]}
    if task=='SCOPED_SOURCE_FIDELITY':
        candidates={r['candidate_id']:r for r in request['candidates']}
        return {'checks':[{'claim_id':pair['claim_id'],'candidate_id':pair['candidate_id'],
            'source_support':{'status':'SUPPORTED','evidence':e,'rationale':'Declared fixture clause'},
            'question_relation':{'status':'RELEVANT','question_hash':candidates[pair['candidate_id']]['question_hash'],
                                 'evidence':e,'rationale':'Same fixture gift question'},
            'executable_correspondence':{'status':'PRESERVES','representation_quotes':[candidates[pair['candidate_id']]['representation']],
                                         'rationale':'The declared fixture includes the exception'},
            'authority':{'status':'NONE_DECLARED','dependency_ids':[],'rationale':'No fixture dependency'},
            'followup_questions':[]} for pair in request['required_pairs']],'additional_concerns':[]}
    return responder()(request)


@pytest.fixture(scope='module')
def investigation():
    root=Path(__file__).resolve().parents[2]
    with tempfile.TemporaryDirectory(prefix='complete-investigation-',dir=root/'artifacts') as td:
        provider=FunctionProvider(complete_responder)
        runner=CompleteInvestigation(root,td,provider,root/'.localresources/java-toolchain/jdk-17.0.20.1+1',AT,
                                     settings=settings(),maximum_scoped_actions=12,scoped_rounds=1)
        result=runner.run([source()],'Selected gift control')
        yield root,runner,provider,result


def test_real_search_scoped_judgments_lean_and_java_form_one_investigation(investigation):
    root,runner,provider,r=investigation
    assert r['execution_complete'],r['core']['interpretation']['report']
    assert r['scoped']['pairs_with_two_validated_proposals']>0
    assert any(p['status']=='CHECKED' for p in r['proofs'])
    assert r['replay'] and verify(root,r)['status']=='FILE_BOUND_INVESTIGATION_VERIFIED'
    count=len(provider.requests)
    again=runner.run([source()],'Selected gift control')
    assert len(provider.requests)==count and again['revision']==r['revision']
    assert verify(root,r)['status']=='FILE_BOUND_INVESTIGATION_VERIFIED'


@pytest.mark.parametrize('mutation',['questions','proofs','execution','legal'])
def test_summary_cannot_hide_issues_or_strengthen_claims(investigation,mutation):
    root,_,_,r=investigation;v=deepcopy(r)
    if mutation=='questions':v['questions']['assignments']=[]
    elif mutation=='proofs':v['proofs']=[]
    elif mutation=='execution':v['execution_complete']=not v['execution_complete']
    else:v['legal_correctness_established']=True
    with pytest.raises(LegalMathError):verify(root,v)


def test_changed_source_creates_new_revision_and_preserves_original_evidence(investigation):
    root,runner,provider,old=investigation
    changed=source();changed['data']=changed['data'].replace(b'A distributor',b'An intermediary distributor')
    count=len(provider.requests)
    new=runner.run([changed],'Selected gift control')
    assert new['revision']!=old['revision'] and len(provider.requests)>count
    assert verify(root,old)['status']=='FILE_BOUND_INVESTIGATION_VERIFIED'
    assert verify(root,new)['status']=='FILE_BOUND_INVESTIGATION_VERIFIED'
    import json
    history=json.loads((runner.directory/'revisions.json').read_text())
    assert len(history)==2 and history[-1]['predecessor']==old['revision']
    from legalmath.interpretation.assurance.complete_investigation import current
    with pytest.raises(LegalMathError):current(root,runner.directory,old['revision'])
    assert current(root,runner.directory,new['revision'])['revision']==new['revision']
