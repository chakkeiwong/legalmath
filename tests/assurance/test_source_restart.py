"""Fresh whole-source restart, immutable predecessor, and finite continuation."""
from copy import deepcopy
from pathlib import Path
import tempfile
import pytest
from legalmath.canonical import digest, loads
from legalmath.errors import LegalMathError
from legalmath.interpretation.assurance.complete_investigation import CompleteInvestigation, verify
from legalmath.interpretation.assurance.source_restart import snapshot
from legalmath.interpretation.assurance.investigation_answer import question_text
from tests.search.support import FunctionProvider
from .test_integration import settings, source, AT
from .test_round16 import JDK
from .test_successor_workflow import complete_responder

QUESTIONS=[{'question_id':'p10','text':'What fulfills the requirement?'},
           {'question_id':'evidence','text':'What evidence establishes it?'}]


def respondent(request):
    task=request.get('original_task',request['task'])
    if task=='REVIEW_SOURCE_CLAIMS':
        # The first branch exposes the omitted exception. The repaired branch
        # reads it afresh; the fixture does not imply legal reviewer accuracy.
        claims=request['claims']
        return {'request_binding':request['request_binding'],
            'checked_unit_ids':[u['unit_id'] for u in request['source_packet']['units']],
            'claims':[{'claim_id':c['claim_id'],'claim_hash':digest(c),
                'assessment':'RETAINED' if c['exceptions'] else 'QUESTIONED',
                'source_reading':c['statement'],'support':c['evidence'],'contrary':[],
                'qualifications':[],'missing_authorities':[],'nonlocal_claim_ids':[]} for c in claims],
            'unresolved_questions':[]}
    if task=='REVIEW_SOURCE_OMISSIONS':
        return {'checked_unit_ids':[u['unit_id'] for u in request['source_packet']['units']],
                'issues':[],'unresolved_questions':[]}
    value=complete_responder(request)
    if task=='SOURCE_INVENTORY' and not request.get('source_restart'):
        value['claims'][0]['exceptions']=[]
    return value


def test_real_full_restart_rereads_both_sources_and_rebuilds_every_stage(root):
    with tempfile.TemporaryDirectory(prefix='full-source-restart-',dir=root/'artifacts') as td:
        provider=FunctionProvider(respondent)
        config=settings(1).model_copy(update={'staged_source_review':True,'total_model_calls':40})
        runner=CompleteInvestigation(root,td,provider,JDK,AT,settings=config,maximum_scoped_actions=12,scoped_rounds=1)
        args=dict(original_questions=QUESTIONS)
        with pytest.raises(LegalMathError) as error:
            runner.run([source()],question_text(QUESTIONS),**args)
        assert error.value.code=='E_STALE_REVIEW'
        prior=loads((runner.directory/'current-state.json').read_bytes())['revision']
        prior_dir=runner.directory/'revisions'/prior
        before=snapshot(prior_dir); count=len(provider.requests)
        assert not list(prior_dir.glob('core/actions/*/formal'))
        result=runner.restart_sources(prior,[source()],question_text(QUESTIONS),**args)
        assert result['execution_complete'],result
        assert result['revision']!=prior and snapshot(prior_dir)==before
        fresh=provider.requests[count:]
        assert sum(r['task']=='SOURCE_INVENTORY' for r in fresh)==2
        assert {'REVIEW_SOURCE_CLAIMS','REVIEW_SOURCE_OMISSIONS','GENERATE','SOURCE_FIDELITY',
                'STRUCTURED_CRITICISM','DEFINE_EXACT_QUESTIONS','SCOPED_SOURCE_FIDELITY'} <= {r['task'] for r in fresh}
        assert all(r['original_questions']==QUESTIONS for r in fresh)
        assert all(r['source_restart']['predecessor_revision']==prior for r in fresh if r['task']=='SOURCE_INVENTORY')
        assert verify(root,result)['status']=='FILE_BOUND_INVESTIGATION_VERIFIED'
        count=len(provider.requests)
        assert runner.restart_sources(prior,[source()],question_text(QUESTIONS),**args)==result
        assert len(provider.requests)==count
        with pytest.raises(LegalMathError) as denied:
            runner.restart_sources(prior,[source()],question_text(QUESTIONS),maximum_restarts=2,**args)
        assert denied.value.code=='E_STALE_REVIEW'
        changed=source();changed['data']+=b' changed'
        with pytest.raises(LegalMathError):runner.restart_sources(prior,[changed],question_text(QUESTIONS),**args)
        prior_file=next(p for p in prior_dir.rglob('*.json'))
        prior_file.write_text('{}')
        with pytest.raises(LegalMathError):runner.restart_sources(prior,[source()],question_text(QUESTIONS),**args)
        assert len(provider.requests)==count


def test_forged_restart_refused_before_dispatch(tmp_path):
    provider=FunctionProvider(lambda r:pytest.fail('Unregistered restart dispatched'))
    runner=CompleteInvestigation(tmp_path,tmp_path/'run',provider,JDK,AT,settings=settings())
    with pytest.raises(LegalMathError):
        runner.run([source()],question_text(QUESTIONS),original_questions=QUESTIONS,
                   source_restart={'profile':'full-source-restart.v1','number':1})
    assert not provider.requests
