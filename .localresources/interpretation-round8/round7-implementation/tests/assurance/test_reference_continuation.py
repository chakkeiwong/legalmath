from copy import deepcopy
import pytest
from legalmath.canonical import canonical,raw_digest
from legalmath.errors import LegalMathError
from legalmath.interpretation.search.providers import verify_allowance_checkpoint
from legalmath.interpretation.assurance.engine import Assurance
from tests.search.support import FunctionProvider
from tests.search.test_formal import AT


def test_later_authorized_calls_preserve_earlier_ledger_checkpoint(tmp_path):
    before={'maximum':100,'calls':[{'issued_at_ns':'1','request_hash':'a'*64}]}
    expected=raw_digest(canonical(before));p=tmp_path/'ledger.json'
    current=deepcopy(before);current['calls'].append({'issued_at_ns':'2','request_hash':'b'*64})
    p.write_bytes(canonical(current))
    assert verify_allowance_checkpoint(p,expected)=={'checkpoint_calls':1,'appended_calls':1,'maximum':100}
    for defect in ('history','ceiling','reset','overspend'):
        bad=deepcopy(current)
        if defect=='history':bad['calls'][0]['request_hash']='c'*64
        elif defect=='ceiling':bad['maximum']=101
        elif defect=='reset':bad['calls']=bad['calls'][1:]
        else:bad['calls']=bad['calls']*51
        p.write_bytes(canonical(bad))
        with pytest.raises(LegalMathError):verify_allowance_checkpoint(p,expected)


def test_changed_selected_regions_cannot_reuse_an_old_assurance_report(tmp_path,root,monkeypatch):
    provider=FunctionProvider(lambda r:pytest.fail('No call needed for identity check'))
    engine=Assurance(tmp_path/'run',provider,root/'.localresources/java-toolchain/jdk-17.0.20.1+1',AT)
    monkeypatch.setattr(engine,'_drive',lambda *a,**k:{'status':'INCOMPLETE','findings':[],
        'release_eligible':False,'execution_complete':False,'candidate_ids':[]})
    doc={'url':'https://www.sfc.hk/test-source','media_type':'text/plain','data':b'One. Two.',
        'selection':{'ranges':[[0,4]]}}
    engine.drive([doc],'Selected control')
    changed=deepcopy(doc);changed['selection']['ranges']=[[5,9]]
    with pytest.raises(LegalMathError) as exc:engine.drive([changed],'Selected control')
    assert exc.value.code=='E_IDEMPOTENCY'
