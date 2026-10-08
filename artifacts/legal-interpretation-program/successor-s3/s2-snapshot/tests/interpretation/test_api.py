import time
from fastapi.testclient import TestClient
from legalmath.api.app import create_app
from .test_controller import config

IDS={'author':{'token':'author','roles':['author']},'meaning':{'token':'meaning','roles':['meaning']}}

def test_async_and_strict_requests(tmp_path,packet):
    app=create_app(tmp_path/'api',IDS)
    with TestClient(app) as client:
        def post(path,body,key,token='author'):
            return client.post(path,json=body,headers={'Authorization':'Bearer '+token,'Idempotency-Key':key})
        assert post('/v1/interpretations',{'packet':packet,'authority':'ENTERPRISE_AUTHENTICATED'},'bad').status_code==422
        result=post('/v1/interpretations',{'packet':packet},'create');assert result.status_code==201
        r=result.json();rid=r['run_id'];base='/v1/interpretations/'+rid
        p=dict(source_packet_hash=r['source_packet_hash'],source_unit_ids=['p10'],family_ids=['literal'],subject_unit='Customer',controlled_language='Prior route',bundle_hash=None,assumptions=[],arguments=[],parent_id=None,revision_reason='Blind first reading')
        assert post(base+'/configuration',{'members':config(p)},'configure').status_code==200
        assert post(base+'/execute',{},'execute').status_code==202
        deadline=time.monotonic()+15
        while time.monotonic()<deadline:
            data=client.get(base,headers={'Authorization':'Bearer meaning'}).json()
            if data['run']['report_id']: break
            time.sleep(.05)
        assert data['run']['status']=='BLOCKED_UNRESOLVED'
        assert len(data['records']['action'])==4
        assert client.get(base).status_code!=200
        assert post(base+'/review',{'reviewer_role':'meaning'},'forged').status_code==422
        html=client.get('/interpretations');assert html.status_code==200 and 'Discrepancies and uncertainty' in html.text
        assert '/v1/interpretations/{run_id}/review' in client.get('/openapi.json').json()['paths']


def test_cancel_without_start_and_recovery(tmp_path,packet):
    app=create_app(tmp_path/'api',IDS,run_jobs=False)
    with TestClient(app) as client:
        h={'Authorization':'Bearer author','Idempotency-Key':'new'}
        r=client.post('/v1/interpretations',json={'packet':packet},headers=h).json()
        response=client.post('/v1/interpretations/'+r['run_id']+'/cancel',json={},headers={**h,'Idempotency-Key':'cancel'})
        assert response.status_code==200
    other=create_app(tmp_path/'api',IDS)
    assert other.state.interpretations.read('meaning',r['run_id'])['run']['status']=='CANCELLED'
