from copy import deepcopy
from pathlib import Path
from tempfile import TemporaryDirectory
import pytest

from legalmath.canonical import loads
from legalmath.errors import LegalMathError
from legalmath.interpretation.assurance import investigation_observations as obs, source_references
from legalmath.interpretation.assurance.complete_investigation import CompleteInvestigation,verify
from tests.search.support import FunctionProvider
from tests.catala.backend_support import TOOLCHAIN
from tests.search.test_formal import AT
from .test_challenge_panel import decode,response
from .test_continuation_references import encode_quotes
from .test_integration import source,settings
from .test_successor_workflow import complete_responder


def responder(wire):
    request=decode(wire)
    if request['task']=='INTERPRETATION_CHALLENGES':return response(wire,differs=True,premise=True)
    value=complete_responder(request)
    return encode_quotes(value,request['source_references']) if 'source_references' in request else value


@pytest.fixture(scope='module')
def completed():
    root=Path(__file__).resolve().parents[2]
    with TemporaryDirectory(prefix='challenge-integration-',dir=root/'artifacts') as path:
        provider=FunctionProvider(responder)
        runner=CompleteInvestigation(root,path,provider,root/'.localresources/java-toolchain/jdk-17.0.20.1+1',AT,
            settings=settings(),maximum_scoped_actions=12,scoped_rounds=1,machine_qualification=True,catala=TOOLCHAIN,
            reference_protocol=source_references.PROTOCOL,input_profile='readable-tables.v1',
            challenge_options={'batch_size':4,'rounds':2,'maximum_actions':24})
        dossier=runner.run([source()],'Selected gift control')
        yield root,runner,provider,dossier


def test_optional_profile_executes_inside_actual_complete_dispatcher(completed):
    root,runner,provider,dossier=completed
    assert dossier['execution_complete'] and dossier['challenges']['response_differences']
    assert dossier['challenges']['finite_grammars'] and dossier['challenges']['formal_checks']
    assert verify(root,dossier)['status']=='FILE_BOUND_INVESTIGATION_VERIFIED'
    assert all('input_encoding' in req for req in provider.requests)
    stage=obs.check_stages(root,dossier,obs.method(runner),runner)
    assert stage['challenge_summary_hash'] and 'challenges' in stage['stage_started_ms']
    assert stage['legal_correctness']=='NOT_ESTABLISHED'


def test_omitted_panel_or_forged_summary_cannot_verify(completed):
    root,runner,provider,dossier=completed
    for defect in ('missing','changed','codec','configuration'):
        bad=deepcopy(dossier)
        if defect=='missing':bad['component_refs'].pop('challenges')
        elif defect=='changed':bad['challenges']['legal_correctness']='PROVED'
        elif defect=='codec':bad['binding']['input_profile']='literal'
        else:bad['binding']['challenge_panel']['rounds']=1
        with pytest.raises(LegalMathError):verify(root,bad)


def test_method_hash_includes_actual_optional_stage_and_changed_rounds(completed,monkeypatch):
    _,runner,_,_=completed
    baseline=obs.method(runner)
    assert baseline['transports']['readable_input']=='readable-tables.v1'
    assert baseline['challenge_panel']['rounds']==2
    monkeypatch.setattr(runner,'challenge_options',{**runner.challenge_options,'rounds':1})
    assert obs.method(runner)!=baseline


def test_existing_dossier_resumes_without_new_model_requests(completed):
    _,runner,provider,dossier=completed
    before=len(provider.requests)
    assert runner.run([source()],'Selected gift control')==dossier
    assert len(provider.requests)==before


def test_complete_continuation_reuses_stages_and_preserves_issue_limits(completed):
    root,old_runner,_,prior=completed
    with TemporaryDirectory(prefix='challenge-continuation-',dir=root/'artifacts') as path:
        provider=FunctionProvider(responder)
        runner=CompleteInvestigation(root,path,provider,old_runner.jdk,AT,settings=settings(),
            machine_qualification=True,catala=TOOLCHAIN,reference_protocol=source_references.PROTOCOL,
            input_profile='readable-tables.v1',challenge_options={
                'batch_size':4,'rounds':1,'maximum_actions':12,'input_profile':'readable-challenges.v1'})
        predecessor=root/old_runner.directory/'revisions'/prior['revision']/'dossier.json'
        dossier=runner.continue_challenges(predecessor)
        assert provider.requests and all(decode(r)['task']=='INTERPRETATION_CHALLENGES' for r in provider.requests)
        assert verify(root,dossier)['status']=='FILE_BOUND_CHALLENGE_CONTINUATION_VERIFIED'
        assert not dossier['fresh_whole_method_execution']
        assert all(v['spent']==3 for counts in dossier['challenges']['issue_histories'].values() for v in counts.values())
        for role,counts in prior['challenges']['issue_histories'].items():
            for key,value in counts.items():
                assert dossier['challenges']['issue_histories'][role][key]['started_ms']==value['started_ms']
        before=len(provider.requests)
        assert runner.continue_challenges(predecessor)==dossier and len(provider.requests)==before
        with pytest.raises(LegalMathError):obs.check_stages(root,dossier,obs.method(runner),runner)
        bad=deepcopy(dossier);bad['binding']['reused_components'].pop('core')
        from legalmath.canonical import digest
        bad['revision']=digest(bad['binding'])
        with pytest.raises(LegalMathError):verify(root,bad)
