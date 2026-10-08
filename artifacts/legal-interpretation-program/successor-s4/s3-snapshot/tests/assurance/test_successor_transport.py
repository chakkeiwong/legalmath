from pathlib import Path
import json
import sys
import pytest
from legalmath.errors import LegalMathError
from legalmath.interpretation.search.providers import CodexProvider
from legalmath.interpretation.search.models import Settings
from .test_successor_grants import grant


def test_failed_transport_keeps_request_schema_and_redacted_evidence(tmp_path):
    allowance,_=grant(tmp_path)
    p=CodexProvider(allowance=allowance)
    p.command=lambda directory,schema,output:[sys.executable,'-c',
        'import sys;print("token=fake-sensitive-value",file=sys.stderr);sys.exit(1)']
    with pytest.raises(LegalMathError) as caught:p.complete({'public':'source'},{'type':'object','properties':{},'required':[],'additionalProperties':False},Settings(timeout_seconds=3))
    assert caught.value.code=='E_DEPENDENCY' and allowance.verify()['used']==1
    dirs=list((tmp_path/'provider-evidence').iterdir());assert len(dirs)==1
    assert json.loads((dirs[0]/'request.json').read_text())=={'public':'source'}
    assert 'fake-sensitive-value' not in (dirs[0]/'stderr.txt').read_text()
    assert json.loads((dirs[0]/'manifest.json').read_text())['files']['stderr.txt']['redacted']


def test_timeout_keeps_partial_transport_and_never_refunds(tmp_path):
    allowance,_=grant(tmp_path);p=CodexProvider(allowance=allowance)
    p.command=lambda directory,schema,output:[sys.executable,'-c',
        'import time;print("partial event",flush=True);time.sleep(10)']
    with pytest.raises(LegalMathError) as caught:p.complete({'public':'source'},{'type':'object','properties':{},'required':[],'additionalProperties':False},Settings(timeout_seconds=1))
    assert caught.value.code=='E_RESOURCE_LIMIT' and allowance.verify()['used']==1
    event=next((tmp_path/'provider-evidence').glob('*/events.jsonl'))
    assert event.read_text()=='partial event\n'
