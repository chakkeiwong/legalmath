"""Faults that invalidated preliminary round-14 execution must not recur."""
from pathlib import Path
import sys
import pytest
from legalmath.errors import LegalMathError
from legalmath.interpretation.contracts import Strict

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'scripts'))
from resolution_support import CircuitReader
from resolution_sources import new_packet, html_text


class Shape(Strict):
    ok: bool


def test_first_environment_failure_stops_all_later_dispatch(tmp_path):
    class FailedProvider:
        provider_id='failed.fixture'
        live=False
        routing={'model':'fixture','provider':'fixture','fields':{}}
        calls=0
        def complete(self,*args):
            self.calls+=1
            raise LegalMathError('E_DEPENDENCY',details='State database read-only')
    provider=FailedProvider()
    reader=CircuitReader(provider,tmp_path,{'test':'circuit'},maximum_actions=10)
    for i in range(8):
        assert reader.call({'id':i},Shape,lambda v:v) is None
    assert provider.calls==1
    assert reader.stopped_reason.startswith('DISPATCH_BLOCKED:')
    assert reader.provider.journal.report()['consumed_actions']==1


def test_official_packet_preserves_all_extracted_text_and_last_footnote():
    import json
    path=ROOT/'artifacts/interpretation/round14/sources-official/23ec52.json'
    data=json.loads(path.read_text());packet=new_packet(path)
    assert '\n'.join(u['text'] for u in packet['units'])==html_text(data['html'])
    text='\n'.join(u['text'] for u in packet['units'])
    assert '30.' in text and '36.' in text and 'Registered institutions should also provide' in text
    assert not data.get('capture_basis')
    assert all(u['span']['raw_sha256']==packet['units'][0]['span']['raw_sha256'] for u in packet['units'])


def test_master_rejects_fabricated_predecessor_summary(tmp_path,monkeypatch):
    # Continuation may never be an unchecked escape around stale code.
    import run_resolution_master as master
    from legalmath.interpretation.assurance.diversity import save
    save(tmp_path/'phase-results.json',{'R0':{'receipt':{'sequence':0,'result_hash':'fake'}}})
    monkeypatch.setattr(master,'OUT',tmp_path)
    monkeypatch.setattr(master,'EXECUTION',tmp_path/'execution')
    monkeypatch.setattr(master,'audit',lambda:None)
    monkeypatch.setattr(master,'sha',lambda p:'0'*64)
    with pytest.raises(LegalMathError,match='integrity'):
        master.execute('R1','R1')
