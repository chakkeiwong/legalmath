from copy import deepcopy
import json
import pytest
from legalmath.errors import LegalMathError
from legalmath.interpretation.assurance.bounded_product import BoundedProduct
from legalmath.interpretation.assurance.phased.product import PhasedProduct
from legalmath.interpretation.assurance.phased.prepared_checkpoint import PROFILE
from legalmath.interpretation.assurance.phased.preparation_diagnosis import diagnose
from scripts.legal_mission_execution import ref, save, read
from tests.assurance.test_phased_product import PhasedScripted
from tests.assurance.test_bounded_product import envelope, limits


def setup(root):
    service=PhasedScripted()
    original=BoundedProduct(root,root/'acquisition',service,envelope(),list,limits=limits())
    acquired=original.investigate()
    def admission(name,count):
        if name.startswith('call-candidates-'):
            raise LegalMathError('E_RESOURCE_LIMIT',details='Fixture: optional call withheld')
        return dict(name=name,count=count)
    p=PhasedProduct(root,root/'prepare',service,envelope(),list,limits=limits(),
        phase_admit=admission,phase_identity='fixture')
    p.install_dispatch_admission()
    result=p.answer(acquired,preparation_only=True)
    assert result['answers']['p14']['status']=='PREPARED'
    d=p.directory
    journal=read(d/'calls/dispatch.json')
    checkpoint=dict(profile=PROFILE,question='p14',input_hash=p.route.input_hash,
        source_store=ref(root,d/'source-store.json'),result=ref(root,d/'result.json'),
        details=ref(root,d/'requirement-details.json'),journal=ref(root,d/'calls/dispatch.json'),
        representation=ref(root,d/'synthesis-representation-p14.json'),
        call_results={k:ref(root,d/'calls'/k/'result.json') for k in journal['calls']},
        levels=[dict(membership=ref(root,f),result=ref(root,f.with_name(f.name.replace('-membership.json','.json'))))
            for f in sorted(d.glob('reduction-p14-*-membership.json'))])
    save(root/'checkpoint.json',checkpoint)
    return service,acquired,checkpoint,result


def resumed(root,service):
    return PhasedProduct(root,root/'resumed',service,envelope(),list,limits=limits(),
        phase_admit=lambda *a:{},phase_identity='fixture',retained_preparation=ref(root,'checkpoint.json'))


def test_completed_synthesis_reused_and_baseline_skips_optional_tools(tmp_path):
    service,acquired,checkpoint,original=setup(tmp_path)
    before=len(service.requests)
    p=resumed(tmp_path,service)
    p.install_dispatch_admission()
    def forbidden(*a,**kw):raise AssertionError('Baseline tried optional tools')
    p.tools=forbidden
    result=p.answer(acquired)
    assert result['answers']['p14']['answer']['status']=='VALIDATED'
    new=[r['task'] for r in service.requests[before:]]
    assert 'ANSWER_ORIGINAL_QUESTION' in new
    assert not set(new)&{'SYNTHESIZE_FINDINGS','ASSESS_ORIGINAL_REQUIREMENT','GENERATE_SOURCE_WARRANTED_CANDIDATES','STRUCTURED_CRITICISM'}
    assert read(p.directory/'retained-preparation.json')==ref(tmp_path,'checkpoint.json')


@pytest.mark.parametrize('change',['source','input','missing_account','membership','lineage','final','call_result'])
def test_checkpoint_rejects_changed_source_or_lost_lineage(tmp_path,change):
    service,acquired,checkpoint,original=setup(tmp_path)
    if change=='input':checkpoint['input_hash']='changed'
    elif change=='call_result':
        path=tmp_path/next(iter(checkpoint['call_results'].values()))['path']
        value=read(path);value['value']['conclusion']='changed';save(path,value)
    else:
        target={'source':'source_store','missing_account':'details','final':'result'}.get(change)
        pointer=checkpoint[target] if target else checkpoint['levels'][0]['membership' if change=='membership' else 'result']
        value=read(tmp_path/pointer['path'])
        if change=='source':next(iter(value.values()))['text']='changed'
        elif change=='missing_account':value.clear()
        elif change=='membership':value['groups'][0].pop()
        elif change=='lineage':value[0]['children'].append('invented')
        elif change=='final':value['answers']['p14']['findings'][0]['value']['conclusion']='changed'
        save(tmp_path/pointer['path'],value)
        pointer.update(ref(tmp_path,pointer['path']))
    save(tmp_path/'checkpoint.json',checkpoint)
    with pytest.raises(LegalMathError):
        p=resumed(tmp_path,service)
        p.retained_acquisition=acquired
        p.requirement_details()
        p.reduce('p14',envelope()['original_questions'][0],[])


def test_bm25_only_does_not_need_formal_candidates(tmp_path):
    from legalmath.canonical import digest
    class Backend:
        tools=['bm25']
        def identity(self):return {'fixture':'bm25'}
        def retrieval(self,packet,inputs,directory):return {'status':'PASS','record_count':len(packet['units'])}
    p=BoundedProduct(tmp_path,tmp_path/'bm25',PhasedScripted(),envelope(),list,limits=limits(),selected_tools=['bm25'])
    def forbidden(*a,**kw):raise AssertionError('BM25 tried a model call')
    p.dispatch.call=forbidden
    rows=p.tools('p14',envelope()['original_questions'][0],Backend())
    assert len(rows)==1 and rows[0]['id']=='tool-bm25'
