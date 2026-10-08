from copy import deepcopy
from pathlib import Path
import pytest
from legalmath.errors import LegalMathError
from legalmath.interpretation.assurance import evidence_identity as evidence


def test_installed_dependency_identity_replays_and_detects_forgery():
    value=evidence.dependency_identity(['pydantic','jsonschema'])
    assert all(r['status']=='FILES_HASHED' for r in value['distributions'])
    assert evidence.verify_dependencies(value)['status']=='LOCAL_FILES_RECHECKED'
    bad=deepcopy(value);bad['distributions'][0]['files'][0]['sha256']='0'*64
    with pytest.raises(LegalMathError):evidence.verify_dependencies(bad)
    assert not value['remote_execution_attested'] and not value['transitive_closure_established']


@pytest.mark.parametrize('url',['http://apps.sfc.hk/x','https://apps.sfc.hk.evil.test/x',
    'https://user@www.sfc.hk/x','https://www.sfc.hk:444/x','file:///tmp/a'])
def test_nonofficial_or_unsafe_retrieval_rejected_before_network(url):
    with pytest.raises(LegalMathError):evidence.checked_url(url)


def test_missing_dependency_is_explicit():
    value=evidence.dependency_identity(['legalmath-nonexistent-assurance-package'])
    assert value['distributions']==[{'name':'legalmath-nonexistent-assurance-package','status':'NOT_INSTALLED'}]


def fake_client(monkeypatch,responses):
    class Response:
        def __init__(self,status,headers,body):self.status_code=status;self.headers=headers;self.body=body
        def __enter__(self):return self
        def __exit__(self,*a):pass
        def raise_for_status(self):
            if self.status_code>=400:raise RuntimeError('HTTP failed')
        def iter_bytes(self,n):yield self.body
    class Client:
        def __init__(self,**kw):pass
        def __enter__(self):return self
        def __exit__(self,*a):pass
        def stream(self,*a,**kw):return Response(*responses.pop(0))
    import httpx
    monkeypatch.setattr(httpx,'Client',Client)


def test_bytes_rechecked_and_unexpected_format_preserved(tmp_path,monkeypatch):
    fake_client(monkeypatch,[(200,{'content-type':'text/html'},b'Client requires JavaScript')])
    row=evidence.acquire('https://www.elegislation.gov.hk/hk/cap571!en.pdf',tmp_path,expected_media=['application/pdf'])
    assert row['status']=='UNEXPECTED_MEDIA'
    assert evidence.verify_acquisition(tmp_path)==row
    (tmp_path/'response.bin').write_bytes(b'altered')
    with pytest.raises(LegalMathError):evidence.verify_acquisition(tmp_path)


def test_redirect_is_checked_before_second_request(tmp_path,monkeypatch):
    responses=[(302,{'location':'https://evil.test/law'},b'')]
    fake_client(monkeypatch,responses)
    row=evidence.acquire('https://www.sfc.hk/law',tmp_path,expected_media=['application/pdf'])
    assert row['status']=='FAILED' and len(row['requests'])==1 and not responses


def test_size_limit_is_not_a_truncated_success(tmp_path,monkeypatch):
    fake_client(monkeypatch,[(200,{'content-type':'application/pdf'},b'123456')])
    row=evidence.acquire('https://www.sfc.hk/law',tmp_path,expected_media=['application/pdf'],maximum_bytes=4)
    assert row['status']=='FAILED' and row['bytes']==0
