from fastapi.testclient import TestClient
from legalmath.api.app import create_app
from legalmath.interpretation.search.models import Settings
from tests.search.support import packet


def test_search_api_does_not_accept_provider_commands_or_unauthorized_spend(tmp_path):
    identities={'author':{'token':'author','roles':['author']}}
    app=create_app(tmp_path,identities,run_jobs=False)
    headers={'Authorization':'Bearer author','Idempotency-Key':'start'}
    with TestClient(app) as client:
        body={'packet':packet(),'settings':Settings().model_dump()}
        result=client.post('/v1/interpretation-search',headers=headers,json=body)
        assert result.status_code==201,result.text
        rid=result.json()['run_id']
        response=client.post('/v1/interpretation-search/'+rid+'/execute',headers={**headers,'Idempotency-Key':'execute'},json={'at':'2026-09-23T00:00:00.000000Z'})
        assert response.status_code==422 and response.json()['error']=='E_DEPENDENCY'
        malicious=client.post('/v1/interpretation-search',headers={**headers,'Idempotency-Key':'bad'},json={**body,'provider_command':'arbitrary shell'})
        assert malicious.status_code==422
